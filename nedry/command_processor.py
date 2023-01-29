# Implements a CommandProcesser class to parse and handle commands received from
# discord users.
#
# All of the handler functions for commands are also implemented here.

import random
import datetime
import os
import logging

from nedry import quotes
from nedry import utils
from nedry.twitch_monitor import InvalidTwitchUser


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


COMMAND_PREFIX = "!"

CMD_HELP_HELP = """
{0} [command]

Shows helpful information about the given command. Replace [command] with the
command you want help with.


Example:

@BotName !help wiki
"""

CMD_TIMEZONE_HELP = """
{0} [timezone_name]

Set the timezone for the author of the discord message, allowing this
discord user to provide/see dates and times in their local timezone.

[timezone_name] should be replaced with the name of a timezone from the IANA
time zone database, or some substring, e.g. "london" or "los angeles". If you
live in a big city, then often just typing the name of the city here will be
enough. If you are having issues, however, try selecting your region on
this IANA timezone map, and using the country/city name that is shown in
the drop-down selection box: https://kevalbhatt.github.io/timezone-picker

Sending this command with no arguments will query the timezone currently
assigned to the author of the discord message.

Example:

@BotName !timezone           # Query timezone setting for this discord user
@BotName !timezone london    # Set timezone for this discord user to "Europe/London"
"""

CMD_PLUGINFO_HELP = """
{0} [plugin_name]

Query information about a loaded plugin.

Example:

@BotName !pluginfo knock_knock_jokes
"""

CMD_ANNOUNCECHANNEL_HELP = """
{0} [discord_channel_name]

Sets the discord channel where stream announcements will be posted. If no discord
channel name is provided, then the name of the current stream announcements channel
will be returned.

Example:

@BotName !announcechannel                # Query current channel name
@BotName !announcechannel my-channel     # Set announcements channel to 'my-channel'
"""

CMD_TWITCHCLIENTID_HELP = """
{0} [client_id_string] [client_secret_string]

Sets the client ID and client secret used to interact with the Twitch API.
Replace [client_id_string] with the client ID string for your twitch application.
Replace [client_secret_string] with the client secret string for your twitch application.

Example:

@BotName !help twitchclientid XXXXXXXXXXXX YYYYYYYYYYYY
"""

CMD_PLUGINS_HELP = """
{0}

Show all loaded plugins, and show which ones are currently enabled

Example:

@BotName !help wiki
"""

CMD_PLUGSON_HELP = """
{0} [plugin_name] [plugin_name] ...

Enable / turn on one or more plugins by name (plugin names can be seen in the
output of the 'plugins' command, surrounded by square braces e.g. "[]").

Example:

@BotName !pluginon knock_knock_jokes other_plugin
"""

CMD_PLUGSOFF_HELP = """
{0} [plugin_name] [plugin_name] ...

Disable / turn off one or more plugins by name (plugin names can be seen in the
output of the 'plugins' command, surrounded by square braces e.g. "[]").

Example:

@BotName !pluginoff knock_knock_jokes other_plugin
"""

CMD_CMDHISTORY_HELP = """
{0} [entry_count]

Show the last few entries in the command log file. If no count is given then the
last 25 entries are shown.

Examples:

@BotName !{0}     (show last 25 entries)
@BotName !{0} 5   (show last 5 entries)
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

CMD_REMOVEPHRASES_HELP = """
{0} [number] [number] ...

Removes one or more phrases from the list of phrases being used for stream announcements.
[number] must be replaced with the number for the desired phrase, as shown in the
numbered list produced by the 'phrases' command. In other words, in order to remove
a phrase, you must first look at the output of the "phrases" command to get the
number of the phrase you want to remove.

Example:

@BotName !removephrases 3 4 5
"""

CMD_SAY_HELP = """
{0} [stuff to say]

Causes the bot to send a message in the announcements channel, immediately, containing
whatever you type in place of [stuff to say].

Example:

@BotName !say Good morning
"""


class Command(object):
    """
    Represents all data required to handle a single command
    """
    def __init__(self, word, handler, admin_only, helptext):
        self.word = word.lower()
        self.handler = handler
        self.helptext = helptext
        self.admin_only = admin_only

    def help(self):
        return "```%s```" % self.helptext.format(self.word)

    def help_oneline(self):
        lines = []
        empty_lines_seen = 0
        for line in self.helptext.strip().split('\n'):
            line = line.strip()
            if not line:
                empty_lines_seen += 1
            elif empty_lines_seen:
                lines.append(line)

            if empty_lines_seen > 1:
                break

        if len(self.word) < 20:
            num_spaces = 20 - len(self.word)
        else:
            num_spaces = 1

        ret = self.word + (" " * num_spaces) + " : " + ' '.join(lines)
        if len(ret) > 80:
            ret = ret[:76] + ' ...'

        return ret

class MessageData(object):
    """
    Represents all required data related to the author and channel of a received command
    """
    def __init__(self, channel, author, is_admin):
        self.channel = channel
        self.author = author
        self.is_admin = is_admin


class ChannelData(object):
    """
    Holds information we need to track on a per-discord-channel basis
    """
    def __init__(self):
        self.joke_in_progress = None


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
        self.command_log_buf = []
        self.mocking_enabled = True
        self.log_filename = None
        self.channel_data = {}

        try:
            # Check if command log file path is accessible
            _ = open(config.config.command_log_file, 'a')
        except:
            pass
        else:
            self.log_filename = config.config.command_log_file

    def get_channel_data(self, channel_id, ident):
        if channel_id not in self.channel_data:
            return None

        if ident not in self.channel_data[channel_id]:
            return None

        return self.channel_data[channel_id][ident]

    def add_command(self, cmd_word, cmd_handler, admin_only, helptext):
        cmd = Command(cmd_word, cmd_handler, admin_only, helptext)
        if cmd.word in self.cmds:
            raise ValueError("Command '%s' already exists" % cmd.word)

        self.cmds[cmd.word] = cmd

    def remove_command(self, cmd_word):
        if cmd_word in self.cmds:
            del self.cmds[cmd_word]

    def close(self):
        logger.debug("Stopping")
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

        timestamp = datetime.datetime.utcnow().strftime("%m/%d/%Y %H:%M:%S")
        msg_to_write = "[%s] %s" % (timestamp, message)
        self.command_log_buf.append(msg_to_write)

        if len(self.command_log_buf) >= 10:
            self._flush_command_log_buf()

    def _log_valid_command(self, author, command_text):
        msg = "[%s (%d)] %s" % (author.name, author.id, command_text)
        self._log_command_event(msg)

    def command_history(self, last=25):
        if not self.log_filename:
            return None

        if not os.path.isfile(self.log_filename):
            return None

        if len(self.command_log_buf) >= last:
            # All requested lines are in memory
            return self.command_log_buf[-last:]

        lines_in_file = last - len(self.command_log_buf)

        with open(self.log_filename, 'r') as fh:
            lines = [l.strip() for l in fh.readlines()]

        return lines[-lines_in_file:] + self.command_log_buf

    def help(self, include_admin=True):
        """
        Get the text for a discord message showing all available commands
        """
        if include_admin:
            cmd_names = [self.cmds[x].help_oneline() for x in self.cmds]
        else:
            cmd_names = [self.cmds[x].help_oneline() for x in self.cmds if not self.cmds[x].admin_only]

        return "Available commands:\n```%s```" % "\n".join(cmd_names)

    def process_message(self, message):
        """
        Called for any old message (not a command for the bot)

        :return: Response to send back to discord
        :rtype: str
        """
        author = message.author
        text = message.content

        return None

    def process_command(self, channel, author, text):
        """
        Parse some text containing a command and run the handler, if there is an
        appropriate one

        :param channel: Discord channel object
        :param author: User object from discord.py, the user who wrote the message
        :param str text: Command text to parse

        :return: Response to send back to discord
        :rtype: str
        """
        text = text.strip()
        if not text.startswith(COMMAND_PREFIX):
            # Not a command, do nothing
            return None

        words = text.lstrip(COMMAND_PREFIX).split()
        command = words[0].lower().strip()
        argtext = text.lstrip(COMMAND_PREFIX + command)

        msg_data = MessageData(channel, author, author.id in self.config.config.discord_admin_users)

        if command in self.cmds:
            if self.cmds[command].admin_only and not msg_data.is_admin:
                return ("Sorry %s, this command can only be used by admin users. "
                        "Use the '!help' command to see which commands you are allowed to use."
                        % author.mention)

            # Log received command
            if command != 'cmdhistory':
                self._log_valid_command(author, text)

            # Run command handler
            handler = self.cmds[command].handler
            return handler(command, argtext, msg_data, self, self.config, self.twitch_monitor)

        return "Sorry, I don't recognize the command '%s'" % command

    def usage_msg(self, msg, cmd_word):
        ret = msg + "\n\n"
        ret += "For more information see:\n```@%s !help %s```" % (self.bot.client.user.name, cmd_word)
        return ret



# All command handlers, for all commands, follow...

def cmd_help(cmd_word, args, message, proc, config, twitch_monitor):
    bot_name = proc.bot.client.user.name
    args = args.lower().split()

    if len(args) == 0:
        return (("See list of available commands below. Use the help command again "
                "and write another command word after 'help' (e.g. `@%s !help wiki`) "
                "to get help with a specific command.\n" % bot_name) + proc.help(include_admin=message.is_admin))

    cmd = args[0].strip()
    if cmd.startswith(COMMAND_PREFIX):
        cmd = cmd.lstrip(COMMAND_PREFIX)

    if cmd not in proc.cmds:
        return "No command '%s' to get help for" % cmd

    return proc.cmds[cmd].help().replace('BotName', bot_name)

def cmd_cmdhistory(cmd_word, args, message, proc, config, twitch_monitor):
    default_count = False
    args = args.lower().split()

    if len(args) == 0:
        count = 25
        default_count = True
    else:
        try:
            count = int(args[0])
        except ValueError:
            return "Command expects an integer, cannot convert '%s' to an integer" % args[0]

    # HTTP request can't be larger than 2000 bytes
    max_len = 1600
    ret = ""
    history = proc.command_history(count)
    actual_count = 0

    history.reverse()
    for line in history:
        if (len(line) + 1 + len(ret)) > max_len:
            break

        ret = line + "\n" + ret
        actual_count += 1

    truncated = actual_count < count

    firstline = "Last %s commands" % (actual_count if default_count else count)

    if truncated and not default_count:
        firstline += " (exceeded max. message size so only showing last %d)" % actual_count

    return "%s:\n```\n%s```" % (firstline, ret)

def cmd_streamers(cmd_word, args, message, proc, config, twitch_monitor):
    if len(config.config.streamers_to_monitor) == 0:
        return "No streamers are currently being monitored."

    lines = []
    for n in twitch_monitor.usernames:
        val = n
        if twitch_monitor.usernames[n] is False:
            val += " (unrecognized twitch username)"

        lines.append(val)

    return "Streamers being monitored:\n```\n%s```" % "\n".join(lines)

def cmd_addstreamers(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) < 1:
        return proc.usage_msg("Please provide the name(s) of the streamer(s) you want to add.", cmd_word)

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

    try:
        twitch_monitor.add_usernames(names_to_add)
    except InvalidTwitchUser as e:
        return str(e)

    config.config.streamers_to_monitor.extend([x.lower() for x in args])

    config.save_to_file()

    if len(args) == 1:
        return "OK! Streamer '%s' is now being monitored" % args[0]
    else:
        return "OK! Streamers %s are now being monitored" % utils.list_to_english(args)

def cmd_removestreamers(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) < 1:
        return proc.usage_msg("Please provide the name(s) of the streamer(s) you want to remove.", cmd_word)

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
        return "OK! Streamers %s are no longer being monitored" % utils.list_to_english(args)

def cmd_clearallstreamers(cmd_word, args, message, proc, config, twitch_monitor):
    twitch_monitor.clear_usernames()
    config.confing.streamers_to_monitor.clear()

    return "OK, no streamers are being monitored any more."

def cmd_nocompetition(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) < 1:
        return "nocompetition is %s" % ("enabled" if config.config.silent_when_host_streaming else "disabled")

    val = args[0].lower()
    if val not in ["true", "false"]:
        return "Invalid value '%s': please use 'true' or 'false'" % val

    val = True if val == "true" else False

    if val != config.config.silent_when_host_streaming:
        config.config.silent_when_host_streaming = val
        config.save_to_file()

    return ("OK! nocompetition %s. announcements will %sbe made during host's stream" %
            ("enabled" if val else "disabled", "not " if val else ""))

def cmd_phrases(cmd_word, args, message, proc, config, twitch_monitor):
    msgs = config.config.stream_start_messages
    lines = ["%d. %s" % (i + 1, msgs[i]) for i in range(len(msgs))]
    return "Phrases currently in use:\n```\n%s```" % "\n\n".join(lines)

def cmd_testphrases(cmd_word, args, message, proc, config, twitch_monitor):
    fmt_args = utils.streamer_fmt_tokens("JohnSmith", "https://twitch.tv/JohnSmith")
    fmt_args.update(utils.bot_fmt_tokens(proc.bot))
    fmt_args.update(utils.datetime_fmt_tokens())

    lines = []
    for p in config.config.stream_start_messages:
        lines.append(p.format(**fmt_args))

    return "Phrases currently in use (with format tokens populated):\n```\n%s```" % "\n\n".join(lines)

def cmd_addphrase(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) < 1:
        return proc.usage_msg("Please provide the text for the phrase you want to add.",
                              cmd_word)

    phrase = utils.clean_outer_quotes(" ".join(args))

    if not utils.validate_format_tokens(phrase):
        return proc.usage_msg("There's an invalid format token in the phrase you provided.",
                              cmd_word)

    if phrase in config.config.stream_start_messages:
        return "This phrase already exists"

    config.config.stream_start_messages.append(phrase)
    config.save_to_file()

    return "OK! added the following phrase:\n```%s```" % phrase

def cmd_removephrases(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) < 1:
        return proc.usage_msg("Please provide the number(s) for the phrase(s) you want to remove.",
                              cmd_word)

    size = len(config.config.stream_start_messages)
    if size == 0:
        return "No phrases to remove"

    phrases_to_remove = []
    for a in args:
        try:
            num = int(a.strip())
        except ValueError:
            return proc.usage_msg("Uuh, '%s' is not a number" % a,
                                  cmd_word)

        if (num < 1) or (num > size):
            return proc.usage_msg("There is no phrase number %d, valid phrases numbers are 1-%d" % (num, size),
                                  cmd_word)

        phrases_to_remove.append(config.config.stream_start_messages[num - 1])

    for p in phrases_to_remove:
        config.config.stream_start_messages.remove(p)

    config.save_to_file()

    return "OK! Removed the following phrases:\n```%s```" % '\n'.join(phrases_to_remove)

def cmd_quote(cmd_word, args, message, proc, config, twitch_monitor):
    text, author = quotes.get_donk_quote()
    return "```\n\"%s\"\n  - %s\n```" % (text, author)

def cmd_say(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) < 1:
        return proc.usage_msg("Give me something to say!", cmd_word)

    proc.bot.send_stream_announcement(" ".join(args))
    return "OK! message sent to channel '%s'" % config.config.discord_channel_name

def cmd_plugins(cmd_word, args, message, proc, config, twitch_monitor):
    enabled = proc.bot.plugin_manager.enabled_plugins()
    disabled = proc.bot.plugin_manager.disabled_plugins()

    if (not enabled) and (not disabled):
        return "No plugins are loaded"

    def format_plugin_list(plugins):
        return["[%s] version %s: %s" % (x.plugin_name, x.plugin_version, x.plugin_short_description) for x in plugins]

    enabled_desc = format_plugin_list(enabled)
    disabled_desc = format_plugin_list(disabled)
    ret = ""

    if enabled:
        ret += "The following plugins are enabled:\n"
        ret += "```%s```" % '\n'.join(enabled_desc)
    else:
        ret += "No plugins are enabled.\n"

    if disabled:
        ret += "The following plugins are disabled:\n"
        ret += "```%s```" % '\n'.join(disabled_desc)
    else:
        ret += "No plugins are disabled.\n"

    return ret

def cmd_plugson(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) == 0:
        return proc.usage_msg("Please provide the name(s) of one or more plugin(s) you want to enable.",
                             cmd_word)

    args = [x.strip() for x in args]
    for n in args:
        if not proc.bot.plugin_manager.is_valid_plugin_name(n):
            return proc.usage_msg("'%s' is not a valid plugin name" % n,
                                  cmd_word)

    proc.bot.plugin_manager.enable_plugins(plugin_names=args)

    enabled_plugins = [x.plugin_name.lower() for x in proc.bot.plugin_manager.enabled_plugins()]
    if set(enabled_plugins) != set(config.config.enabled_plugins):
        # If enabled plugins changed, save changes to config file
        config.config.enabled_plugins = enabled_plugins
        config.save_to_file()

    return "OK, the following plugins are enabled: %s" % ', '.join(args)

def cmd_plugsoff(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) == 0:
        return proc.usage_msg("Please provide the name(s) of one or more plugin(s) you want to disable.",
                              cmd_word)

    args = [x.strip() for x in args]
    for n in args:
        if not proc.bot.plugin_manager.is_valid_plugin_name(n):
            return proc.usage_msg("'%s' is not a valid plugin name" % n,
                                  cmd_word)

    proc.bot.plugin_manager.disable_plugins(plugin_names=args)

    enabled_plugins = [x.plugin_name.lower() for x in proc.bot.plugin_manager.enabled_plugins()]
    if set(enabled_plugins) != set(config.config.enabled_plugins):
        # If enabled plugins changed, save changes to config file
        config.config.enabled_plugins = enabled_plugins
        config.save_to_file()

    return "OK, the following plugins are disabled: %s" % ', '.join(args)

def cmd_pluginfo(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) == 0:
        return proc.usage_msg("Please provide the name of the plugin you want information about.",
                              cmd_word)

    plugin_name = args[0].strip()
    if not proc.bot.plugin_manager.is_valid_plugin_name(plugin_name):
        return proc.usage_msg("%s is not a valid plugin name." % plugin_name,
                              cmd_word)

    plugin = proc.bot.plugin_manager.get_plugins_by_name([plugin_name])[0]

    long_desc = plugin.plugin_long_description.strip()
    long_desc = '\n'.join([x.strip() for x in long_desc.split('\n')])
    lines = []
    lines.append("%s %s (%s)" % (plugin.plugin_name, plugin.plugin_version,
                                 "enabled" if plugin.enabled else "disabled"))
    lines.append("")
    lines.append(plugin.plugin_short_description)
    lines.append("")
    lines.append(long_desc)

    return ("Here is information about the '%s' plugin:\n```%s```" % (plugin_name, '\n'.join(lines)))

def cmd_twitchclientid(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) != 2:
        return proc.usage_msg("Please provide 2 strings, twitch client ID & twitch client secret.",
                              cmd_word)

    new_client_id = args[0].strip()
    new_client_secret = args[1].strip()

    if not twitch_monitor.reconnect(new_client_id, new_client_secret):
        return "Unable to connect to twitch using that client ID/secret, are you sure they're right?"

    config.config.twitch_client_id = new_client_id
    config.config.twitch_client_secret = new_client_secret
    config.save_to_file()

    return "OK! successfully connected to twitch with your new client ID/secret"

def cmd_announcechannel(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) == 0:
        return "Current stream announcements channel is ```%s```" % config.config.discord_channel_name

    channel_name = args[0].strip()
    if not proc.bot.change_channel(channel_name):
        return ("Couldn't find a discord channel called '%s' in '%s', "
                "are you sure that's the right name?" % (channel_name, proc.bot.guild.name))

    config.config.discord_channel_name = channel_name
    config.save_to_file()

    return "OK! stream announcements will now be sent to the '%s' channel" % channel_name

def cmd_timezone(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) == 0:
        if str(message.author.id) not in config.config.timezones:
            return f"{message.author.mention} no timezone currently assigned for you"

        tz_name = config.config.timezones[str(message.author.id)]
        return f"{message.author.mention} your timezone is:\n```{tz_name}```"

    tz_name = ' '.join([x.strip().lower().replace('_', ' ').replace('/', ' ') for x in args])
    tz_obj = utils.find_timezone_by_name(tz_name)
    if tz_obj is None:
        return f"{message.author.mention} Unable to find a timezone matching '{' '.join(args)}'"

    try:
        del config.config.timezones[str(message.author.id)]
    except KeyError:
        pass

    config.config.timezones[str(message.author.id)] = tz_obj.key
    config.save_to_file()
    return f"{message.author.mention} OK, your timezone is set to:\n```{tz_obj.key}```"

nedry_command_list = [
    # Commands available to everyone
    Command("help", cmd_help, False, CMD_HELP_HELP),
    Command("quote", cmd_quote, False, CMD_QUOTE_HELP),
    Command("timezone", cmd_timezone, False, CMD_TIMEZONE_HELP),

    # Commands only available to admin users
    Command("streamers", cmd_streamers, True, CMD_STREAMERS_HELP),
    Command("addstreamers", cmd_addstreamers, True, CMD_ADDSTREAMERS_HELP),
    Command("removestreamers", cmd_removestreamers, True, CMD_REMOVESTREAMERS_HELP),
    Command("clearallstreamers", cmd_clearallstreamers, True, CMD_CLEARALLSTREAMERS_HELP),
    Command("phrases", cmd_phrases, True, CMD_PHRASES_HELP),
    Command("testphrases", cmd_testphrases, True, CMD_TESTPHRASES_HELP),
    Command("addphrase", cmd_addphrase, True, CMD_ADDPHRASE_HELP),
    Command("removephrases", cmd_removephrases, True, CMD_REMOVEPHRASES_HELP),
    Command("nocompetition", cmd_nocompetition, True, CMD_NOCOMPETITION_HELP),
    Command("cmdhistory", cmd_cmdhistory, True, CMD_CMDHISTORY_HELP),
    Command("say", cmd_say, True, CMD_SAY_HELP),
    Command("plugins", cmd_plugins, True, CMD_PLUGINS_HELP),
    Command("plugson", cmd_plugson, True, CMD_PLUGSON_HELP),
    Command("plugsoff", cmd_plugsoff, True, CMD_PLUGSOFF_HELP),
    Command("pluginfo", cmd_pluginfo, True, CMD_PLUGINFO_HELP),
    Command("twitchclientid", cmd_twitchclientid, True, CMD_TWITCHCLIENTID_HELP),
    Command("announcechannel", cmd_announcechannel, True, CMD_ANNOUNCECHANNEL_HELP),
]
