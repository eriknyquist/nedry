from nedry.plugin import PluginModule

from pytimeparse.timeparse import timeparse

from datetime import timedelta, timezone, datetime
import threading
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
    def __init__(self, expiry_time, event_type, *event_data):
        self.expiry_time = expiry_time  # Expiry time in seconds, UTC timestamp
        self.event_type = event_type    # Event type (one of ScheduledEventType)
        self.event_data = event_data    # Event data (list, different for each event type)

    def time_remaining_string(self):
        return timedelta(seconds=(self.expiry_time - _utc_time()))

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

                if event.event_type == ScheduledEventType.DM_MESSAGE:
                    text = event.event_data[0]
                    user_id = event.event_data[1]
                    timedesc = event.event_data[2]

                    user = self._discord_bot.client.get_user(user_id)
                    msg = "Hey %s, don't forget %s!\n" % (user.mention, text)
                    msg += "(You asked me to remind you about this %s ago)" % timedesc

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
        for i in range(len(self._active_events)):
            if self._active_events[i].expiry_time > event.expiry_time:
                index = i
                break

        if (index == 0) and self._active_events:
            index = len(self._active_events)

        self._active_events.insert(index, event)
        return index == 0

    def add_event(self, mins_from_now, event_type, *event_data):
        expiry_time_secs = int(_utc_time() + (mins_from_now * 60))
        event = ScheduledEvent(expiry_time_secs, event_type, *event_data)

        with self._lock:
            first_event = len(self._active_events) == 0
            if self._active_events:
                # Other events are active, stop the thread before modifying the list
                self._stop_event.set()
                self._thread.join()

            self._add_active_event(event)

        # (Re)Start thread
        self._thread = threading.Thread(target=self._thread_task)
        self._thread.daemon = True
        self._thread.start()

        return event


HELPTEXT = """
"""


scheduler = Scheduler()


def _parse_time_string(s):
    s = s.replace(',', ' ').replace('&', '').replace(' and ', ' ')
    return timeparse(s)


def _dump_reminders(user):
    """
    Handler for !reminders command
    """
    events = []
    for e in scheduler.all_events():
        if e.event_type == ScheduledEventType.DM_MESSAGE:
            if e.event_data[1] == user.id:
                events.append("!remindme %s in %s (%s until reminder)" %
                              (e.event_data[0], e.event_data[2], e.time_remaining_string()))

    if not events:
        return "%s you have no scheduled reminders" % user.mention

    ret = "%s here are your scheduled reminders:\n" % user.mention
    ret += "```%s```" % "\n".join(events)

    return ret


def remind_command_handler(proc, config, twitch_monitor, args, message):
    """
    Handler for !remindme command
    """
    if len(args) == 0:
        return _dump_reminders(message.author)

    collapsed_spaces = ' '.join(args).lower()
    split_fields = collapsed_spaces.split(' in ')

    if len(split_fields) < 2:
        return "Invalid command format, try saying something like '!remindme to call my mother in 5 days and 6 hours"

    msg = ' '.join(split_fields[:-1])
    timedesc = split_fields[-1]

    seconds = _parse_time_string(timedesc)
    if seconds is None:
        return "Invalid time format, try saying something like '!remindme to call my mother in 5 days and 6 hours"

    if seconds < 60:
        return "Sorry, '%s' is too short, it needs to be at least 1 minute" % timedesc

    event = scheduler.add_event(int(seconds / 60),
                                ScheduledEventType.DM_MESSAGE,
                                msg,
                                message.author.id,
                                timedesc)

    return ("%s OK, I will remind you \"%s\" in %s!\n```(%s until reminder)```" %
            (message.author.mention, msg, timedesc, event.time_remaining_string()))


def schedule_command_handler(proc, config, twitch_monitor, args, message):
    """
    Handler for !schedule command
    """
    if len(args) < 4:
        return ("Invalid schedule, try saying something like:\n"
                "```!schedule channel-name Hey Guys, 10 mins have elapsed! in 10 minutes```")

    channel_name = args[0].strip()

    collapsed_spaces = ' '.join(args[1:])
    split_fields = collapsed_spaces.split(' in ')

    if len(split_fields) < 2:
        return ("Invalid schedule, try saying something like:\n"
                "```!schedule channel-name Hey Guys, 10 mins have elapsed! in 10 minutes```")


    msg = ' '.join(split_fields[:-1])
    timedesc = split_fields[-1]

    seconds = _parse_time_string(timedesc)

    channel = proc.bot.get_channel_by_name(channel_name)
    if not channel:
        return "Can't find a discord channel called '%s', are you sure that's right?" % channel_name

    event = scheduler.add_event(int(secon`ds / 60),
                                ScheduledEventType.CHANNEL_MESSAGE,
                                msg,
                                channel_name,
                                timedesc)

    return ("%s OK, I will send the following message:\n```%s```\n in channel \"%s\" in %s!\n"
            "```(%s until scheduled message)```" % (message.author.mention, msg, channel_name,
            timedesc, event.time_remaining_string()))


class Schedule(PluginModule):
    """
    Plugin for scheduling discord messages to be delivered at a specific later time
    """
    plugin_name = "schedule"
    plugin_version = "1.0.0"
    plugin_short_description = "Schedule discord messages"
    plugin_long_description = "Schedule discord messages"

    def open(self):
        """
        Enables plugin operation; subscribe to events and/or initialize things here
        """
        self.discord_bot.add_command("schedule", schedule_command_handler, False, HELPTEXT)
        self.discord_bot.add_command("remindme", remind_command_handler, False, HELPTEXT)
        scheduler.set_discord_bot(self.discord_bot)

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        self.discord_bot.remove_command("schedule")
        self.discord_bot.remove_command("remindme")
        scheduler.set_discord_bot(None)
