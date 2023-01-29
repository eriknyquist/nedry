import requests
import logging
import threading
import concurrent
import asyncio
import random

from nedry.event_types import EventType
from nedry import events, utils
from nedry.plugin import PluginModule

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

main_event_loop = asyncio.get_event_loop()


APOLOGIES = [
    "I am deeply sorry for any inconvenience caused.",
    "I am truly sorry for any inconvenience caused, I hope you can forgive me.",
    "Please accept my sincerest apologies.",
    "Please accept my sincerest apologies, I deeply regret the things that have taken place",
    "I regret any mistakes and offer my apologies.",
    "I regret any mistakes and offer my deepest and most sincere apologies.",
    "I apologize for any errors and hope for forgiveness.",
    "I apologize humbly for any misgivings and hope to earn your forgiveness.",
    "My apologies for any confusion or discomfort caused.",
    "My deepest and most sincere apologies for any confusion or discomfort I may have been caused.",
    "I take full responsibility and extend my most sincere apologies.",
    "I accept full responsibility and offer my sincerest and deepest apologies.",
    "I apologize for any negative impact caused by my actions.",
    "I apologize humbly for the negative impacts of my reckless actions.",
    "I humbly apologize for any offence or hurt caused.",
    "I sincerely apologize for any offence or hurt caused, and hope to regain your consideration.",
    "Please accept my apologies for any shortcomings.",
    "Please accept my humblest and sincerest apologies for my misgivings and shortcomings.",
    "My apologies for any disappointment caused.",
    "Please accept my deepest and most sincere of apologies for any disappointment caused.",
    "I regret any trouble caused and extend my apologies.",
    "I deeply regret any trouble and hardships caused by my actions, and would like to extend my sincere apologies.",
    "I apologize for any inconvenience caused by my actions.",
    "I'm very sorry for any difficulties caused by my actions.",
    "I apologize for my actions and any negative effects they may have had.",
    "I'm very sorry for my actions and regret any ill effects resulting from them.",
    "I am truly sorry for any harm or upset caused.",
    "I am truly sorry for any harm or upset caused. I hope we can move past this.",
    "Please accept my apologies for any mistakes made.",
    "Please accept my humblest apologies for any mistakes I may have made.",
    "I take full responsibility for my actions and apologize for any issues caused.",
    "I accept full responsibility for my actions, and would like to offer my apologies for any resulting hardships.",
    "I apologize for any inconvenience or trouble caused by my behavior.",
    "I'm deeply sorry for any hardships you had to endure because of my behavior.",
    "I regret any mistakes and offer my sincerest apologies.",
    "I deeply regret my mistakes and humbly offer my sincere apologies.",
    "I apologize for any errors and hope for understanding and forgiveness.",
    "I apologize for my upsetting behaviour and hope to gain your understanding and forgiveness.",
    "Please accept my apologies for any discomfort or confusion caused.",
    "Please accept my humble and sincere apologies for any discomfort or difficulty you have endured.",
    "I take full responsibility and extend my most humble apologies.",
    "I take full responsibility for this situation and humbly extend my most sincere apologies.",
    "I apologize for any negative impact my actions may have had.",
    "I'd like to offer my sincere apologies for any negative impact my actions may have had.",
    "I am deeply sorry for any offense or hurt caused by my actions.",
    "I am very sorry for any offense or hurt that may have been caused by my actions.",
    "Please forgive any shortcomings on my part and accept my apologies.",
    "Please forgive any shortcomings or misgivings on my part and accept my most humble and sincere apologies.",
    "I regret any difficulties my mistakes may have caused and offer my sincerest apologies.",
    "I truly regret any difficulties or ill effects my mistakes may have caused and offer my humble apologies."
]

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
    args = args.lower().split()
    if len(args) == 0:
        return proc.usage_msg("Please mention the user you want to mock.", cmd_word)

    user_id = utils.parse_mention(args[0].strip())
    if user_id is None:
        return "Please mention the user you wish to mock (e.g. '!mock @eknyquist)"

    asyncio.run_coroutine_threadsafe(_mock_last_message(proc.bot, message.channel, user_id), main_event_loop)


def apologize_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.lower().split()
    if len(args) == 0:
        return proc.usage_msg("Please mention the user you want to apologise to.", cmd_word)

    mention = args[0].strip()
    user_id = utils.parse_mention(mention)
    if user_id is None:
        return "Please mention the user you wish to apologise to (e.g. '!apologise @eknyquist)"

    return f"{mention} {random.choice(APOLOGIES)}"


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
