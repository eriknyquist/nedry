import os
import logging
import textwrap

from nedry.plugin import PluginModule
from nedry import utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PLUGIN_NAME = "stories"
PLUGIN_VERSION = "1.0.0"

LINE_WIDTH = 80

PROMPTS_FILE = os.path.join(os.path.dirname(__file__), "writing_prompts.txt")

STORY_HELPTEXT = """
{0} new|add|continue|show|stop [optional story contribution text]

Interact with the story being written on the current discord channel.

The first argument to this command may be one of the following 5 operations:

new      - Start a new story in this channel.

add      - Contribute the next part of the story being written on this channel.
           [optional story contribution text] should be replaced with your desired
           text for the next part of the story.

continue - Instead of starting a new story with a random prompt, add to an existing
           story by providing the whole story. [optional story contribution text]
           should be replaced with the text of the story that you want to continue.
           (Note: if your story is too large to fit in a single discord message,
           you may need to start with a smaller portion of the story, and afterwards
           add the remaining text using the '!story add' command)

show     - Show the current story as written so far.

stop     - Stop the story writing session, and show the story as written so far.

Examples:

@BotName !story new                            (Provide a random prompt to start a new story)
@BotName !story add And then he fell down...   (Contribute to the current story)
@BotName !story continue Call me Ishmael       (Start new story with provided text, no prompt)
@BotName !story show                           (Show the story as written so far)
@BotName !story stop                           (Stop the story)
"""

stories_by_channel = {}


class StoryContribution(object):
    """
    Represents a story contribution by a specific discord user in a specific channel
    """
    def __init__(self, discord_user_id, text):
        self.discord_user_id = discord_user_id
        self.text = text

    def to_json(self):
        return str(self.discord_user_id) + ":" + self.text

    @classmethod
    def from_json(cls, attrs):
        # 'attrs' is just a string in this case
        id_str, text = attrs.split(':', 1)
        return StoryContribution(int(id_str), text)


class StorySession(object):
    """
    Represents a single story written by multiple discord users in a single channel
    """
    def __init__(self, prompt):
        self.prompt = prompt
        self.contributions = []

    def to_json(self):
        return {
            "prompt": self.prompt,
            "contribs": [x.to_json() for x in self.contributions]
        }

    @classmethod
    def from_json(cls, attrs):
        session = StorySession(attrs["prompt"])

        for c in attrs["contribs"]:
            session.add_contribution(StoryContribution.from_json(c))

        return session

    def add_contribution(self, contribution):
        self.contributions.append(contribution)

    def dump_story(self):
        ret = ""
        lines = [self.prompt] if self.prompt else []
        lines += [x.text for x in self.contributions]
        for c in lines:
            text = c.strip()
            if text[-1] not in ['.', '?', '!', ':', ';', '-']:
                text += '.'

            ret += text + ' '

        return textwrap.fill(ret, LINE_WIDTH)


def _handle_new_op(cmd_word, proc, message):
    if message.channel.id in stories_by_channel:
        return proc.usage_msg(f"{message.author.mention} Story already in progress in this channel, "
                              f"stop the current story before starting a new one.", cmd_word)

    prompt = utils.random_line_from_file(PROMPTS_FILE)
    session = StorySession(prompt)
    stories_by_channel[message.channel.id] = session

    mention = ""
    if hasattr(message.channel, 'mention'):
        mention = message.channel.mention
    else:
        mention = message.author.mention

    return (f"{mention} Let's write a story! I will start you off with a prompt, "
            f"and you can add to the story using the '!story add' command.\n\n"
            f"Here is your prompt:\n```{prompt}```")

def _handle_add_op(cmd_word, proc, message, text):
    if message.channel.id not in stories_by_channel:
        return proc.usage_msg(f"{message.author.mention} No story is in progress on this channel, "
                              f"you must start a new one before adding to it", cmd_word)

    if text == '':
        return proc.usage_msg(f"{message.author.mention} Please provide some text for the story.",
                              cmd_word)

    session = stories_by_channel[message.channel.id]
    session.add_contribution(StoryContribution(message.author.id, text))

    return f"{message.author.mention} Got it, thank you for your story contribution!"

def _handle_continue_op(cmd_word, proc, message, text):
    if message.channel.id in stories_by_channel:
        return proc.usage_msg(f"{message.author.mention} Story already in progress in this channel, "
                              f"stop the current story before starting a new one.", cmd_word)

    if text == '':
        return proc.usage_msg(f"{message.author.mention} Please provide some text for the story.",
                              cmd_word)

    session = StorySession(None)
    session.add_contribution(StoryContribution(message.author.id, text))
    stories_by_channel[message.channel.id] = session

    return f"{message.author.mention} Got it, I have started a new story using the text you provided!"

def _handle_show_op(cmd_word, proc, message):
    if message.channel.id not in stories_by_channel:
        return proc.usage_msg(f"{message.author.mention} No story is in progress on this channel.",
                              cmd_word)

    session = stories_by_channel[message.channel.id]
    story = session.dump_story()
    return f"{message.author.mention} Here is the story so far:\n```{story}```"

def _handle_stop_op(cmd_word, proc, message):
    if message.channel.id not in stories_by_channel:
        return proc.usage_msg(f"{message.author.mention} No story is in progress on this channel.",
                              cmd_word)

    session = stories_by_channel[message.channel.id]
    story = session.dump_story()
    del stories_by_channel[message.channel.id]

    return f"{message.author.mention} OK, story stopped. Here is your story:\n```{story}```"

def story_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    args = args.split()
    if len(args) == 0:
        return proc.usage_msg(f"{message.author.mention} Command requires more information.", cmd_word)

    op = args[0].strip().lower()
    if op not in ['new', 'add', 'continue', 'stop', 'show']:
        return proc.usage_msg(f"{message.author.mention} Unrecognized operation.", cmd_word)

    if 'new' == op:
        return _handle_new_op(cmd_word, proc, message)
    elif 'add' == op:
        return _handle_add_op(cmd_word, proc, message, ' '.join(args[1:]).strip())
    elif 'continue' == op:
        return _handle_continue_op(cmd_word, proc, message, ' '.join(args[1:]).strip())
    elif 'show' == op:
        return _handle_show_op(cmd_word, proc, message)
    elif 'stop' == op:
        return _handle_stop_op(cmd_word, proc, message)


class Stories(PluginModule):
    """
    Plugin for writing prompts and collaborative story writing.
    """
    plugin_name = PLUGIN_NAME
    plugin_version = PLUGIN_VERSION
    plugin_short_description = "Writing prompts and collaborative story writing"
    plugin_long_description = """
    Provides a random writing prompt, and collects story fragments from discord users
    to collaboritvely write a story.

    Commands added:

    !story (see !help story)
    """

    def startup(self):
        """
        Called once on bot startup, after config file is loaded
        """
        if PLUGIN_NAME in self.discord_bot.config.config.plugin_data:
            stories = self.discord_bot.config.config.plugin_data[PLUGIN_NAME]

            for chan_id_str in stories:
                chan_id = int(chan_id_str)
                attrs = stories[chan_id_str]
                stories_by_channel[chan_id] = StorySession.from_json(attrs)

    def shutdown(self):
        """
        Called once when bot shuts down / is killed
        """
        serialized = {}
        for chan_id in stories_by_channel:
            session = stories_by_channel[chan_id]
            serialized[str(chan_id)] = session.to_json()

        self.discord_bot.config.config.plugin_data[PLUGIN_NAME] = serialized
        self.discord_bot.config.save_to_file()

    def open(self):
        """
        Enables plugin operation; subscribe to events and/or initialize things here
        """
        self.discord_bot.add_command("story", story_command_handler, False, STORY_HELPTEXT)

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        self.discord_bot.remove_command("story")
