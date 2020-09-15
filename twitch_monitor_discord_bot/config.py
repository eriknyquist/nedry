import json
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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

HOST_STREAM_KEY = "host_streamer"
HOST_STREAM_DEFAULT = ""

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
    @classmethod
    def from_file(cls, filename):
        return BotConfig(filename)
    
    def __init__(self, filename=None):
        self.filename = filename
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
            self.streamers = []
        else:
            # Load provided config file
            self.load_from_file(filename)

    def load_from_file(self, filename):
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

        return self

    def save_to_file(self, filename=None):
        logger.info("saving configuration to %s", filename)

        if filename is None:
            filename = self.filename

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
                STARTUP_MESSAGE_KEY: self.startup_message
            }, fh, indent=4)
