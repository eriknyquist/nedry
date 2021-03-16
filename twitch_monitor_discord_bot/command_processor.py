from twitch_monitor_discord_bot.utils import validate_format_tokens

COMMAND_PREFIX = "!"

CMD_HELP_HELP = """
{0} [command]

Shows helpful information about the given command. Replace [command] with the
command you want help with.
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

Romoves one or more streamers from the  list of streamers being monitored. Replace [name]
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

Example:

@BotName !nocompetition
"""

CMD_PHRASES_HELP = """
{0}

Shows a numbered list of phrases currently in use for stream announcements.

@BotName !phrases
"""

CMD_ADDPHRASE_HELP = """
{0} [phrase]

Adds a new phrase to be used for stream annnouncements. The following format
tokens may be used within a phrase:

    {{streamer_name}} : replaced with the streamer's twitch name
    {{stream_url}}    : replaced with the stream URL on twitch.tv

Example:

@BotName !addphrase \"{{streamer_name}} is now streaming at {{stream_url}}!\"
"""

CMD_REMOVEPHRASE_HELP = """
{0} [number]

Removes a phrase from the list of phrases being used for stream announcements.
[number] must be replaced with the number for the desired phrase, as shown in the
numbered list produced by the 'addphrase' command.

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


class Command(object):
    def __init__(self, word, handler, helptext):
        self.word = word
        self.handler = handler
        self.helptext = helptext

    def help(self):
        return "```%s```" % self.helptext.format(self.word)


class CommandProcessor(object):
    def __init__(self, config, bot, twitch_monitor, command_list):
        self.twitch_monitor = twitch_monitor
        self.config = config
        self.bot = bot
        self.cmds = {x.word: x for x in command_list}

    def help(self):
        return "Available commands:\n```%s```" % "\n".join(self.cmds.keys())

    def process(self, text):
        text = text.strip()
        if not text.startswith(COMMAND_PREFIX):
            return None

        words = text.lstrip(COMMAND_PREFIX).split()
        command = words[0].lower()

        if command in self.cmds:
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


def cmd_help(proc, config, twitch_monitor, args):
    if len(args) == 0:
        return proc.help()

    cmd = args[0].strip()
    if cmd.startswith(COMMAND_PREFIX):
        cmd = cmd.lstrip(COMMAND_PREFIX)

    if cmd not in proc.cmds:
        return "No command '%s' to get help for" % cmd

    return proc.cmds[cmd].help()

def cmd_streamers(proc, config, twitch_monitor, args):
    if len(config.streamers) == 0:
        return "No streamers are currently being monitored."

    return "Streamers being monitored:\n```\n%s```" % "\n".join(config.streamers)

def cmd_addstreamers(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "'addstreamers' requires an argument, please provide the name(s) of the streamer(s) you want to add"

    names_to_add = []
    for arg in args:
        try:
            user_id = twitch_monitor.translate_username(arg)
        except:
            user_id = None

        if user_id is None:
            return "Invalid twitch streamer: %s" % arg

        # Check if streamer was already added
        if twitch_monitor.username_added(arg):
            continue # Already added, skip

        names_to_add.append(arg)

    if not config.write_allowed():
        return ("Configuration was already changed in the last %d seconds, wait a bit and try again" %
                config.write_delay_seconds)

    twitch_monitor.add_usernames(args)
    config.streamers.extend([x.lower() for x in args])

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
                config.write_delay_seconds)

    twitch_monitor.remove_usernames(args)

    for name in args:
        try:
            config.streamers.remove(name.lower())
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
    config.streamers.clear()

    return "OK, no streamers are being monitored any more."

def cmd_nocompetition(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "nocompetition is %s" % ("enabled" if config.silent_during_host_stream else "disabled")

    val = args[0].lower()
    if val not in ["true", "false"]:
        return "Invalid value '%s': please use 'true' or 'false'" % val

    if not config.write_allowed():
        return ("Configuration was already changed in the last %d seconds, wait a bit and try again" %
                config.write_delay_seconds)

    val = True if val == "true" else False

    if val != config.silent_during_host_stream:
        config.silent_during_host_stream = val
        config.save_to_file()

    return ("OK! nocompetition %s. announcements will %sbe made during host's stream" %
            ("enabled" if val else "disabled", "not " if val else ""))

def cmd_phrases(proc, config, twitch_monitor, args):
    msgs = config.stream_start_messages
    lines = ["%d. %s" % (i + 1, msgs[i]) for i in range(len(msgs))]
    return "Phrases currently in use:\n```\n%s```" % "\n".join(lines)

def cmd_addphrase(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "'addphrase' requires an argument, please provide the text for the phrase you want to add"

    phrase = " ".join(args)
    if not validate_format_tokens(phrase):
        return "There's an invalid format token in the phrase you provided"

    if not config.write_allowed():
        return ("Configuration was already changed in the last %d seconds, wait a bit and try again" %
                config.write_delay_seconds)

    config.stream_start_messages.append(phrase)
    config.save_to_file()

    return "OK! added the following phrase:\n```%s```" % phrase

def cmd_removephrase(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "'removephrase' requires an argument, please provide the number for the phrase you want to remove"

    size = len(config.stream_start_messages)
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
                config.write_delay_seconds)

    deleted = config.stream_start_messages[num - 1]
    del config.stream_start_messages[num - 1]
    config.save_to_file()

    return "OK! Removed the following phrase:\n```%s```" % deleted

def cmd_say(proc, config, twitch_monitor, args):
    if len(args) < 1:
        return "You didn't write a message for me to say. So I'll say nothing."

    proc.bot.send_message(" ".join(args))
    return "OK! message sent to channel '%s'" % config.discord_channel

twitch_monitor_bot_command_list = [
    Command("help", cmd_help, CMD_HELP_HELP),
    Command("streamers", cmd_streamers, CMD_STREAMERS_HELP),
    Command("addstreamers", cmd_addstreamers, CMD_ADDSTREAMERS_HELP),
    Command("removestreamers", cmd_removestreamers, CMD_REMOVESTREAMERS_HELP),
    Command("clearallstreamers", cmd_clearallstreamers, CMD_CLEARALLSTREAMERS_HELP),
    Command("phrases", cmd_phrases, CMD_PHRASES_HELP),
    Command("addphrase", cmd_addphrase, CMD_ADDPHRASE_HELP),
    Command("removephrase", cmd_removephrase, CMD_REMOVEPHRASE_HELP),
    Command("nocompetition", cmd_nocompetition, CMD_NOCOMPETITION_HELP),
    Command("say", cmd_say, CMD_SAY_HELP)
]
