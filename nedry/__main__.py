# Main entry point for regular bot operation. Reads the configuration file and
# initializes everything.

import argparse
import time
import threading
import random
import os
import logging

from nedry import utils, events
from nedry.discord_bot import DiscordBot
from nedry.twitch_monitor import TwitchMonitor
from nedry.config import BotConfigManager
from nedry.plugin import PluginModuleManager


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


DEFAULT_CONFIG_FILE = "default_bot_config.json"


class RuntimeData(object):
    last_host_obj = None
    streamers = {}


def check_streamers(config, monitor, bot):
    channels = monitor.read_all_streamer_info()
    msgs = []

    # See if host stream status changed state
    host_is_streaming = False
    if config.config.host_streamer is not None:
        host = monitor.read_streamer_info(config.config.host_streamer)
        host_is_streaming = host.is_live
        if RuntimeData.last_host_obj is not None:
            if RuntimeData.last_host_obj.is_live != host.is_live:
                if host.is_live:
                    events.emit(EventType.HOST_STREAM_STARTED)
                    host_stream_started = True
                else:
                    events.emit(EventType.HOST_STREAM_ENDED)

    # If configured, check whether host is streaming before
    # making any announcements
    if config.config.silent_when_host_streaming:
        if host_is_streaming:
            # Host is streaming, make no announcements
            return []

    # Check for any announcements that need to be made
    for c in channels:
        if c.user is None:
            del monitor.usernames[c.username]
            monitor.usernames[c.username] = False
            continue

        if c.name in RuntimeData.streamers:
            if c.is_live != RuntimeData.streamers[c.name].is_live:
                if c.is_live:
                    logger.info("streamer %s went live" % c.name)
                    fmt_args = utils.streamer_fmt_tokens(c.name, c.url)
                    fmt_args.update(utils.bot_fmt_tokens(bot))
                    fmt_args.update(utils.datetime_fmt_tokens())
                    fmtstring = random.choice(config.config.stream_start_messages)
                    msgs.append(fmtstring.format(**fmt_args))
                    events.emit(EventType.TWITCH_STREAM_STARTED, c.name)
                else:
                    logger.info("streamer %s is no longer live" % c.name)
                    events.emit(EventType.TWITCH_STREAM_ENDED, c.name)

        RuntimeData.streamers[c.name] = c

    return msgs

def streamer_check_loop(config, monitor, bot):
    bot.guild_available.wait()

    if config.config.startup_message is not None:
        msg = config.config.startup_message.format(**utils.datetime_fmt_tokens())
        bot.send_stream_announcement(msg)

    while True:
        time.sleep(config.config.poll_period_seconds)

        msgs = check_streamers(config, monitor, bot)

        for msg in msgs:
            logger.debug("sending message to channel '%s'" % config.config.discord_channel_name)
            bot.send_stream_announcement(msg)

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

    monitor = TwitchMonitor(config.config.twitch_client_id, config.config.twitch_client_secret, config.config.streamers_to_monitor)

    bot = DiscordBot(config, monitor)

    plugin_manager = PluginModuleManager(bot, config.config.plugin_directories)
    plugin_manager.load_plugins_from_directories()
    plugin_manager.open_plugins()

    _ = check_streamers(config, monitor, bot)
    thread = threading.Thread(target=streamer_check_loop, args=(config, monitor, bot))
    thread.daemon = True
    thread.start()

    # KeyboardInterrupt will not be bubbled up, instead it will just
    # cause this function to return silently
    bot.run()

    logger.info("Stopping")
    bot.stop()

if __name__ == "__main__":
    main()