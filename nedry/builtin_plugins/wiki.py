import requests
import logging

from nedry.event_types import EventType
from nedry import events, utils
from nedry.plugin import PluginModule

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

WIKI_URL = 'https://en.wikipedia.org/w/api.php'


def _wiki_summary_by_page_title(title):
    params = {
        'action': 'query',
        'format': 'json',
        'titles': title,
        'prop': 'extracts',
        'exintro': True,
        'explaintext': True,
    }

    # Use the search API to search for pages related to text
    try:
        response = requests.get(WIKI_URL, params=params)
    except:
        return None

    data = response.json()
    page = next(iter(data['query']['pages'].values()))
    return page['extract'].strip()

def get_wiki_summary(search_text):
    params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'utf8': 1,
            'srsearch': search_text
    }

    # Use the search API to search for pages related to text
    try:
        response = requests.get(WIKI_URL, params=params)
    except:
        return None

    data = response.json()

    if not data['query']['search']:
        # No results
        return None

    # Just take the 1st search result
    return _wiki_summary_by_page_title(data['query']['search'][0]['title'])

def get_random_wiki_summary():
    url = 'https://en.wikipedia.org/w/api.php'
    params = {
            'action': 'query',
            'format': 'json',
            'list': 'random',
            'utf8': 1,
            'rnnamespace': 0,
            'rnlimit': 1
    }

    try:
        response = requests.get(url, params=params)
    except:
        return None

    data = response.json()

    return _wiki_summary_by_page_title(data['query']['random'][0]['title'])


HELPTEXT = """
{0} [search text]

Search the provided text using Wikipedia's public API, and return the summary text
(generally the first paragraph) of the first page in the search results. If no search
text is provided, then a random Wikipedia article will be selected instead.

Examples:

@BotName !wiki python language   (Show summary of wiki page for Python programming language)
@BotName !wiki                   (Show summary of a random wiki page)
"""


def wiki_command_handler(cmd_word, args, message, proc, config, twitch_monitor):
    """
    Handler for !wiki command
    """
    search_text = args
    if not search_text:
        # If no search text provided, just get a random wiki page
        result = get_random_wiki_summary()
    else:
        result = get_wiki_summary(search_text)

    if not result:
        return "No results found, sorry :("

    result = utils.truncate_text(result, 1500)

    if result.endswith("may refer to:"):
        return "Please be a bit more specific with your search terms"

    return result


class Wikipedia(PluginModule):
    """
    Plugin for returning text results from wikipedia's search API
    """
    plugin_name = "wiki"
    plugin_version = "1.0.0"
    plugin_short_description = "Search wikipedia via discord messages"
    plugin_long_description = """
    This plugin adds a 'wiki' command, allowing you to pass in a string containing search terms
    as arguments, and the bot will perform a wikipedia search, and return a message to the
    same channel in which the command was sent, containing a summary of the first article in
    the search results. If no search terms are given, a random article is provided.

    Commands added:

    !wiki (see !help wiki)
    """

    def open(self):
        """
        Enables plugin operation; subscribe to events and/or initialize things here
        """
        self.discord_bot.add_command("wiki", wiki_command_handler, False, HELPTEXT)

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        self.discord_bot.remove_command("wiki")
