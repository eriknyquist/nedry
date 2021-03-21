# Main entry point for regular bot operation. Reads the configuration file and
# initializes everything.

import argparse
import time
import threading
import random
import os
import logging

from twitch_monitor_discord_bot import utils
from twitch_monitor_discord_bot.discord_bot import DiscordBot
from twitch_monitor_discord_bot.twitch_monitor import TwitchMonitor
from twitch_monitor_discord_bot.config import BotConfig, STREAM_START_MESSAGES_KEY


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


DEFAULT_CONFIG_FILE = "default_bot_config.json"

streamers = {}

def check_streamers(config, monitor, bot, host_user):
    channels = monitor.read_all_streamer_info()
    msgs = []

    # If configured, check whether host is streaming before
    # making any announcements
    if config.silent_during_host_stream:
        if host_user is not None:
            host = monitor.read_streamer_info(host_user)
            if host.is_live:
                # Host is streaming, make no announcements
                return []

    # Check for any announcements that need to be made
    for c in channels:
        if c.name in streamers:
            if c.is_live and (not streamers[c.name].is_live):
                logger.debug("streamer %s went live" % c.name)
                utils.format_args[utils.FMT_TOK_STREAMER_NAME] = c.name
                utils.format_args[utils.FMT_TOK_STREAM_URL] = c.url
                fmtstring = random.choice(config.stream_start_messages)
                msgs.append(fmtstring.format(**utils.format_args))

        streamers[c.name] = c

    return msgs

def streamer_check_loop(config, monitor, bot, host_user):
    bot.guild_available.wait()

    if config.startup_message is not None:
        bot.send_message(config.startup_message)

    while True:
        time.sleep(config.poll_period_secs)

        msgs = check_streamers(config, monitor, bot, host_user)
        for msg in msgs:
            logger.debug("sending message to channel '%s'" % config.discord_channel)
            bot.send_message(msg)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', default=None, nargs='?',
            help="Path to bot config file (default=%(default)s)")

    args = parser.parse_args()

    if args.config_file is None:
        b = BotConfig()
        b.save_to_file(DEFAULT_CONFIG_FILE)
        print("Created default config file '%s', please add required parameters" %
              DEFAULT_CONFIG_FILE)
        return

    config = BotConfig(args.config_file)

    # Make sure stream start messages are valid
    for m in config.stream_start_messages:
        if not utils.validate_format_tokens(m):
            print("%s: unrecognized format token in %s" % (config.filename,
                                                           STREAM_START_MESSAGES_KEY))
            return

    monitor = TwitchMonitor(config.twitch_clientid, config.streamers)

    host_user = None
    if config.host_streamer not in ["", None]:
        host_user = monitor.translate_username(config.host_streamer)

    bot = DiscordBot(config, monitor)

    _ = check_streamers(config, monitor, bot, host_user)
    thread = threading.Thread(target=streamer_check_loop, args=(config, monitor, bot, host_user))
    thread.daemon = True
    thread.start()

    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()

if __name__ == "__main__":
    main()
