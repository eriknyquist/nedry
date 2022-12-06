from nedry.command_processor import nedry_command_list
from nedry.builtin_plugins import builtin_plugin_modules

CMD_TITLE_UNDERLINE_CHAR = '-'

for cmd in nedry_command_list:
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
