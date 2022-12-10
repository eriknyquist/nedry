from unittest import mock
from nedry.discord_bot import DiscordBot
from nedry.plugin import PluginModuleManager
from nedry.command_processor import nedry_command_list
from nedry.builtin_plugins import builtin_plugin_modules

CMD_TITLE_UNDERLINE_CHAR = '-'

with mock.patch('nedry.discord_bot.discord') as mock_discord:
    bot = DiscordBot(mock.MagicMock(), mock.MagicMock())
    plugin_manager = PluginModuleManager(bot, [])

# Load built-in plugins
names = []
for plugin in builtin_plugin_modules:
    plugin_manager.add_plugin_class(plugin)
    names.append(plugin.plugin_name)

plugin_manager.enable_plugins(names)

for cmd in bot.cmdprocessor.cmds.values():
    # Print title
    title = "Command ``%s``" % cmd.word
    print(title)
    print(CMD_TITLE_UNDERLINE_CHAR * len(title))

    # Print description
    txt = cmd.helptext.format(cmd.word)
    lines = txt.split('\n')
    indented = '\n   '.join(lines)
    print('\n::\n\n   ' + indented)

    if cmd.admin_only:
        print("   Only discord users registered in 'admin_users' in the bot config. file may use this command.\n")
    else:
        print("   All discord users may use this command.\n")
