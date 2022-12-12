import requests
import logging
import threading
import concurrent
import asyncio

from nedry.event_types import EventType
from nedry import events, utils
from nedry.plugin import PluginModule

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

main_event_loop = asyncio.get_event_loop()


MOCK_HELPTEXT = """
{0} [mention]

Repeat the last thing said by a specific user in a "mocking" tone. Replace [mention]
with a mention of the discord user you want to mock.

Example:

@BotName !mock @discord_user
"""

APOLOGIZE_HELPTEXT = """
{0} [mention]

Apologize to a specific user for having mocked them. Replace [mention]
with a mention of the discord user you want to apologize to.

Example:

@BotName !apologize @discord_user
"""


async def _mock_last_message(bot, channel, user_id):
    async for message in channel.history(limit=100):
        content = message.content.strip()
        if (message.author.id == user_id) and not content.startswith(bot.mention()):
            bot.send_message(channel, utils.mockify_text(message.content))
            break


def mock_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    if len(args) == 0:
        return proc.usage_msg("Please mention the user you want to mock.", cmd_word)

    user_id = utils.parse_mention(args[0].strip())
    if user_id is None:
        return "Please mention the user you wish to mock (e.g. '!mock @eknyquist)"

    asyncio.run_coroutine_threadsafe(_mock_last_message(proc.bot, message.channel, user_id), main_event_loop)


def apologize_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    if len(args) == 0:
        return proc.usage_msg("Please mention the user you want to apologise to.", cmd_word)

    user_id = utils.parse_mention(args[0].strip())
    if user_id is None:
        return "Please mention the user you wish to apologise to (e.g. '!apologise @eknyquist)"

    return ("%s, I am truly, deeply sorry for mocking you just now. "
            "I promise I won't do it again, unless someone tells me to."% args[0].strip())


class Mocking(PluginModule):
    """
    Plugin for repeating the last thing someone said in a comical/mocking way
    """
    plugin_name = "mock"
    plugin_version = "1.0.0"
    plugin_short_description = "Repeat the last thing someone said in a funny way"
    plugin_long_description = """
    Adds one new command which allows you to mention a specific discord user, and the
    bot will repeat the last thing that user said in the same channel in a mocking/funny
    way, e.g. "hello there" becomes "HeLlO tHeRe"

    Commands added:

    !mock (see !help mock)
    !apologize (see !help apologize)
    !apologise (see !help apologise)
    """

    def open(self):
        """
        Enables plugin operation; subscribe to events and/or initialize things here
        """
        self.discord_bot.add_command("mock", mock_command_handler, False, MOCK_HELPTEXT)
        self.discord_bot.add_command("apologize", apologize_command_handler, False, APOLOGIZE_HELPTEXT)
        self.discord_bot.add_command("apologise", apologize_command_handler, False, APOLOGIZE_HELPTEXT)

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        self.discord_bot.remove_command("mock")
        self.discord_bot.remove_command("apologize")
        self.discord_bot.remove_command("apologise")
