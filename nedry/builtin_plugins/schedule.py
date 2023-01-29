from nedry.plugin import PluginModule

from pytimeparse.timeparse import timeparse

from datetime import timedelta, timezone, datetime
import threading
import logging
import zoneinfo


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


PLUGIN_NAME = "schedule"
PLUGIN_VERSION = "1.1.0"


DATETIME_FMT = [
    ('%d/%m/%Y %H:%M', 'DD/MM/YYYY HH:MM'),
    ('%Y/%m/%d %H:%M', 'YYYY/MM/DD HH:MM'),
    ('%H:%M %d/%m/%Y', 'HH:MM DD/MM/YYYY'),
    ('%H:%M %Y/%m/%d', 'HH:MM YYYY/MM/DD'),
]

def _utc_time():
    return datetime.now(timezone.utc).timestamp()


class ScheduledEventType(object):
    """
    Enumerates all available types of scheduled event
    """
    DM_MESSAGE = 0
    CHANNEL_MESSAGE = 1


class ScheduledEvent(object):
    """
    Represents a single generic scheduled event
    """
    def __init__(self, time_seconds, expiry_time, event_type, *event_data):
        self.time_seconds = time_seconds # Expiry time in seconds from now
        self.expiry_time = expiry_time   # Expiry time in absolute seconds, UTC timestamp
        self.event_type = event_type     # Event type (one of ScheduledEventType)
        self.event_data = event_data     # Event data (list, different for each event type)

    def to_json(self):
        return {
            "time_seconds": self.time_seconds,
            "expiry_time": self.expiry_time,
            "event_type": self.event_type,
            "event_data": self.event_data
        }

    @classmethod
    def from_json(cls, attrs):
        return ScheduledEvent(
            attrs["time_seconds"],
            attrs["expiry_time"],
            attrs["event_type"],
            *attrs["event_data"]
        )

    def time_remaining_string(self):
        return timedelta(seconds=(int(self.expiry_time) - int(_utc_time())))

    def __str__(self):
        return "%s(%s, %s, %s)" % (self.__class__.__name__, self.expiry_time,
                                   self.event_type, self.event_data)

    def __repr__(self):
        return self.__str__()


class Scheduler(object):
    """
    Handles all scheduled events in a thread
    """
    def __init__(self):
        self._discord_bot = None
        self._active_events = []
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def set_discord_bot(self, bot):
        self._discord_bot = bot

    def all_events(self):
        with self._lock:
            for e in self._active_events:
                yield e

    def _handle_expired_events(self):
        with self._lock:
            while self._active_events and (self._active_events[0].expiry_time <= _utc_time()):
                event = self._active_events.pop(0)

                if not event:
                    return

                # Save state of scheduled event queue
                self.save_scheduled_events()

                if event.event_type == ScheduledEventType.DM_MESSAGE:
                    text = event.event_data[0]
                    user_id = event.event_data[1]

                    user = self._discord_bot.client.get_user(user_id)
                    msg = "Hey %s!\n```\n%s```\n" % (user.mention, text)
                    msg += "(You asked me to remind you about this %s ago)" % timedelta(seconds=event.time_seconds)

                    logger.debug("sending reminder '%s' to user %s" % (text, user.name))
                    self._discord_bot.send_dm(user, msg)

                elif event.event_type == ScheduledEventType.CHANNEL_MESSAGE:
                    text = event.event_data[0]
                    channel_name = event.event_data[1]

                    channel = self._discord_bot.get_channel_by_name(channel_name)
                    if not channel:
                        self.logger.error("unable to find channel '%s'" % channel_name)
                        continue

                    logger.debug("sending '%s' to channel %s" % (text, channel_name))
                    self._discord_bot.send_message(channel, text)

    def _thread_task(self):
        # Loop forever
        while True:
            if not self._active_events:
                # Exit if no active events, this thread should
                # only be started when there are active events
                return

            # Figure out how long to wait until the next expiry
            with self._lock:
                expiry_time = self._active_events[0].expiry_time

            utc_now = _utc_time()

            if (expiry_time + 1) < utc_now:
                time_until_expiry = 1
            else:
                time_until_expiry = expiry_time - utc_now

            stopped = self._stop_event.wait(time_until_expiry)
            if stopped:
                self._stop_event.clear()
                return

            self._handle_expired_events()

    def _add_active_event(self, event):
        # Need to maintain the list in order of timer expiry
        index = 0
        found_later_expiry = False

        for i in range(len(self._active_events)):
            if self._active_events[i].expiry_time > event.expiry_time:
                found_later_expiry = True
                index = i
                break

        if not found_later_expiry:
            index = len(self._active_events)

        self._active_events.insert(index, event)
        return index == 0

    def save_scheduled_events(self):
        if PLUGIN_NAME in self._discord_bot.config.config.plugin_data:
           del self._discord_bot.config.config.plugin_data[PLUGIN_NAME]

        scheduled_events = []
        for event in self._active_events:
            scheduled_events.append(event.to_json())

        self._discord_bot.config.config.plugin_data[PLUGIN_NAME] = scheduled_events
        self._discord_bot.config.save_to_file()

    def load_scheduled_events(self):
        events_loaded = 0
        if PLUGIN_NAME in self._discord_bot.config.config.plugin_data:
            with self._lock:
                for event_data in self._discord_bot.config.config.plugin_data[PLUGIN_NAME]:
                    event = ScheduledEvent.from_json(event_data)

                    if _utc_time() >= event.expiry_time:
                        # Event has already expired
                        continue

                    self._add_active_event(event)
                    events_loaded += 1

            if events_loaded > 0:
                # (Re)Start thread
                self._thread = threading.Thread(target=self._thread_task)
                self._thread.daemon = True
                self._thread.start()

    def add_event(self, mins_from_now, event_type, *event_data):
        expiry_time_secs = int(_utc_time() + (mins_from_now * 60))
        event = ScheduledEvent(mins_from_now * 60, expiry_time_secs, event_type, *event_data)

        with self._lock:
            first_event = len(self._active_events) == 0
            if self._active_events:
                # Other events are active, stop the thread before modifying the list
                self._stop_event.set()
                self._thread.join()

            self._add_active_event(event)

            # Save state of scheduled event queue
            self.save_scheduled_events()

        # (Re)Start thread
        self._thread = threading.Thread(target=self._thread_task)
        self._thread.daemon = True
        self._thread.start()

        return event

    def remove_events(self, events):
        with self._lock:
            for e in events:
                if e not in self._active_events:
                    raise ValueError()

            if self._active_events:
                # Other events are active, stop the thread before modifying the list
                self._stop_event.set()
                self._thread.join()

            for e in events:
                self._active_events.remove(e)

        # (Re)Start thread
        self._thread = threading.Thread(target=self._thread_task)
        self._thread.daemon = True
        self._thread.start()

    def get_events_of_type(self, event_type):
        with self._lock:
            return [x for x in self._active_events if x.event_type == event_type]


scheduler = Scheduler()


def _parse_time_string(s):
    s = s.replace(',', ' ').replace('&', '').replace(' and ', ' ')
    return timeparse(s)


def _dump_reminders(user):
    """
    Get description of all active reminders for given user
    """
    events = []
    for e in scheduler.get_events_of_type(ScheduledEventType.DM_MESSAGE):
        if e.event_data[1] == user.id:
            events.append("```\n%d. !remindme %s in %s (%s until reminder)```" %
                          (len(events) + 1, e.event_data[0], e.event_data[2], e.time_remaining_string()))

    if not events:
        return "%s you have no scheduled reminders" % user.mention

    ret = "%s here are your scheduled reminders:\n" % user.mention
    ret += "%s\n" % "\n\n".join(events)
    ret += "(Use the '!unremind' command to remove reminders)"

    return ret

def _dump_scheduled(user):
    """
    Get description of all scheduled messages
    """
    events = []
    for e in scheduler.get_events_of_type(ScheduledEventType.CHANNEL_MESSAGE):
        events.append("```\n%d. !schedule %s %s in %s (%s until scheduled message)```" %
                      (len(events) + 1, e.event_data[1], e.event_data[0], e.event_data[2],
                       e.time_remaining_string()))


    if not events:
        return "%s you have no scheduled messages" % user.mention

    ret = "%s here are your scheduled messages:\n" % user.mention
    ret += "%s\n" % "\n\n".join(events)
    ret += "(Use the '!unschedule' command to remove scheduled messages)"

    return ret

lastreminder_by_user = {}
lastsched_by_user = {}

UNREMIND_HELPTEXT = """
{0} [reminder_number] [reminder_number] ...
{0} all
{0} last

Remove one or more reminders by number. [reminder_number] should be replaced with the
number of the reminder you want to remove, as shown by the output of running the
'!remindme' command with no arguments.

Alternatively, instead of passing numbers, you can pass a single argument of "all"
to remove all reminders at once, or "last" to remove the last reminder that you scheduled.

Examples:

@BotName !unremind last          # Remove last added reminder
@BotName !unremind all           # Remove all reminders
@BotName !unremind 2             # Remove reminder #2
@BotName !unremind 5 6           # Remove reminders 5 and 6
"""

UNSCHEDULE_HELPTEXT = """
{0} [message_number] [message_number] ...
{0} all
{0} last

Remove one or more scheduled messages by number. [message_number] should be replaced
with the number of the message you want to remove, as shown by the output of running the
'!schedule' command with no arguments.

Alternatively, instead of passing numbers, you can pass a single argument of "all"
to remove all scheduled messages at once, or "last" to remove the most recently
added scheduled message.

Examples:

@BotName !unschedule last          # Remove last added message
@BotName !unschedule all           # Remove all messages
@BotName !unschedule 2             # Remove message #2
@BotName !unschedule 5 6           # Remove messages 5 and 6
"""

REMIND_HELPTEXT = """
{0} [reminder_text] in|on|at [time_description]

Set up a reminder. After the specified time, the bot will send you a DM with whatever
text you provided for [reminder_text].

[reminder_text] should be replaced with whatever text you want in the reminder message,
e.g. the thing that you want to be reminded of.

[time_description] should be replaced with a description of the desired time before
the reminder is delivered. The time can be described in one of the following ways:

- An absolute delay period written in english, using digits (e.g. "5") instead of
  words (e.g. "five") for number values. For example: "1 minute", "2 hours and 3 minutes",
  "2hrs3mins", "2 hours & 3 minutes"

- A specific date and time, written in one of the following formats:

  * DD/MM/YYYY HH:MM
  * YYYY/MM/DD HH:MM
  * HH:MM DD/MM/YYYY
  * HH:MM YYYY/MM/DD

  NOTE: if you are using a specific date/time, you should first tell the bot which
  timezone you are in using the "!timezone" command. That way, you can provide dates/times
  in your local timezone. You only have to set your timezone once, the bot will
  remember it (see "@BotName !help timezone" for more details about how to set your timezone).

Sending the command with no arguments returns the list of active reminders
for the user that sent the command.

Examples:

@BotName !{0}                                           # Query current reminders for me
@BotName !{0} To take out the trash... in 12 hours      # schedule reminder in 12 hours
@BotName !{0} to take a shower :D in 1 day and 5 mins   # Schedule reminder in 1 day and 5 minutes
@BotName !{0} to brush my teeth on 22/4/2025 14:30      # Schedule reminder at specific date & time
"""

SCHEDULE_HELPTEXT = """
{0} [channel_name] [message_text] in|on|at [time_description]

Set up a message to be sent by the bot in a specific discord channel after a specific
time delay.

[channel_name] should be replaced with name of the discord channel in which you
want the message to be sent.

[message_text] should be replaced with whatever text you want to be sent in the discord message.

[time_description] should be replaced with a description of the desired time before
the message is delivered to the channel. The time can be described in one of the following ways:

- An absolute delay period written in english, using digits (e.g. "5") instead of
  words (e.g. "five") for number values. For example: "1 minute", "2 hours and 3 minutes",
  "2hrs3mins", "2 hours & 3 minutes"

- A specific date and time, written in one of the following formats:

  * DD/MM/YYYY HH:MM
  * YYYY/MM/DD HH:MM
  * HH:MM DD/MM/YYYY
  * HH:MM YYYY/MM/DD

  NOTE: if you are using a specific date/time, you should first tell the bot which
  timezone you are in using the "!timezone" command. That way, you can provide dates/times
  in your local timezone. You only have to set your timezone once, the bot will
  remember it (see "@BotName !help timezone" for more details about how to set your timezone).

Sending the command with no arguments returns the list of currently scheduled messages.

Examples:

@BotName !{0}                                    # Query currently scheduled messages
@BotName !{0} jokes haha! in 2 hours             # Schedule message to "jokes" in 2 hours
@BotName !{0} news raining :( in 1h & 10m        # Schedule message to "news" in 1 hour, 10 mins
@BotName !{0} general howdy! at 17:02 23/10/2025 # Schedule message to "general" at specific date & time
"""

def _parse_datetime_str_to_seconds(config, discord_user, message):
    parsed_dt = None
    # See if we can parse a datetime from this string
    for fmtstr, _ in DATETIME_FMT:
        try:
            parsed_dt = datetime.strptime(message, fmtstr)
        except ValueError:
            continue
        else:
            break

    if parsed_dt is None:
        # None of the datetime format strings matched
        return

    # Check if discord user has a stored timezone
    tz_info = config.timezone_by_discord_user_id(discord_user.id)

    # Add discord user's timezone to datetime object
    parsed_dt = parsed_dt.replace(tzinfo=tz_info)
    local_now = datetime.now(tz=tz_info)

    # Return seconds until specified datetime (will be negative if datetime is in the past)
    return (parsed_dt - local_now).total_seconds()

def _parse_timedelta_from_message(config, discord_user, message):
    fields = None
    splitw = None
    for w in [' in ', ' on ', ' at ']:
        f = message.split(w)
        if len(f) >= 2:
            fields = f
            splitw = w
            break

    if None in [fields, splitw]:
        return None, None, None

    # See if string describes a time delta
    msg = ' '.join(fields[:-1])
    timedesc = fields[-1]
    deltasecs = _parse_time_string(timedesc)

    if deltasecs is None:
        deltasecs = _parse_datetime_str_to_seconds(config, discord_user, timedesc)

    return timedesc, splitw.strip(), deltasecs


def remind_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    """
    Handler for !remindme command
    """
    def invalid_format(cmd_word):
        return proc.usage_msg("Invalid reminder, try saying something like:\n"
                              "```!remindme to call my mother in 5 days and 6 hours```",
                              cmd_word)

    if not args.strip():
        return _dump_reminders(message.author)

    collapsed_spaces = ' '.join(args.split())
    timedesc, splitw, seconds = _parse_timedelta_from_message(config, message.author, collapsed_spaces)
    if seconds is None:
        return invalid_format(cmd_word)

    fields = args.rsplit(' ' + splitw + ' ', 1)
    if len(fields) == 1:
        fields = args.rsplit('\n' + splitw + ' ', 1)

    msg = fields[0].strip()

    if seconds < 0:
        return "Sorry, the time you provided is in the past, please provide a time in the future"

    if seconds < 60:
        return "Sorry, %s is too short, must be at least 1 minute in the future" % timedesc

    event = scheduler.add_event(int(seconds / 60),
                                ScheduledEventType.DM_MESSAGE,
                                msg,
                                message.author.id,
                                timedesc)

    # Save event for this user ID, for the "unremind last" command
    lastreminder_by_user[message.author.id] = event

    return ("%s OK, I will remind you \"%s\" %s %s!\n```\n(%s until reminder)```" %
            (message.author.mention, msg, splitw, timedesc, event.time_remaining_string()))


def schedule_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    """
    Handler for !schedule command
    """

    def invalid_format(cmd_word):
        return proc.usage_msg("Invalid schedule, try saying something like:\n"
                              "```!schedule channel-name Hey Guys, 10 mins have elapsed! in 10 minutes```",
                              cmd_word)
    if not args.strip():
        return _dump_scheduled(message.author)

    fields = args.lower().split(maxsplit=1)
    if len(fields) != 2:
        return invalid_format(cmd_word)

    channel_name = fields[0].strip()
    argtext = fields[1]

    collapsed_spaces = ' '.join(argtext.split())
    timedesc, splitw, seconds = _parse_timedelta_from_message(config, message.author, collapsed_spaces)
    if seconds is None:
        return invalid_format(cmd_word)

    fields = argtext.rsplit(' ' + splitw + ' ', 1)
    if len(fields) == 1:
        fields = argtext.rsplit('\n' + splitw + ' ', 1)

    msg = fields[0].strip()

    if seconds < 0:
        return "Sorry, the time you provided is in the past, please provide a time in the future"

    if seconds < 60:
        return "Sorry, '%s' is too short, must be at least 1 minute in the future" % timedesc


    channel = proc.bot.get_channel_by_name(channel_name)
    if not channel:
        return "Can't find a discord channel called '%s', are you sure that's right?" % channel_name

    event = scheduler.add_event(int(seconds / 60),
                                ScheduledEventType.CHANNEL_MESSAGE,
                                msg,
                                channel_name,
                                timedesc)

    # Save event for this user ID, for the "unschedule last" command
    lastsched_by_user[message.author.id] = event

    return ("%s OK, I will send the following message:\n```\n%s```\n in channel \"%s\" %s %s!\n"
            "```(%s until scheduled message)```" % (message.author.mention, msg, channel_name,
            splitw, timedesc, event.time_remaining_string()))


def unremind_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    """
    Handler for !unremind command
    """
    args = args.lower().split()
    if len(args) == 0:
        return proc.usage_msg("Please provide some arguments.", cmd_word)

    if args[0].lower() == "all":
        all_events = scheduler.get_events_of_type(ScheduledEventType.DM_MESSAGE)
        events_to_remove = []
        for e in all_events:
            if e.event_data[1] == message.author.id:
                events_to_remove.append(e)

        scheduler.remove_events(events_to_remove)
        return "%s OK! removed all your reminders" % message.author.mention

    elif args[0].lower() == "last":
        if message.author.id not in lastreminder_by_user:
            return "Sorry, I don't remember the last reminder you added"

        removed = lastreminder_by_user[message.author.id]
        scheduler.remove_events([removed])
        del lastreminder_by_user[message.author.id]

        return ("OK! removed this reminder:\n```!remindme %s in %s```" %
                (removed.event_data[0], removed.event_data[2]))

    all_events = []
    for e in scheduler.get_events_of_type(ScheduledEventType.DM_MESSAGE):
        if e.event_data[1] == message.author.id:
            all_events.append(e)

    if not all_events:
        return "%s No reminders to remove" % message.author.mention

    event_nums = []
    for a in args:
        try:
            i = int(a)
        except ValueError:
            return "%s Invalid reminder number '%s'" % (a, message.author.mention)

        event_nums.append(i)

    events_to_remove = []
    for n in event_nums:
        if n < 1:
            return "%s Invalid reminder number '%d'" % (n, message.author.mention)

        if n > len(all_events):
            return "%s Invalid reminder number '%d'" % (n, message.author.mention)

        events_to_remove.append(all_events[n - 1])

    try:
        scheduler.remove_events(events_to_remove)
    except ValueError:
        return "%s Invalid event number provided" % message.author.mention

    rm_desc = ["!remindme %s in %s" % (e.event_data[0], e.event_data[2]) for e in events_to_remove]
    return "%s OK! removed the following reminders:\n```%s```" % (message.author.mention, '\n'.join(rm_desc))


def unschedule_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    """
    Handler for !unschedule command
    """
    args = args.lower().split()
    if len(args) == 0:
        return proc.usage_msg("Please provide some arguments.", cmd_word)

    if args[0].lower() == "all":
        events_to_remove = scheduler.get_events_of_type(ScheduledEventType.CHANNEL_MESSAGE)
        scheduler.remove_events(events_to_remove)
        return "%s OK! removed all scheduled messages" % message.author.mention

    elif args[0].lower() == "last":
        if message.author.id not in lastsched_by_user:
            return "Sorry, I don't remember the last scheduled message you added"

        removed = lastsched_by_user[message.author.id]
        del lastsched_by_user[message.author.id]

        try:
            scheduler.remove_events([removed])
        except ValueError:
            return "The last message you scheduled has already been removed"

        return ("OK! removed this scheduled message:\n```!schedule %s %s in %s```" %
                (removed.event_data[1], removed.event_data[0], removed.event_data[2]))

    all_events = []
    for e in scheduler.get_events_of_type(ScheduledEventType.CHANNEL_MESSAGE):
        all_events.append(e)

    if not all_events:
        return "%s No scheduled messages to remove" % message.author.mention

    event_nums = []
    for a in args:
        try:
            i = int(a)
        except ValueError:
            return "%s Invalid message number '%s'" % (a, message.author.mention)

        event_nums.append(i)

    events_to_remove = []
    for n in event_nums:
        if n < 1:
            return "%s Invalid message number '%d'" % (n, message.author.mention)

        if n > len(all_events):
            return "%s Invalid message number '%d'" % (n, message.author.mention)

        events_to_remove.append(all_events[n - 1])

    try:
        scheduler.remove_events(events_to_remove)
    except ValueError:
        return "%s Invalid message number provided" % message.author.mention

    rm_desc = ["!schedule %s %s in %s" % (e.event_data[1], e.event_data[0], e.event_data[2]) for e in events_to_remove]
    return "%s OK! removed the following scheduled messages:\n```%s```" % (message.author.mention, '\n'.join(rm_desc))


class Schedule(PluginModule):
    """
    Plugin for scheduling discord messages to be delivered at a specific later time
    """
    plugin_name = PLUGIN_NAME
    plugin_version = PLUGIN_VERSION
    plugin_short_description = "Schedule discord messages"
    plugin_long_description = """
    Adds multiple commands that allow;

    - All discord users to create/manage reminders, which consist of the bot sending
      the a DM with a specific message after a specified delay.

    - Admin. discord users to create/manage scheduled channel messages, which consist
      of the bot sending a specific message to a specific public channel after a
      specified time delay.

    Commands added:

    !remindme (see !help remindme)
    !unremind (see !help unremind)
    !schedule (see !help schedule)
    !unschedule (see !help unschedule)
    """

    def __init__(self, *args, **kwargs):
        super(Schedule, self).__init__(*args, **kwargs)
        self.open_count = 0

    def open(self):
        """
        Enables plugin operation; subscribe to events and/or initialize things here
        """
        self.discord_bot.add_command("schedule", schedule_command_handler, True, SCHEDULE_HELPTEXT)
        self.discord_bot.add_command("unschedule", unschedule_command_handler, True, UNSCHEDULE_HELPTEXT)
        self.discord_bot.add_command("remindme", remind_command_handler, False, REMIND_HELPTEXT)
        self.discord_bot.add_command("unremind", unremind_command_handler, False, UNREMIND_HELPTEXT)
        scheduler.set_discord_bot(self.discord_bot)

        if self.open_count == 0:
            # Only want to do this on first open
            scheduler.load_scheduled_events()

        self.open_count += 1

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        self.discord_bot.remove_command("schedule")
        self.discord_bot.remove_command("remindme")
        self.discord_bot.remove_command("unremind")
        self.discord_bot.remove_command("unschedule")
        scheduler.set_discord_bot(None)
