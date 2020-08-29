import argparse
import asyncio
import time
import threading
import random
import os
import logging

from twitch import TwitchClient

from twitch_monitor_discord_bot.discord_bot import DiscordBot
from twitch_monitor_discord_bot.config import BotConfig, STREAM_START_MESSAGES_KEY


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


DEFAULT_CONFIG_FILE = "default_bot_config.json"

main_event_loop = asyncio.get_event_loop()
streamers = {}

FMT_TOK_STREAMER_NAME = "streamer_name"
FMT_TOK_STREAM_URL = "stream_url"

format_args = {
    FMT_TOK_STREAMER_NAME: None,
    FMT_TOK_STREAM_URL: None
}

class TwitchChannel(object):
    def __init__(self, channel, stream):
        self.channel = channel
        self.stream = stream

    @property
    def is_live(self):
        return self.stream is not None

    @property
    def name(self):
        return self.channel.name

    @property
    def url(self):
        return self.channel.url

def read_streamer_info(client, user):
    channel = client.channels.get_by_id(user.id)
    stream = client.streams.get_stream_by_user(user.id)
    return TwitchChannel(channel, stream)

def read_all_streamer_info(client, users):
    return [read_streamer_info(client, u) for u in users]

def check_streamers(config, client, bot, users, host_user):
    channels = read_all_streamer_info(client, users)
    msgs = []

    # If configured, check whether host is streaming before
    # making any announcements
    if config.silent_during_host_stream:
        if host_user is not None:
            host = read_streamer_info(host_user)
            if host.is_live:
                # Host is streaming, make no announcements
                return []

    # Check for any announcements that need to be made
    for c in channels:
        if c.name in streamers:
            if c.is_live and (not streamers[c.name].is_live):
                logger.debug("streamer %s went live" % c.name)
                format_args[FMT_TOK_STREAMER_NAME] = c.name
                format_args[FMT_TOK_STREAM_URL] = c.url
                fmtstring = random.choice(config.stream_start_messages)
                msgs.append(fmtstring.format(**format_args))

        streamers[c.name] = c

    return msgs
    
def streamer_check_loop(config, client, bot, users, host_user):
    while True:
        time.sleep(config.poll_period_secs)

        msgs = check_streamers(config, client, bot, users, host_user)
        for msg in msgs:
            asyncio.run_coroutine_threadsafe(bot.send_message(msg),
                                             main_event_loop)

def translate_usernames(client, names, max_per_request=16):
    users = []

    while len(names) > 0:
        req = names[:max_per_request]
        users.extend(client.users.translate_usernames_to_ids(req))
        names = names[max_per_request:]

    return users

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
        try:
            dd = m.format(**format_args)
        except KeyError:
            print("%s: unrecognized format token in %s" % (config.filename,
                                                           STREAM_START_MESSAGES_KEY))
            return

    client = TwitchClient(client_id=config.twitch_clientid)
    users = translate_usernames(client, config.streamers)

    host_user = None
    if config.host_streamer not in ["", None]:
        host_user = client.users.translate_usernames_to_ids([config.host_streamer])[0]

    bot = DiscordBot(config.discord_token, config.discord_guildid, config.discord_channel)

    _ = check_streamers(config, client, bot, users, host_user)
    thread = threading.Thread(target=streamer_check_loop, args=(config, client, bot, users, host_user))
    thread.start()

    bot.run()
    
if __name__ == "__main__":
    main()
