# Main entry point for regular bot operation. Reads the configuration file and
# initializes everything.

import argparse
import time
import random
import threading
import os
import logging

from nedry import utils, events
from nedry.event_types import EventType
from nedry.discord_bot import DiscordBot
from nedry.twitch_monitor import TwitchMonitor
from nedry.config import BotConfigManager
from nedry.plugin import PluginModuleManager

# Import built-in plugin modules
from nedry.builtin_plugins import builtin_plugin_modules


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


DEFAULT_CONFIG_FILE = "default_bot_config.json"


def wait_for_guild_avail(config, bot):
    bot.guild_available.wait()

    if config.config.startup_message is not None:
        msg = config.config.startup_message.format(**utils.datetime_fmt_tokens())
        bot.send_stream_announcement(msg)

    events.emit(EventType.DISCORD_CONNECTED)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', default=None, nargs='?',
            help="Path to bot config file (default=%(default)s)")

    args = parser.parse_args()
    config = None

    if args.config_file is None:
        b = BotConfigManager(DEFAULT_CONFIG_FILE)

        if os.path.isfile(DEFAULT_CONFIG_FILE):
            config = b
        else:
            b.config.enabled_plugins = [x.plugin_name for x in builtin_plugin_modules]
            b.save_to_file()
            print("Created default config file '%s', please add required parameters" %
                  DEFAULT_CONFIG_FILE)
            return
    else:
        config = BotConfigManager(args.config_file)

    result = config.load_from_file()
    if result is not None:
        # Config file migration was performed, log it and save the new file
        logger.info("migrated config file from version %s to version %s" % (result.old_version, result.version_reached))
        config.save_to_file()

    random.seed(time.time())

    # Make sure stream start messages are valid
    for m in config.config.stream_start_messages:
        if not utils.validate_format_tokens(m):
            logger.error("%s: unrecognized format token in config file stream start messages" % config.filename)
            return

    monitor = TwitchMonitor(config)

    bot = DiscordBot(config, monitor)

    plugin_manager = PluginModuleManager(bot, config.config.plugin_directories)

    # Load plugins from external directories
    plugin_manager.load_plugins_from_directories()

    # Load built-in plugins
    for plugin in builtin_plugin_modules:
        plugin_manager.add_plugin_class(plugin)

    plugin_manager.enable_plugins(config.config.enabled_plugins)

    bot.plugin_manager = plugin_manager


    connect_thread = threading.Thread(target=wait_for_guild_avail, args=(config, bot))
    connect_thread.daemon = True
    connect_thread.start()

    # KeyboardInterrupt will not be bubbled up, instead it will just
    # cause this function to return silently
    bot.run()

    logger.info("Stopping")
    bot.stop()              # Shut down discord client
    plugin_manager.stop()   # Shut down all plugins
    config.stop()           # Shut down config file manager

if __name__ == "__main__":
    main()
