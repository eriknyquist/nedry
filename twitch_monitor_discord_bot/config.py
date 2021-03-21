# Implements a BotConfig class that handles saving/loading the bot .json
# configuration file from disk.

import json
import time
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


COMMAND_LOG_KEY = "command_log_file"
COMMAND_LOG_DEFAULT = ""

TWITCH_CLIENTID_KEY = "twitch_client_id"
TWITCH_CLIENTID_DEFAULT = ""

DISCORD_TOKEN_KEY = "discord_bot_api_token"
DISCORD_TOKEN_DEFAULT = ""

DISCORD_GUILDID_KEY = "discord_server_id"
DISCORD_GUILDID_DEFAULT = 0

DISCORD_CHANNEL_KEY = "discord_channel_name"
DISCORD_CHANNEL_DEFAULT = ""

POLL_PERIOD_KEY = "poll_period_seconds"
POLL_PERIOD_DEFAULT = 60

CONFIG_FILE_WRITE_DELAY_KEY = "config_write_delay_seconds"
CONFIG_FILE_WRITE_DELAY_DEFAULT = 30

HOST_STREAM_KEY = "host_streamer"
HOST_STREAM_DEFAULT = ""

ADMIN_USERS_KEY = "discord_admin_users"
ADMIN_USERS_DEFAULT = []

SILENT_HOST_STREAM_KEY = "silent_when_host_streaming"
SILENT_HOST_STREAM_DEFAULT = False

STARTUP_MESSAGE_KEY = "startup_message"
STARTUP_MESSAGE_DEFAULT = None

STREAM_START_MESSAGES_KEY = "stream_start_messages"
STREAM_START_MESSAGES_DEFAULT = [
    '{streamer_name} just started streaming! Check them out here: {stream_url}'
]

STREAMER_LIST_KEY = "streamers_to_monitor"


def load_cfg_default(attrs, key, default):
    if key in attrs:
        return attrs[key]

    return default

class BotConfig(object):
    """
    Represents an in-memory copy of the configuration .json file for the bot
    """
    @classmethod
    def from_file(cls, filename):
        return BotConfig(filename)
    
    def __init__(self, filename=None):
        self.filename = filename
        self.last_write_time = 0.0

        if filename is None:
            # No filename passed- use default values
            self.stream_start_messages = STREAM_START_MESSAGES_DEFAULT
            self.twitch_clientid = TWITCH_CLIENTID_DEFAULT
            self.discord_token = DISCORD_TOKEN_DEFAULT
            self.discord_guildid = DISCORD_GUILDID_DEFAULT
            self.discord_channel = DISCORD_CHANNEL_DEFAULT
            self.poll_period_secs = POLL_PERIOD_DEFAULT
            self.host_streamer = HOST_STREAM_DEFAULT
            self.silent_during_host_stream = SILENT_HOST_STREAM_DEFAULT
            self.startup_message = STARTUP_MESSAGE_DEFAULT
            self.admin_users = ADMIN_USERS_DEFAULT
            self.write_delay_seconds = CONFIG_FILE_WRITE_DELAY_DEFAULT
            self.command_log_file = COMMAND_LOG_DEFAULT
            self.streamers = []
        else:
            # Load provided config file
            self.load_from_file(filename)

    def load_from_file(self, filename):
        """
        Load data from a configuration .json file

        :param str filename: Name of .json file to load
        """
        logger.info("loading configuration from %s", filename)

        with open(filename, 'r') as fh:
            attrs = json.load(fh)

        try:
            self.streamers = attrs[STREAMER_LIST_KEY]
        except Exception:
            return None

        self.stream_start_messages = load_cfg_default(attrs, STREAM_START_MESSAGES_KEY, STREAM_START_MESSAGES_DEFAULT)
        self.twitch_clientid = load_cfg_default(attrs, TWITCH_CLIENTID_KEY, TWITCH_CLIENTID_DEFAULT)
        self.discord_token = load_cfg_default(attrs, DISCORD_TOKEN_KEY, DISCORD_TOKEN_DEFAULT)
        self.discord_guildid = load_cfg_default(attrs, DISCORD_GUILDID_KEY, DISCORD_GUILDID_DEFAULT)
        self.discord_channel = load_cfg_default(attrs, DISCORD_CHANNEL_KEY, DISCORD_CHANNEL_DEFAULT)
        self.poll_period_secs = load_cfg_default(attrs, POLL_PERIOD_KEY, POLL_PERIOD_DEFAULT)
        self.host_streamer = load_cfg_default(attrs, HOST_STREAM_KEY, HOST_STREAM_DEFAULT)
        self.silent_during_host_stream = load_cfg_default(attrs, SILENT_HOST_STREAM_KEY, SILENT_HOST_STREAM_DEFAULT)
        self.startup_message = load_cfg_default(attrs, STARTUP_MESSAGE_KEY, STARTUP_MESSAGE_DEFAULT)
        self.admin_users = load_cfg_default(attrs, ADMIN_USERS_KEY, ADMIN_USERS_DEFAULT)
        self.write_delay_seconds = load_cfg_default(attrs, CONFIG_FILE_WRITE_DELAY_KEY, CONFIG_FILE_WRITE_DELAY_DEFAULT)
        self.command_log_file = load_cfg_default(attrs, COMMAND_LOG_KEY, COMMAND_LOG_DEFAULT)

        return self

    def save_to_file(self, filename=None):
        """
        Save current data to configuration .json file.

        :param str filename: Optional filename to write to. If unset, the filename \
                             provided when the object was initialized will be used.

        :return: True if save was successful, False otherwise (saving may fail if \
                the configured cooldown period has not expired since the last write \
                to the configuration .json file)
        :rtype: bool
        """
        if not self.write_allowed():
            # Write delay hasn't expired since last write, do nothing
            return False

        if filename is None:
            filename = self.filename

        logger.info("saving configuration to %s", filename)

        with open(filename, 'w') as fh:
            json.dump({
                TWITCH_CLIENTID_KEY: self.twitch_clientid,
                DISCORD_TOKEN_KEY: self.discord_token,
                DISCORD_GUILDID_KEY: self.discord_guildid,
                DISCORD_CHANNEL_KEY: self.discord_channel,
                STREAMER_LIST_KEY: self.streamers,
                HOST_STREAM_KEY: self.host_streamer,
                SILENT_HOST_STREAM_KEY: self.silent_during_host_stream,
                POLL_PERIOD_KEY: self.poll_period_secs,
                STREAM_START_MESSAGES_KEY: self.stream_start_messages,
                STARTUP_MESSAGE_KEY: self.startup_message,
                ADMIN_USERS_KEY: self.admin_users,
                CONFIG_FILE_WRITE_DELAY_KEY: self.write_delay_seconds,
                COMMAND_LOG_FILE: self.command_log_file
            }, fh, indent=4)

        self.last_write_time = time.time()
        return True

    def write_allowed(self):
        """
        Check if the configured cooldown has elapsed since the last write to the
        configuration .json file

        :return: True if cooldown time has elapsed
        :rtype: bool
        """
        return ((time.time() - self.last_write_time) >= self.write_delay_seconds)
