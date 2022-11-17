# Implements a BotConfig class that handles saving/loading the bot .json
# configuration file from disk.

import json
import time
import logging

from versionedobj import VersionedObject, Serializer, migration

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BotConfig(VersionedObject):
    version = "1.2"
    twitch_client_id = ""
    twitch_client_secret = ""
    discord_bot_api_token = ""
    discord_server_id = 0
    discord_channel_name = ""
    streamers_to_monitor = []
    host_streamer = ""
    silent_when_host_streaming = False
    poll_period_seconds = 600
    stream_start_messages = [
        '{streamer_name} just started streaming! Check them out here: {stream_url}'
    ]
    startup_message = None
    discord_admin_users = []
    discord_joke_tellers = []
    config_write_delay_seconds = 15
    command_log_file = None
    jokes = []

@migration(BotConfig, None, "1.0")
def migrate_none_to_10(attrs):
    return attrs

@migration(BotConfig, "1.0", "1.1")
def migrate_none_10_to_11(attrs):
    attrs["twitch_client_secret"] = ""
    return attrs

@migration(BotConfig, "1.1", "1.2")
def migrate_none_11_to_12(attrs):
    attrs["jokes"] = []
    attrs["discord_joke_tellers"] = []
    return attrs


class BotConfigManager(object):
    def __init__(self, filename):
        self.filename = filename
        self.config = BotConfig()
        self.serializer = Serializer(self.config)
        self.last_write_time = 0

    def write_allowed(self):
        return (time.time() - self.last_write_time) >= float(self.config.config_write_delay_seconds)
   
    def load_from_file(self, filename=None):
        if filename is None:
            filename = self.filename

        return self.serializer.from_file(filename)

    def save_to_file(self, filename=None):
        if filename is None:
            filename = self.filename

        self.serializer.to_file(filename, indent=4)
        self.last_write_time = time.time()
