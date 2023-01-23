from unittest import mock
from nedry.discord_bot import DiscordBot
from nedry.plugin import PluginModuleManager
from nedry.command_processor import nedry_command_list
from nedry.builtin_plugins import builtin_plugin_modules
import nedry

import sys
import logging

OUTPUT_FILE = "bot_command_reference.txt"
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

out_lines = []

for cmd in bot.cmdprocessor.cmds.values():
    # Print title
    title = "Command ``%s``" % cmd.word
    out_lines.append(title)
    out_lines.append(CMD_TITLE_UNDERLINE_CHAR * len(title))

    # Print description
    txt = cmd.helptext.format(cmd.word)
    lines = txt.split('\n')
    indented = '\n   '.join(lines)
    out_lines.append('\n::\n\n   ' + indented)

    if cmd.admin_only:
        out_lines.append("   Only discord users registered in 'discord_admin_users' in the bot configuration file may use this command.\n")
    else:
        out_lines.append("   All discord users may use this command.\n")

    out_lines.append('')

with open(OUTPUT_FILE, 'w') as fh:
    fh.write('\n'.join(out_lines))
