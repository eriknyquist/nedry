# Implements a BotConfig class that handles saving/loading the bot .json
# configuration file from disk.

import logging
import threading
import zoneinfo

from versionedobj import VersionedObject, Serializer, migration

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BotConfig(VersionedObject):
    version = "1.6"
    twitch_client_id = ""
    twitch_client_secret = ""
    discord_bot_api_token = ""
    discord_server_id = 0
    discord_channel_name = ""
    plugin_directories = []
    enabled_plugins = []
    plugin_data = {}
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
    command_log_file = None
    jokes = []
    timezones = {}

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

@migration(BotConfig, "1.2", "1.3")
def migrate_none_12_to_13(attrs):
    attrs["plugin_directories"] = []
    return attrs

@migration(BotConfig, "1.3", "1.4")
def migrate_none_13_to_14(attrs):
    attrs["enabled_plugins"] = []
    return attrs

@migration(BotConfig, "1.4", "1.5")
def migrate_none_14_to_15(attrs):
    attrs["timezones"] = {}
    return attrs

@migration(BotConfig, "1.5", "1.6")
def migrate_none_15_to_16(attrs):
    del attrs["config_write_delay_seconds"]
    attrs["plugin_data"] = {}
    return attrs


class BotConfigManager(object):
    SAVE_INTERVAL_SECS = 3600 # 1 hour

    def __init__(self, filename):
        self.filename = filename
        self.config = BotConfig()
        self.serializer = Serializer(self.config)
        self.save_requested = threading.Event()

    def load_from_file(self, filename=None):
        if filename is None:
            filename = self.filename

        logger.debug(f"loading configuration file {filename}")
        return self.serializer.from_file(filename)

    def save_to_file(self):
        self.save_requested.set()
        logger.debug("flush to config file requested")

    def _check_flush_to_file(self):
        # If save was requested, flush current config data to file
        if self.save_requested.is_set():
            # Serialize to JSON string first (instead of serializing directly
            # into the file), if there is an exception raised when serializing
            # we don't want to blow away the old config data.
            json_str = self.serializer.to_json(self.config, indent=4)

            with open(self.filename, 'w') as fh:
                fh.write(json_str)

            self.save_requested.clear()
            logger.debug(f"flushed new config to {self.filename}")
        else:
            logger.debug("No config changes to flush")

    def stop(self):
        logger.debug("Stopping")
        self._check_flush_to_file()

    def timezone_by_discord_user_id(self, discord_user_id):
        tz_info = None
        if str(discord_user_id) in self.config.timezones:
            tz_name = self.config.timezones[str(discord_user_id)]
            tz_info = zoneinfo.ZoneInfo(tz_name)

        return tz_info
