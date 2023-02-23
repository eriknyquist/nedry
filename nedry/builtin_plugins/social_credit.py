import time
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
{0} [top]

Show your social credit score.

The scoring algorithm is designed to favour users who interact regularly with the
server, as long as those interactions are not "spread thinly" throughout the server.

For example, posting a lot of messages in a single channel every day may make your score go up,
but posting one message in all channels very infrequently may make your score go down.

Using the command with no arguments shows your own social credit score. Using the command
with a single argument of "top" (e.g. "!socialcredit top") shows the 10 users with the highest
social credit score.

Example:

@BotName !socialcredit                 # Show your social credit score
@BotName !socialcredit top             # Show highest 10 scores
"""


TIME_FACTOR_MAX_SECONDS = 3600 * 24 * 7    # 7 days
INACTIVITY_RESET_SECONDS = 3600 * 24 * 28  # 28 days


# Stores all discord user data at runtime, in a dict keyed by user ID
discord_users_by_id = {}


class DiscordUser(VersionedObject):
    # Discord user ID
    user_id = None

    # Total number of commands sent to bot
    bot_commands_sent = 0

    # Key is channel ID, value is number of messages sent to the channel
    channels_visited = {}

    # Time of last message
    last_msg_time = 0


# Stores all discord user data in config file when bot is not running
class SocialCreditConfig(VersionedObject):
    version = "1.0.0"
    discord_users = ListField(DiscordUser)


def _record_user(user_id):
    if user_id not in discord_users_by_id:
        discord_users_by_id[user_id] = DiscordUser()
        discord_users_by_id[user_id].user_id = user_id

def _record_message(message):
    inactivity_secs = time.time() - discord_users_by_id[message.author.id].last_msg_time
    if inactivity_secs >= INACTIVITY_RESET_SECONDS:
        # If discord user has been inactive for a long time, reset their score
        discord_users_by_id[message.author.id] = DiscordUser()
        discord_users_by_id[message.author.id].user_id = message.author.id

    if message.channel.id not in discord_users_by_id[message.author.id].channels_visited:
        discord_users_by_id[message.author.id].channels_visited[message.channel.id] = 0

    discord_users_by_id[message.author.id].channels_visited[message.channel.id] += 1
    discord_users_by_id[message.author.id].last_msg_time = time.time()

def _on_discord_message_received(message):
    _record_user(message.author.id)
    _record_message(message)

def _on_bot_command_received(message, text):
    if text.startswith(COMMAND_PREFIX + "socialcredit"):
        # Don't add points for requesting credit score
        return

    _record_user(message.author.id)
    _record_message(message)
    discord_users_by_id[message.author.id].bot_commands_sent += 1

def _calculate_score(user):
    total_message_count = 0
    avg_msgs_per_channel = 1.0
    channel_count = len(user.channels_visited)

    for chan_id in user.channels_visited:
        total_message_count += user.channels_visited[chan_id]

    if channel_count:
        avg_msgs_per_channel = float(total_message_count) / float(channel_count)

    secs_since_last_msg = min(time.time() - user.last_msg_time, TIME_FACTOR_MAX_SECONDS)
    time_factor = 1.0 - (secs_since_last_msg / TIME_FACTOR_MAX_SECONDS)

    return int(((total_message_count + channel_count + user.bot_commands_sent) * avg_msgs_per_channel) * time_factor)

def _leaderboard(bot):
    users = [(u, _calculate_score(u)) for u in discord_users_by_id.values()]
    users.sort(key=lambda x: x[1], reverse=True)

    leaders = []
    for user, score in users[:10]:
        discord_user = bot.client.get_user(user.user_id)
        leaders.append(f"{discord_user.display_name}: {score}")

    return "Social Credit Leaderboard:\n```%s```" % '\n'.join(leaders)

def socialcredit_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    if args:
        args = args.split()
        if args[0] == "top":
            return _leaderboard(proc.bot)
        else:
            return f"{message.author.mention} unrecognized argument, see '{COMMAND_PREFIX}help {cmd_word}'"

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

    For example, posting a lot of messages in a single channel every day may make your score go up,
    but posting one message in all channels very infrequently may make your score go down.

    The score for each discord user is calculated in the following way:

    ((MSG_COUNT + CHAN_COUNT + CMD_COUNT) * AVG_MSGS_PER_CHAN) * TIME_FACTOR

    MSG_COUNT: this is the total number of discord messages sent by the user in all public channels,
               or in DMs with the bot.

    CHAN_COUNT: this is the total number of public channels the user has sent a message in

    CMD_COUNT: this is the total number of bot commands the user has performed in public channels,
               or in DMs with the bot.

    AVG_MSGS_PER_CHAN: this is MSG_COUNT divided by CHAN_COUNT

    TIME_FACTOR: this will be between 0.0 and 1.0, depending on the time since the last
    message sent by the discord user. The scale goes up to 7 days. If the discord user
    has sent a message in the last few minutes, TIME_SCALE will be 1.0, and if the discord
    user has sent no messages for 7 days or greater then TIME_SCALE will be 0.0

    If a discord user has been inactive (sent no messages in the server) for 28 days or
    longer, then MSG_COUNT, CHAN_COUNT and CMD_COUNT are reset to 0.

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
