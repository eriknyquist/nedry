import requests
import random
import html
import time
import threading
import logging

from nedry.plugin import PluginModule
from nedry.event_types import EventType
from nedry import events, utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PLUGIN_NAME = "trivia"
PLUGIN_VERSION = "1.0.0"


category_names = [
    'general knowledge', 'books', 'film', 'music', 'television', 'science',
    'mythology', 'geography', 'history', 'entertainment: art', 'animals'
]

categories_by_id = {}


class TriviaQuestion(object):
    def __init__(self, category, question, answers, correct_answer):
        self.question = question
        self.answers = answers
        self.correct_answer = correct_answer
        self.category = category

    def correct_answer_index(self):
        return self.answers.index(self.correct_answer)

class TriviaSession(object):
    def __init__(self, trivia, thread):
        self.thread = thread
        self.trivia = trivia
        self.responses = []

def populate_categories():
    resp = requests.get(url="https://opentdb.com/api_category.php")
    attrs = resp.json()

    for d in attrs["trivia_categories"]:
        for n in category_names:
            if n.lower() in d["name"].lower():
                categories_by_id[int(d["id"])] = d["name"]

def get_trivia_question():

    dburl = "https://opentdb.com/api.php?amount=1"

    category_ids = list(categories_by_id.keys())
    if category_ids:
        dburl += f"&category={random.choice(category_ids)}"

    resp = requests.get(url=dburl)
    attrs = resp.json()

    q = attrs["results"][0]

    correct_answer = html.unescape(q["correct_answer"])

    answers = (
        [correct_answer] +
        [html.unescape(x) for x in q["incorrect_answers"]]
    )

    random.shuffle(answers)

    newq = TriviaQuestion(html.unescape(q["category"]),
                          html.unescape(q["question"]),
                          answers,
                          correct_answer)

    return newq


TRIVIA_HELPTEXT = """
{0} [time_limit]

Fetch a trivia question from opentdb.com and allow all discord users to provide
an answer until the time limit is up. Whoever provides the correct answer first
wins, and if the correct answer is not provided, then nobody wins. Also keeps track
of scores (number of wins) by discord user ID.

[time_limit] should be replaced with the desired time limit for the question, in seconds.
This parameter is optional; if no time limit is provided then a time limit of 60 seconds
will be used.

Example:

@BotName !trivia
"""

MIN_TIME_SECONDS = 10
DEFAULT_TIME_SECONDS = 60

trivia_by_channel_lock = threading.Lock()
trivia_by_channel = {}


def _increment_score(config, user_id):
    if PLUGIN_NAME not in config.config.plugin_data:
        config.config.plugin_data[PLUGIN_NAME] = {}

    user_id = str(user_id)

    score = 0
    if user_id in config.config.plugin_data[PLUGIN_NAME]:
        score = config.config.plugin_data[PLUGIN_NAME][user_id]

    new_score = score + 1
    config.config.plugin_data[PLUGIN_NAME][user_id] = new_score
    config.save_to_file()
    return new_score


def _trivia_thread_task(discord_bot, time_secs, channel):
    time.sleep(time_secs)

    with trivia_by_channel_lock:
        session = trivia_by_channel.pop(channel.id)

        correct_answers = []
        incorrect_answers = []
        correct_choice = session.trivia.correct_answer_index() + 1

        for i in range(len(session.responses)):
            discord_user, choice = session.responses[i]
            if choice == correct_choice:
                correct_answers.append(discord_user)
            else:
                incorrect_answers.append(discord_user)


        resp = (f'Time is up! The correct answer was:\n'
                f'```{correct_choice}. {session.trivia.correct_answer}```\n')

        score = None
        if correct_answers:
            score = _increment_score(discord_bot.config, correct_answers[0].id)

        if not correct_answers:
            resp += "Unfortunately, nobody picked that answer :("
        elif len(correct_answers) == 1:
            resp += (f"Congratulations {correct_answers[0].mention}, you're the "
                     f"only one who picked the right answer!\n"
                     f"(total win count for {correct_answers[0].mention}: {score})")
        else:
            mentions = utils.list_to_english([f"{x.mention}" for x in correct_answers])
            resp += (f"{mentions} picked the right answer, but {correct_answers[0].mention} "
                     f"picked it first, so they win. Congratulations {correct_answers[0].mention}!\n"
                     f"(total win count for {correct_answers[0].mention}: {score})")

        discord_bot.send_message(channel, resp)


def trivia_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    with trivia_by_channel_lock:
        if message.channel.id in trivia_by_channel:
            return f"{message.author.mention} A trivia question is already in progress, wait until it finishes"

    if len(args) > 0:
        try:
            time_secs = int(args[0])
        except ValueError:
            return (f"{message.author.mention} '{args[0]}' is not a valid time, "
                    f"please provide a number of seconds")

        if time_secs < MIN_TIME_SECONDS:
            return (f"{message.author.mention} '{args[0]}' is too small, time "
                    f"must be at least {MIN_TIME_SECONDS} seconds")
    else:
        time_secs = DEFAULT_TIME_SECONDS

    q = get_trivia_question()
    answers = "\n".join(["```%d. %s```" % (i + 1, q.answers[i]) for i in range(len(q.answers))])

    with trivia_by_channel_lock:
        thread = threading.Thread(target=_trivia_thread_task,
                                  args=(proc.bot, time_secs, message.channel,))
        thread.daemon = True
        thread.start()

        trivia_by_channel[message.channel.id] = TriviaSession(q, thread)

    return ("%s\n\n%s\n\n You have %d seconds to respond with the number of your "
            "desired answer, make sure to mention me!\n\n(Example: \"@%s 1\")" %
            (q.question, answers, time_secs, proc.bot.client.user.name))


class Trivia(PluginModule):
    """
    Plugin for starting an interactive trivia session in the current discord channel
    """
    plugin_name = PLUGIN_NAME
    plugin_version = PLUGIN_VERSION
    plugin_short_description = "Start an interactive trivia session in the current channel"
    plugin_long_description = """
    Allows all discord users to request a trivia question in the current discord channel.
    Uses opentdb.com to fetch a random trivia quesion. Also keeps track of the scores
    (number of correct trivia answers) of all discord users.

    Commands added:

    !trivia (see !help trivia)
    """

    def _handle_trivia_answer(self, session, message, text_without_mention):
        choice = text_without_mention.strip()
        max_choice = len(session.trivia.answers)

        try:
            intchoice = int(text_without_mention.strip())
        except ValueError:
            intchoice = None

        if intchoice is not None:
            if (intchoice <= 0) or (intchoice > max_choice):
                intchoice = None

        if intchoice is None:
            return (f"{message.author.mention} '{choice}' is not a valid choice, "
                    f"please pick a number between 1-{max_choice}")
        else:
            # Check if we already have an answer to this question from this user
            for author, intchoice in session.responses:
                if author.id == message.author.id:
                    return f"{message.author.mention} I already have an answer from you"

            session.responses.append((message.author, intchoice))
            return (f"{message.author.mention} OK, your answer has been recorded")

    def _on_mention(self, message, text_without_mention):
        with trivia_by_channel_lock:
            session = trivia_by_channel.get(message.channel.id, None)
            if session is not None:
                resp = self._handle_trivia_answer(session, message, text_without_mention)
                if resp:
                    self.discord_bot.send_message(message.channel, resp)

    def open(self):
        """
        Enables plugin operation; subscribe to events and/or initialize things here
        """
        populate_categories()
        events.subscribe(EventType.DISCORD_BOT_MENTION, self._on_mention)
        self.discord_bot.add_command("trivia", trivia_command_handler, False, TRIVIA_HELPTEXT)

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        categories_by_id.clear()
        self.discord_bot.remove_command("trivia")