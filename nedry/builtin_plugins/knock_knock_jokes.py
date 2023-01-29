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
    ["Cow says", "No, cow says moo actually"],
    ["Dishes", "Dishes da police, open up!"],
]

class JokeState(object):
    """
    Enumerates all states we can be in while telling a joke or listening to one
    """
    TELLING_1 = 1     # Joke requested, and we have sent 'knock knock'
    TELLING_2 = 2     # 'whos there' received, and we have sent response
    LISTENING_1 = 3   # 'knock knock' seen, and we have sent 'whos there'
    LISTENING_2 = 4   # response to 'whos there' seen, and we have sent 'xx who?'


def joke_exists(joke, config):
    """
    Check if a joke that we heard is *similar* (but not exactly the same, a-la difflib)
    to one that we already know. WOuld be a shame to have 3 copies of the same joke
    because somebody mispelled a word.
    """
    joke_concat = ' '.join(joke)
    available_jokes = BUILTIN_JOKES + config.config.jokes

    for j in available_jokes:
        j_concat = ' '.join(j)
        ratio = SequenceMatcher(None, joke_concat, j_concat).ratio()

        if ratio >= 0.8:
            return True

    return False


class KnockKnockJoke(object):
    """
    Represents a single joke interaction in a single channel, both telling jokes (triggered by !joke
    command) and listening to jokes (triggered by '@BotName knock knock').

    Either one of those triggers creates a new KnockKnockJoke object for the channel it was triggered on.
    """
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
        """
        Handle a bot mention on a channel with a knock-knock joke in progress


        :param str text: message text with the bot mention stripped out
        """
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


def joke_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    """
    Handler for !joke command
    """
    channel_data[message.channel.id] = KnockKnockJoke(config, True, message.author)
    return "%s knock knock!" % message.author.mention


class KnockKnockJokes(PluginModule):
    """
    Plugin for interactive knock-knock jokes. Adds a new "!joke" command, which
    prompts the bot to tell a randomly-selected knock knock joke. You can also
    *tell* jokes to the bot, by saying "@BotName knock knock", and the bot will
    remember any new jokes it sees, and tell them back to you later.
    """
    plugin_name = "knock_knock_jokes"
    plugin_version = "1.0.0"
    plugin_short_description = "Tell knock-knock jokes, and remember jokes told by others"
    plugin_long_description = """
    Adds a '!joke' command, which causes the bot to tell a randomly selected
    interactive knock-knock joke (interactive in that the bot waits for someone
    to say 'who's there?' etc...).

    There are a small number of hard-coded jokes
    that the bot will pick from, however you can also tell jokes to the bot
    (by mentioning the bot and saying some form of 'knock knock', e.g.
    '@BotName Knock knock!', and the bot will remember jokes that it hasn't heard
    before, adding them to the pool of jokes to be randomly selected the next time
    someone asks for a joke.

    Anyone can tell a joke to the bot, and it will respond, however only discord
    user registered as 'joke tellers' can tell jokes that will be remembered by the bot.

    Commands added:

    !joke (see !help joke)
    """

    def _on_mention(self, message, text_without_mention):
        ret = None
        joke_in_progress = None
        chanid = message.channel.id

        # Figure out the current knock-knock-joke state on the message channel
        if chanid in channel_data:
            joke_in_progress = channel_data[chanid]

        if joke_in_progress is not None:
            ret = joke_in_progress.parse(text_without_mention)
            if joke_in_progress.complete:
                channel_data[chanid] = None
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
        self.discord_bot.add_command("joke", joke_command_handler, False, HELPTEXT)

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        events.unsubscribe(EventType.DISCORD_BOT_MENTION, self._on_mention)
        self.discord_bot.remove_command("joke")
        channel_data.clear()
