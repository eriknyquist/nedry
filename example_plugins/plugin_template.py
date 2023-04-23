from nedry.event_types import EventType
from nedry import events
from nedry.plugin import PluginModule

# Docstring displayed when the "!help command1" command is used.
#
# - First format arg will be replaced with command word.
# - "@BotName" will be replaced with a mention of the real discord name of your bot.
COMMAND1_HELPTEXT = """
{0} arg1 arg2

arg1 - Description of arg1

arg2 - Description of arg1

Examples:
@BotName !command1 abc def    (Example of using the command with some arguments)
@BotName !command1 10 11      (Example of using the command with some other arguments)
"""


def command1_handler(cmd_word, args, message, proc, config, twitch_monitor):
    """
    Handler function for 'command1', called whenever someone sends '@BotName !command1'
    in discord

    :param str cmd_word: Command word used to invoke the command, will always be 'command1' in this case.

    :param str args: The remaining text of the command string after the command word. For example, \
        if the discord message received was '@BotName !command1 1 2 3', then 'args' would be '1 2 3'.

    :param message: The discord.Message object containing the command message \
       (https://discordpy.readthedocs.io/en/stable/api.html#discord.Message).

    :param proc: The nedry.command_processor.CommandProcessor instance that is being used \
        to process commands.

    :param config: The nedry.config.BotConfigManager instance which is managing the \
        currently loaded JSON file where all persistent data is stored.

    :param twitch_monitor:  The nedry.twitch_monitor.TwitchMonitor instance that is currently running.


    :return: a string to be returned as the command response in discord, or None
    :rtype: str
    """
    # If a string is returned, it will be used as the response sent to whichever
    # discord channel the command was received in
    return "Response sent to the same discord channel the command was received in"


class PluginTemplate(PluginModule):
    """
    Plugin template showing the boilerplate needed for most plugins
    """
    plugin_name = "Unique and succint plugin name"
    plugin_version = "1.0.0"
    plugin_short_description = "Short one-line description"
    plugin_long_description = """
    Longer description, typically followed by listing the commands added by
    the plugin in the following format...

    Commands added:

    !command1 (see !help command1)
    """

    def startup(self):
        """
        Called once on bot startup, after config file is loaded
        """
        # Check if there is any saved plugin data to load
        if self.plugin_name in self.discord_bot.config.config.plugin_data:
            saved_data = self.discord_bot.config.config.plugin_data[self.plugin_name]
            # ....

    def shutdown(self):
        """
        Called once when bot shuts down / is killed
        """
        # Populate discord_bot.config.config.plugin_data[self.plugin_name] with data
        # we want to persist after shutdown
        plugin_data_to_save = {}
        self.discord_bot.config.config.plugin_data[self.plugin_name] = plugin_data_to_save

        # Tell nedry that changes were made to persistent data that need to be
        # written out to file when we shut down
        self.discord_bot.config.save_to_file()

    def open(self):
        """
        Called when plugin is enabled via !plugson command. Should enable plugin operation,
        e.g. subscribe to events and/or enable custom commands
        """
        # Register command handler function to enable command
        self.discord_bot.add_command(
            "command1",        # Command word
            command1_handler,  # Command handler function
            False,             # If True, command is only available to admin users
            COMMAND1_HELPTEXT  # Help text for command (displayed on "!help command1")
        )

    def close(self):
        """
        Called when plugin is disabled via !plugsoff command. Should disable plugin operation,
        e.g. unsubscribe from events and/or disable custom commands
        """
        # De-register command handler to disable command
        self.discord_bot.remove_command("command1")
