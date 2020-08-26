import argparse
import asyncio
import time
import threading
import os

from twitch import TwitchClient

from sketibot.discord_bot import DiscordBot
from sketibot.config import BotConfig

DEFAULT_CONFIG_FILE = "default_bot_config.json"

main_event_loop = asyncio.get_event_loop()
streamers = {}


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

def read_streamer_info(client, users):
    channels = []
    for user in users:
        channel = client.channels.get_by_id(user.id)
        stream = client.streams.get_stream_by_user(user.id)
        channels.append(TwitchChannel(channel, stream))

    return channels

def check_streamers(config, client, bot, users):
    channels = read_streamer_info(client, users)
    msgs = []
    send_msg = False

    for c in channels:
        if c.name in streamers:
            if c.is_live and not streamers[c.name].is_live:
                send_msg = True

        if send_msg:
            msgs.append("%s is live! watch it here %s" % (c.name, c.url))  
        
        streamers[c.name] = c

    return msgs
    
def streamer_check_loop(config, client, bot, users):
    while True:
        time.sleep(config.poll_period_secs)

        msgs = check_streamers(config, client, bot, users)
        for msg in msgs:
            asyncio.run_coroutine_threadsafe(bot.send_message(msg),
                                             main_event_loop)

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

    client = TwitchClient(client_id=config.twitch_clientid)
    users = client.users.translate_usernames_to_ids(config.streamers)

    bot = DiscordBot(config.discord_token, config.discord_guildid, config.discord_channel)
    thread = threading.Thread(target=streamer_check_loop, args=(config, client, bot, users))
    thread.start()

    bot.run()
    
if __name__ == "__main__":
    main()
