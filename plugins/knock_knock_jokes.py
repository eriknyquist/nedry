import random
from difflib import SequenceMatcher
import logging

from nedry.event_types import EventType
from nedry import events
from nedry.plugin import PluginModule

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


BUILTIN_JOKES = [
    ["Rufus", "Rufus the most important part of your house!"],
    ["Adore", "Adore is between us, open up!"],
    ["Nobel", "Nobel, that's why I had to knock!"],
    ["Hatch", "omg gross you sneezed on me"],
    ["Kenya", "Kenya stop asking me to tell so many jokes please?!"],
    ["Boo", "Sorry, I didn't mean to scare you. Please stop crying."],
    ["Harmony", "Harmony jokes do I have to keep telling here??"],
    ["Wayne", "Wayne dwops are falling, pwease let me in!"],
    ["Anita", "Anita use the bathroom, please let me in!"],
    ["Madam", "Madam foot is stuck in the door, open up!"],
    ["Ben", "Ben knocking for ages now, open up!"],
    ["Robin", "Robin you! now hand over all your izotope plugins..."],
    ["Daisy", "Daisy me rollin', dey hatin..."],
    ["Horsp", "Eew you said horse poo!"],
    ["Interrupting sloth", "INTERRU- Oh dear, I missed it..."],
    ["Stapler", "I'm a stapler, we don't usually have last names"],
    ["Yoda lady", "Such beautiful yodelling!"],
    ["Amish", "You're not a shoe, you're a person!"],
    ["Europe", "No, you're a poo!"],
]

class JokeState(object):
    TELLING_1 = 1     # Joke requested, and we have sent 'knock knock'
    TELLING_2 = 2     # 'whos there' received, and we have sent response
    LISTENING_1 = 3   # 'knock knock' seen, and we have sent 'whos there'
    LISTENING_2 = 4   # response to 'whos there' seen, and we have sent 'xx who?'


def joke_exists(joke, config):
    joke_concat = ' '.join(joke)
    available_jokes = BUILTIN_JOKES + config.config.jokes

    for j in available_jokes:
        j_concat = ' '.join(j)
        ratio = SequenceMatcher(None, joke_concat, j_concat).ratio()

        if ratio >= 0.8:
            return True

    return False


class KnockKnockJoke(object):
    def __init__(self, config, telling, author):
        self.complete = False
        self.config = config
        self.author = author
        self.state = JokeState.TELLING_1 if telling else JokeState.LISTENING_1
        self.is_joke_teller = author.id in config.config.discord_joke_tellers

        self.joke_in_progress = []

        if telling:
            available_jokes = BUILTIN_JOKES + config.config.jokes
            chosen_joke = random.choice(available_jokes)
            self.joke_in_progress = [chosen_joke[0], chosen_joke[1]]

    def parse(self, text):
        ret = None

        if self.state == JokeState.TELLING_1:
            strings = ["who there", "who's there", "whos there", "who is there"]
            cleaned_text = ' '.join(text.strip().lower().split())
            for s in strings:
                if cleaned_text.startswith(s):
                    # next response seen
                    ret = "%s %s " % (self.author.mention, self.joke_in_progress[0])
                    self.state = JokeState.TELLING_2

        elif self.state == JokeState.TELLING_2:
            cleaned_text = ' '.join(text.strip().lower().split())
            if cleaned_text.startswith('%s who' % self.joke_in_progress[0].lower()):
                # Next response seen, finished telling the joke
                ret = "%s %s" % (self.author.mention, self.joke_in_progress[1])
                self.complete = True

        elif self.state == JokeState.LISTENING_1:
            # Just send back the response "XX who?"
            resp_1 = text.strip()
            self.joke_in_progress.append(resp_1)
            self.state = JokeState.LISTENING_2
            return "%s %s who?" % (self.author.mention, resp_1)

        elif self.state == JokeState.LISTENING_2:
            resp_2 = text.strip()
            self.joke_in_progress.append(resp_2)

            responses = ['what a great joke!', 'great joke!', 'good joke!',
                         'good one!', "that's a good one!", "nice joke!"]
            ret = "%s %s" % (self.author.mention, random.choice(responses))

            if self.is_joke_teller:
                # If the user is a joke teller, we should remember this joke.
                # First, check if we already have the same joke.
                if joke_exists(self.joke_in_progress, self.config):
                    ret += " I think I already know that one though."
                else:
                    ret += " I'll remember that one :)"
                    self.config.config.jokes.append([self.joke_in_progress[0], self.joke_in_progress[1]])
                    self.config.save_to_file()

            self.complete = True

        return ret


HELPTEXT = """
{0}

Tells an interactive knock-knock joke.

You can also *tell* knock-knock jokes to the bot, and it will remember new jokes
to tell them back to you later when you send this command.

Any discord users can tell jokes to the bot, but only jokes told by users listed
in 'discord_joke_tellers' in the configuration file will be remembered.

Example:

@BotName !joke
"""

# Tracks in-progress knock knock jokes by channel ID
channel_data = {}


def handler(proc, config, twitch_monitor, args, message):
    channel_data[message.channel.id] = KnockKnockJoke(config, True, message.author)
    return "%s knock knock!" % message.author.mention


class KnockKnockJokes(PluginModule):
    """
    Abstract implementation of a PluginModule class that represents a
    modular / pluggable behaviour of the bot
    """
    plugin_name = "Knock-knock jokes"
    plugin_short_description = "Tell knock-knock jokes, and remember jokes told by others"
    plugin_long_description = ""

    def __init__(self, discord_bot):
        """
        :param bot: discord bot object, which allows you to send messages to discord channels,\
            among other things
        """
        super(KnockKnockJokesPluginModule, self).__init__(discord_bot)
        
        discord_bot.add_command("joke", handler, False, HELPTEXT)

    def _on_mention(self, message, text_without_mention):
        logger.info("got mention: " + text_without_mention)
        ret = None
        joke_in_progress = None
        chanid = message.channel.id

        # Figure out the current knock-knock-joke state on the message channel
        if chanid in channel_data:
            joke_in_progress = channel_data[chanid]

        if joke_in_progress is not None:
            ret = joke_in_progress.parse(text_without_mention)
            if joke_in_progress.complete:
                channel_data[chanid].joke_in_progress = None
        else:
            cleaned = ''.join(text_without_mention.split()).lower()
            if cleaned.startswith('knockknock'):
                # Someone is telling us a joke
                new_joke = KnockKnockJoke(self.config, False, message.author)
                channel_data[chanid] = new_joke
                ret = "%s who's there?" % message.author.mention

        if ret is not None:
            self.discord_bot.send_message(message.channel, ret)

    def open(self):
        """
        Enables plugin operation; subscribe to events and/or initialize things here
        """
        events.subscribe(EventType.DISCORD_BOT_MENTION, self._on_mention)

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        events.unsubscribe(EventType.DISCORD_BOT_MENTION, self._on_mention)
