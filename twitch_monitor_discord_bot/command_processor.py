# Implements a CommandProcesser class to parse and handle commands received from
# discord users.
#
# All of the handler functions for commands are also implemented here.

import datetime
import os
import logging

from twitch_monitor_discord_bot import quotes
from twitch_monitor_discord_bot import utils
from twitch_monitor_discord_bot.twitch_monitor import InvalidTwitchUser

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


COMMAND_PREFIX = "!"

CMD_HELP_HELP = """
{0} [command]

Shows helpful information about the given command. Replace [command] with the
command you want help with.

Example:

@BotName !help addphrase
"""

CMD_WIKI_HELP = """
{0} [search text]

Search the provided text using Wikipedia's public API, and return the summary text
(generally the first paragraph) of the first page in the search results.

Example:

@BotName !wiki python programming language
"""

CMD_MOCK_HELP = """
{0} [mention]

Repeat everything said by a specific user in a "mocking" tone. Replace [mention]
with a mention of the discord user you want to mock.

Example:

@BotName !mock @discord_user
"""

CMD_UNMOCK_HELP = """
{0} [mention]

Stop mocking the mentioned user. Replace [mention] with a mention of the discord user
you want to stop mocking.

Example:

@BotName !unmock @discord_user
"""

CMD_APOLOGIZE_HELP = """
{0} [mention]

Apologize to a specific user for having mocked them. Replace [mention]
with a mention of the discord user you want to apologize to.

Example:

@BotName !apologize @discord_user
"""

CMD_QUOTE_HELP = """
{0}

Displays a random famous quote

Example:

@BotName !quote
"""

CMD_STREAMERS_HELP = """
{0}

Shows a list of streamers currently being monitored.

Example:

@BotName !streamers
"""

CMD_CLEARALLSTREAMERS_HELP = """
{0}

Clears the list of streamers currently being monitored.

Example:

@BotName !clearallstreamers
"""

CMD_ADDSTREAMERS_HELP = """
{0} [name] ...

Adds one or more new streamers to list of streamers being monitored. Replace
[name] with the twitch name(s) of the streamer(s) you want to monitor.

Example:

@BotName !addstreamers streamer1 streamer2 streamer3
"""

CMD_REMOVESTREAMERS_HELP = """
{0} [name] ...

Removes one or more streamers from the  list of streamers being monitored. Replace [name]
with the twitch name(s) of the streamer(s) you want to remove.

Example:

@BotName !removestreamers streamer1 streamer2 streamer3
"""

CMD_NOCOMPETITION_HELP = """
{0} [enabled]

[enabled] must be replaced with either 'true' or 'false'. If true, then no
announcements about other streams will be made while the host streamer is streaming.
If false, then announcements will always be made, even if the host streamer is streaming.

(To check if nocompetition is enabled, run the command with no true/false argument)

Examples:

@BotName !nocompetition true     (enable nocompetition)
@BotName !nocompetition false    (enable nocompetition)
@BotName !nocompetition          (check current state)
"""

CMD_PHRASES_HELP = """
{0}

Shows a numbered list of phrases currently in use for stream announcements.

Example:

@BotName !phrases
"""

CMD_TESTPHRASES_HELP ="""
{0}

Shows all phrases currently in use for stream announcements, with the format tokens
populated, so you can see what they will look like when posted to the discord channel.

Example:

@BotName !testphrases
"""

CMD_ADDPHRASE_HELP = """
{0} [phrase]

Adds a new phrase to be used for stream annnouncements. The following format
tokens may be used within a phrase:

    {{streamer_name}} : replaced with the streamer's twitch name
    {{stream_url}}    : replaced with the stream URL on twitch.tv
    {{botname}}       : replaced with bot name that is seen by other discord users
    {{date}}          : replaced with current date in DD/MM/YYY format
    {{times}}         : replaced with current time in HH:MM:SS format
    {{time}}          : replaced with current time in HH:MM format
    {{day}}           : replaced with the name of the current weekday (e.g. "Monday")
    {{month}}         : replaced with the name of the current month (e.g. "January")
    {{year}}          : replaced with the current year (e.g. "2022")

Example:

@BotName !addphrase \"{{streamer_name}} is now streaming at {{stream_url}}!\"
"""

CMD_REMOVEPHRASE_HELP = """
{0} [number]

Removes a phrase from the list of phrases being used for stream announcements.
[number] must be replaced with the number for the desired phrase, as shown in the
numbered list produced by the 'phrases' command. In other words, in order to remove
a phrase, you must first look at the output of the "phrases" command to get the
number of the phrase you want to remove.

Example:

@BotName !removephrase 4
"""

CMD_SAY_HELP = """
{0} [stuff to say]

Causes the bot to send a message in the announcements channel, immediately, containing
whatever you type in place of [stuff to say].

Example:

@BotName !say Good morning
"""

CMD_MOCKSON_HELP = """
{0}

Disable all mocking until 'mocksoff' command is sent

Example:

@BotName !mockson
"""

CMD_MOCKSOFF_HELP = """
{0}

Re-enable mocking after disabling

Example:

@BotName !mocksoff
"""

CMD_CLEARMOCKS_HELP = """
{0}

Clear all users that are currently being mocked

Example:

@BotName !clearmocks
"""

CMD_MOCKLIST_HELP = """
{0}

List the name & discord IDs of all users currently being mocked

Example:

@BotName !listmocks
"""


class Command(object):
    """
    Represents all data required to handle a single command
    """
    def __init__(self, word, handler, admin_only, helptext):
        self.word = word
        self.handler = handler
        self.helptext = helptext
        self.admin_only = admin_only

    def help(self):
        return "```%s```" % self.helptext.format(self.word)


class CommandProcessor(object):
    """
    Handles a specific set of commands, defined by a list of Command objects passed
    on object initialization
    """
    def __init__(self, config, bot, twitch_monitor, command_list):
        self.twitch_monitor = twitch_monitor
        self.config = config
        self.bot = bot
        self.cmds = {x.word: x for x in command_list}
        self.last_msg_by_user = {}
        self.mocking_users = []
        self.command_log_buf = []
        self.mocking_enabled = True

        self.log_filename = None

        try:
            # Check if command log file path is accessible
            _ = open(config.config.command_log_file, 'a')
        except:
            pass
        else:
            self.log_filename = config.config.command_log_file

    def close(self):
        logger.info("Stopping")
        if self.log_filename is not None:
            self._flush_command_log_buf()

    def _flush_command_log_buf(self):
        if self.command_log_buf:
            with open(self.log_filename, 'a') as fh:
                fh.write("\n".join(self.command_log_buf) + "\n")

            self.command_log_buf = []

    def _log_command_event(self, message):
        if self.log_filename is None:
            return

        timestamp = datetime.datetime.utcnow().strftime("%m/%d/%Y %H:%M:%S.%f")[:-3]
        msg_to_write = "[%s] %s" % (timestamp, message)
        self.command_log_buf.append(msg_to_write)

        if len(self.command_log_buf) >= 10:
            self._flush_command_log_buf()

    def _log_valid_command(self, author, command_text):
        msg = "[%s (%d)] %s" % (author.name, author.id, command_text)
        self._log_command_event(msg)

    def help(self):
        """
        Get the text for a discord message showing all available commands
        """
        return "Available commands:\n```%s```" % "\n".join(self.cmds.keys())

    def process_message(self, author, text):
        """
        Called for any old message (not a command for the bot)

        :param author: User object from discord.py, the user who wrote the message
        :param str text: Message text

        :return: Response to send back to discord
        :rtype: str
        """
        self.last_msg_by_user[author.id] = text

        if self.mocking_enabled and (author.id in self.mocking_users):
            return utils.mockify_text(text)

        return None

    def process_command(self, author, text):
        """
        Parse some text containing a command and run the handler, if there is an
        appropriate one

        :param author: User object from discord.py, the user who wrote the message
        :param str text: Command text to parse

        :return: Response to send back to discord
        :rtype: str
        """
        text = text.strip()
        if not text.startswith(COMMAND_PREFIX):
            return None

        words = text.lstrip(COMMAND_PREFIX).split()
        command = words[0].lower()

        if command in self.cmds:
            admin_only = self.cmds[command].admin_only
            if admin_only and (author.id not in self.config.config.discord_admin_users):
                return "Sorry %s, this command can only be used by admin users" % author.mention

            # Log received command
            self._log_valid_command(author, text)

            # Run command handler
            return self.cmds[command].handler(self, self.config, self.twitch_monitor, words[1:])

        return "Sorry, I don't recognize the command '%s'" % command


def _list_to_english(words):
    if not words:
        return ""
    elif len(words) == 1:
        return words[0]
    elif len(words) == 2:
        return "%s and %s" % (words[0], words[1])
    else:
        return ", ".join(words[:-1]) + " and " + words[-1]


# All command handlers, for all commands, follow...

def cmd_help(proc, config, twitch_monitor, args):
    bot_name = proc.bot.client.user.name

    if len(args) == 0:
        return (("See list of available commands below. Use the help command again "
                "and write another command word after 'help' (e.g. `@%s !help addphrase`) "
                "to get help with a specific command.\n" % bot_name) + proc.help())

    cmd = args[0].strip()
    if cmd.startswith(COMMAND_PREFIX):
        cmd = cmd.lstrip(COMMAND_PREFIX)

    if cmd not in proc.cmds:
        return "No command '%s' to get help for" % cmd

    return proc.cmds[cmd].help().replace('BotName', bot_name)

def cmd_streamers(proc, config, twitch_monitor, args):
    if len(config.config.streamers_to_monitor) == 0:
        return "No streamers are currently being monitored."

    lines = []
    for n in twitch_monitor.usernames:
        val = n
        if twitch_monitor.usernames[n] is False:
            val += " (unrecognized twitch username)"

        lines.append(val)

    return "Streamers being monitored:\n```\n%s```" % "\n".join(lines)

def cmd_addstreamers(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "'addstreamers' requires an argument, please provide the name(s) of the streamer(s) you want to add"

    names_to_add = []
    for arg in args:
        # Check if streamer was already added
        if twitch_monitor.username_added(arg):
            continue # Already added, skip

        # Check if streamer name contains invalid chars
        for c in arg:
            if (not c.isalpha()) and not (c.isdigit()) and (c not in ['_', '-']):
                return "Streamer name contains invalid character '%s'" % (c)

        names_to_add.append(arg)

    if not names_to_add:
        return "Streamer(s) already added"

    if not config.write_allowed():
        return ("Configuration was already changed in the last %d seconds, wait a bit and try again" %
                config.config.config_write_delay_seconds)

    try:
        twitch_monitor.add_usernames(names_to_add)
    except InvalidTwitchUser as e:
        return str(e)

    config.config.streamers_to_monitor.extend([x.lower() for x in args])

    config.save_to_file()

    if len(args) == 1:
        return "OK! Streamer '%s' is now being monitored" % args[0]
    else:
        return "OK! Streamers %s are now being monitored" % _list_to_english(args)

def cmd_removestreamers(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "'removestreamers' requires an argument, please provide the name(s) of the streamer(s) you want to remove"

    if not config.write_allowed():
        return ("Configuration was already changed in the last %d seconds, wait a bit and try again" %
                config.config.config_write_delay_seconds)

    twitch_monitor.remove_usernames(args)

    for name in args:
        try:
            config.config.streamers_to_monitor.remove(name.lower())
        except ValueError:
            if len(args) == 1:
                # If removing only one streamer, let the user know if they're trying
                # to remove a streamer that doesn't exist
                return "Streamer '%s' is not being monitored, nothing to remove" % args[0]
            else:
                # If removing multiple streamers at once, ignore any missing streamers
                # and just continue without notifying
                continue

    config.save_to_file()

    if len(args) == 1:
        return "OK! Streamer '%s' is no longer being monitored" % args[0]
    else:
        return "OK! Streamers %s are no longer being monitored" % _list_to_english(args)

def cmd_clearallstreamers(proc, config, twitch_monitor, args):
    twitch_monitor.clear_usernames()
    config.confing.streamers_to_monitor.clear()

    return "OK, no streamers are being monitored any more."

def cmd_nocompetition(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "nocompetition is %s" % ("enabled" if config.config.silent_when_host_streaming else "disabled")

    val = args[0].lower()
    if val not in ["true", "false"]:
        return "Invalid value '%s': please use 'true' or 'false'" % val

    if not config.write_allowed():
        return ("Configuration was already changed in the last %d seconds, wait a bit and try again" %
                config.config.config_write_delay_seconds)

    val = True if val == "true" else False

    if val != config.config.silent_when_host_streaming:
        config.config.silent_when_host_streaming = val
        config.save_to_file()

    return ("OK! nocompetition %s. announcements will %sbe made during host's stream" %
            ("enabled" if val else "disabled", "not " if val else ""))

def cmd_phrases(proc, config, twitch_monitor, args):
    msgs = config.config.stream_start_messages
    lines = ["%d. %s" % (i + 1, msgs[i]) for i in range(len(msgs))]
    return "Phrases currently in use:\n```\n%s```" % "\n\n".join(lines)

def cmd_testphrases(proc, config, twitch_monitor, args):
    fmt_args = utils.streamer_fmt_tokens("JohnSmith", "https://twitch.tv/JohnSmith")
    fmt_args.update(utils.bot_fmt_tokens(proc.bot))
    fmt_args.update(utils.datetime_fmt_tokens())

    lines = []
    for p in config.config.stream_start_messages:
        lines.append(p.format(**fmt_args))

    return "Phrases currently in use (with format tokens populated):\n```\n%s```" % "\n\n".join(lines)

def cmd_addphrase(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "'addphrase' requires an argument, please provide the text for the phrase you want to add"

    phrase = utils.clean_outer_quotes(" ".join(args))

    if not utils.validate_format_tokens(phrase):
        return "There's an invalid format token in the phrase you provided"

    if not config.write_allowed():
        return ("Configuration was already changed in the last %d seconds, wait a bit and try again" %
                config.config.config_write_delay_seconds)

    config.config.stream_start_messages.append(phrase)
    config.save_to_file()

    return "OK! added the following phrase:\n```%s```" % phrase

def cmd_removephrase(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "'removephrase' requires an argument, please provide the number for the phrase you want to remove"

    size = len(config.config.stream_start_messages)
    if size == 0:
        return "No phrases to remove"

    try:
        num = int(args[0])
    except ValueError:
        return "Uuh, '%s' is not a number" % args[0]

    if (num < 1) or (num > size):
        return "There is no phrase number %d, valid phrases numbers are 1-%d" % (num, size)

    if not config.write_allowed():
        return ("Configuration was already changed in the last %d seconds, wait a bit and try again" %
                config.config.config_write_delay_seconds)

    deleted = config.config.stream_start_messages[num - 1]
    del config.config.stream_start_messages[num - 1]
    config.save_to_file()

    return "OK! Removed the following phrase:\n```%s```" % deleted

def cmd_mock(proc, config, twitch_monitor, args):
    if len(args) == 0:
        return "'mock' requires more information, please mention the user you want to mock"

    user_id = utils.parse_mention(args[0].strip())
    if user_id is None:
        return "Please mention the user you wish to mock (e.g. '!mock @eknyquist)"

    if user_id not in proc.mocking_users:
        proc.mocking_users.append(user_id)

    if proc.mocking_enabled:
        if user_id in proc.last_msg_by_user:
            return utils.mockify_text(proc.last_msg_by_user[user_id])
    else:
        return "Mocking has been disabled by an admin user, but I have remembered your request"

def cmd_mockson(proc, config, twitch_monitor, args):
    if proc.mocking_enabled:
        return "Mocking is already enabled"

    proc.mocking_enabled = True
    return "OK, mocking is enabled now!"

def cmd_mocksoff(proc, config, twitch_monitor, args):
    if not proc.mocking_enabled:
        return "Mocking is already disabled"

    proc.mocking_enabled = False
    return "OK, mocking is disabled now!"

def cmd_clearmocks(proc, config, twitch_monitor, args):
    proc.mocking_users = []
    return "OK, I have forgotten about everyone I was supposed to mock!"

def cmd_listmocks(proc, config, twitch_monitor, args):
    names = []

    for user_id in proc.mocking_users:
        user_desc = "Unknown user"

        try:
            user = proc.bot.client.get_user(user_id)
        except:
            pass

        if user is not None:
            user_desc = user.name

        names.append('%s (%d)' % (user_desc, user_id))

    if not names:
        return "No users are being mocked right now."

    ret = "Here are the users that I am currently mocking:\n"
    ret += "```\n%s\n```" % '\n'.join(names)

    if not proc.mocking_enabled:
        ret += "\n(mocking not currently enabled)"

    return ret

def cmd_unmock(proc, config, twitch_monitor, args):
    if len(args) == 0:
        return "'unmock' requires more information, please mention the user you want to unmock"

    user_id = utils.parse_mention(args[0].strip())
    if user_id is None:
        return "Please mention the user you wish to unmock (e.g. '!unmock @eknyquist)"

    if user_id in proc.mocking_users:
        proc.mocking_users.remove(user_id)
        return "OK, I will leave %s alone now." % args[0].strip()

def cmd_apologize(proc, config, twitch_monitor, args):
    if len(args) == 0:
        return "'apologise' requires more information, please mention the user you want to apologise to"

    user_id = utils.parse_mention(args[0].strip())
    if user_id is None:
        return "Please mention the user you wish to apologise to (e.g. '!apologise @eknyquist)"

    return ("%s, I am truly, deeply sorry for mocking you just now. "
            "I'm only a robot, you see. I have no free will." % args[0].strip())

def cmd_quote(proc, config, twitch_monitor, args):
    text, author = quotes.get_donk_quote()
    return "```\n\"%s\"\n  - %s\n```" % (text, author)

def cmd_wiki(proc, config, twitch_monitor, args):
    search_text = ' '.join(args)
    result = utils.get_wiki_summary(search_text)
    if not result:
        return "No results found for %s, sorry :(" % search_text

    if len(result) > 900:
        result = result[:896] + " ..."

    if result.endswith("may refer to:"):
        return "Please be a bit more specific with your search terms"

    return result

def cmd_say(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "You didn't write a message for me to say. So I'll say nothing."

    proc.bot.send_message(" ".join(args))
    return "OK! message sent to channel '%s'" % config.config.discord_channel_name


twitch_monitor_bot_command_list = [
    # Commands available to everyone
    Command("help", cmd_help, False, CMD_HELP_HELP),
    Command("quote", cmd_quote, False, CMD_QUOTE_HELP),
    Command("mock", cmd_mock, False, CMD_MOCK_HELP),
    Command("unmock", cmd_unmock, False, CMD_UNMOCK_HELP),
    Command("apologise", cmd_apologize, False, CMD_APOLOGIZE_HELP),
    Command("apologize", cmd_apologize, False, CMD_APOLOGIZE_HELP),
    Command("wiki", cmd_wiki, False, CMD_WIKI_HELP),

    # Commands only available to admin users
    Command("listmocks", cmd_listmocks, True, CMD_MOCKLIST_HELP),
    Command("mockson", cmd_mockson, True, CMD_MOCKSON_HELP),
    Command("mocksoff", cmd_mocksoff, True, CMD_MOCKSOFF_HELP),
    Command("clearmocks", cmd_clearmocks, True, CMD_CLEARMOCKS_HELP),
    Command("streamers", cmd_streamers, True, CMD_STREAMERS_HELP),
    Command("addstreamers", cmd_addstreamers, True, CMD_ADDSTREAMERS_HELP),
    Command("removestreamers", cmd_removestreamers, True, CMD_REMOVESTREAMERS_HELP),
    Command("clearallstreamers", cmd_clearallstreamers, True, CMD_CLEARALLSTREAMERS_HELP),
    Command("phrases", cmd_phrases, True, CMD_PHRASES_HELP),
    Command("testphrases", cmd_testphrases, True, CMD_TESTPHRASES_HELP),
    Command("addphrase", cmd_addphrase, True, CMD_ADDPHRASE_HELP),
    Command("removephrase", cmd_removephrase, True, CMD_REMOVEPHRASE_HELP),
    Command("nocompetition", cmd_nocompetition, True, CMD_NOCOMPETITION_HELP),
    Command("say", cmd_say, True, CMD_SAY_HELP)
]
