# Implements a BotConfig class that handles saving/loading the bot .json
# configuration file from disk.

import json
import time
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
        self.stop_event = threading.Event()
        self.save_requested = threading.Event()

        self.save_thread = threading.Thread(target=self._save_thread_task)
        self.save_thread.daemon = True
        self.save_thread.start()

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
            self.serializer.to_file(self.filename, indent=4)
            self.save_requested.clear()
            logger.debug(f"flushed new config to {self.filename}")
        else:
            logger.debug("No config changes to flush")

    def stop(self):
        logger.debug("Stopping")
        self.stop_event.set()
        self.save_thread.join()
        self._check_flush_to_file()

    def timezone_by_discord_user_id(self, discord_user_id):
        tz_info = None
        if str(discord_user_id) in self.config.timezones:
            tz_name = self.config.timezones[str(discord_user_id)]
            tz_info = zoneinfo.ZoneInfo(tz_name)

        return tz_info

    def _save_thread_task(self):
        logger.debug("started config file save thread")
        last_save_time = time.time()

        while True:
            # Wait until it's time to check for a requested save
            while (time.time() - last_save_time) < self.SAVE_INTERVAL_SECS:
                time.sleep(1.0)

                if self.stop_event.is_set():
                    self.stop_event.clear()
                    return

            last_save_time = time.time()
            self._check_flush_to_file()
