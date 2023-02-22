import logging
from versionedobj import VersionedObject, Serializer, ListField

from nedry.command_processor import COMMAND_PREFIX
from nedry.plugin import PluginModule
from nedry.event_types import EventType
from nedry import utils, events

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PLUGIN_NAME = "social_credit"
PLUGIN_VERSION = "1.0.0"


SOCIALCREDIT_HELPTEXT = """
{0}

Show your social credit score.

The scoring algorihm is designed to favour users who interact regularly with the
server, as long as those interactions are not "spread thinly" throughout the server.

For example, posting a lot of messages in a single channel may make your score go up,
but posting one message in all channels may make your score go down.

Example:

@BotName !socialcredit
"""


# Stores all discord user data at runtime, in a dict keyed by user ID
discord_users_by_id = {}


class DiscordUser(VersionedObject):
    # Discord user ID
    user_id = None

    # Total number of commands sent to bot
    bot_commands_sent = 0

    # Key is channel ID, value is number of messages sent to the channel
    channels_visited = {}


# Stores all discord user data in config file when bot is not running
class SocialCreditConfig(VersionedObject):
    version = "1.0.0"
    discord_users = ListField(DiscordUser)

def _on_discord_message_received(message):
    logger.info("msg received: " + message.content)

    user_id = message.author.id
    chan_id = message.channel.id

    if user_id not in discord_users_by_id:
        discord_users_by_id[user_id] = DiscordUser()
        discord_users_by_id[user_id].user_id = user_id

    if chan_id not in discord_users_by_id[user_id].channels_visited:
        discord_users_by_id[user_id].channels_visited[chan_id] = 0

    discord_users_by_id[user_id].channels_visited[chan_id] += 1

def _on_bot_command_received(message, text):
    logger.info("cmd received:" + text)

    if text.startswith(COMMAND_PREFIX + "socialcredit"):
        # Don't add points for requesting credit score
        return

    user_id = message.author.id
    chan_id = message.channel.id

    if user_id not in discord_users_by_id:
        discord_users_by_id[user_id] = DiscordUser()
        discord_users_by_id[user_id].user_id = user_id

    discord_users_by_id[user_id].bot_commands_sent += 1

    if chan_id not in discord_users_by_id[user_id].channels_visited:
        discord_users_by_id[user_id].channels_visited[chan_id] = 0

    discord_users_by_id[user_id].channels_visited[chan_id] += 1


def _calculate_score(user):
    total_message_count = 0
    avg_msgs_per_channel = 1.0
    channel_count = len(user.channels_visited)

    for chan_id in user.channels_visited:
        total_message_count += user.channels_visited[chan_id]

    if channel_count:
        avg_msgs_per_channel = float(total_message_count) / float(channel_count)

    return int((total_message_count + channel_count + user.bot_commands_sent) * avg_msgs_per_channel)

def socialcredit_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    if message.author.id not in discord_users_by_id:
        score = 0
    else:
        score = _calculate_score(discord_users_by_id[message.author.id])

    return f"{message.author.mention} Your score is {score:,}"


class SocialCredit(PluginModule):
    """
    Plugin for keeping track of discord user interaction levels,
    e.g. "social credit score" for the discord server
    """
    plugin_name = PLUGIN_NAME
    plugin_version = PLUGIN_VERSION
    plugin_short_description = "'social credit score' based on discord server interaction"
    plugin_long_description = """
    Keeps track of a 'social credit score' for discord users. Scores are based on
    how people interact with the discord server. A higher score is better.

    The intent of the scoring algorithm is to favour users who interact regularly with the
    server, as long as those interactions are not "spread thinly" throughout the server.

    For example, posting a lot of messages in a single channel may make your score go up,
    but posting one message in all channels may make your score go down.

    The score for each discord user is calculated in the following way:

    (MSG_COUNT + CHAN_COUNT + CMD_COUNT) * AVG_MSGS_PER_CHAN

    MSG_COUNT: this is the total number of discord messages sent by the user in all public channels,
               or in DMs with the bot.

    CHAN_COUNT: this is the total number of public channels the user has sent a message in

    CMD_COUNT: this is the total number of bot commands the user has performed in public channels,
               or in DMs with the bot.

    Commands added:

    !socialcredit (see !help socialcredit)
    """

    def startup(self):
        """
        Called once on bot startup, after config file is loaded
        """
        if PLUGIN_NAME in self.discord_bot.config.config.plugin_data:
            config_data = self.discord_bot.config.config.plugin_data[PLUGIN_NAME]
            config = SocialCreditConfig()
            Serializer(config).from_dict(config_data)

            # Load users into dict
            for user in config.discord_users:
                discord_users_by_id[user.user_id] = user

            # Clear list of discord users in config object
            self.discord_bot.config.config.plugin_data[PLUGIN_NAME] = []

    def shutdown(self):
        """
        Called once when bot shuts down / is killed
        """
        config = SocialCreditConfig()
        config.discord_users = ListField(DiscordUser)

        # Populate new config object with all discord user data
        for user_id in discord_users_by_id:
            config.discord_users.append(discord_users_by_id[user_id])

        self.discord_bot.config.config.plugin_data[PLUGIN_NAME] = Serializer(config).to_dict()
        self.discord_bot.config.save_to_file()

    def open(self):
        """
        Enables plugin operation; subscribe to events and/or initialize things here
        """
        self.discord_bot.add_command("socialcredit", socialcredit_command_handler, False, SOCIALCREDIT_HELPTEXT)
        events.subscribe(EventType.DISCORD_MESSAGE_RECEIVED, _on_discord_message_received)
        events.subscribe(EventType.BOT_COMMAND_RECEIVED, _on_bot_command_received)

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        self.discord_bot.remove_command("socialcredit")
        events.unsubscribe(EventType.DISCORD_MESSAGE_RECEIVED, _on_discord_message_received)
        events.unsubscribe(EventType.BOT_COMMAND_RECEIVED, _on_bot_command_received)
