import requests
import datetime

FMT_TOK_STREAMER_NAME = "streamer_name"
FMT_TOK_STREAM_URL = "stream_url"

FMT_TOK_DATE = "date"
FMT_TOK_TIME = "time"
FMT_TOK_TIMES = "times"
FMT_TOK_DAY = "day"
FMT_TOK_MONTH = "month"
FMT_TOK_YEAR = "year"

FMT_TOK_BOT_NAME = "botname"

WIKI_URL = 'https://en.wikipedia.org/w/api.php'

format_args = {
    FMT_TOK_STREAMER_NAME: None,
    FMT_TOK_STREAM_URL: None,
    FMT_TOK_DATE: None,
    FMT_TOK_TIME: None,
    FMT_TOK_TIMES: None,
    FMT_TOK_DAY: None,
    FMT_TOK_MONTH: None,
    FMT_TOK_YEAR: None,
    FMT_TOK_BOT_NAME: None
}

def clean_outer_quotes(text):
    text = text.strip()
    fields = []

    if text.startswith('"') and text.endswith('"'):
        fields = text.split('"')
    elif text.startswith("'") and text.endswith("'"):
        fields = text.split("'")
    else:
        return text

    if len(fields) > 3:
        return text

    return text[1:-1]

def streamer_fmt_tokens(name, url):
    return {FMT_TOK_STREAMER_NAME: name, FMT_TOK_STREAM_URL: url}

def datetime_fmt_tokens():
    now = datetime.datetime.now()
    return {
        FMT_TOK_DATE: now.strftime("%d/%m/%Y"),
        FMT_TOK_TIMES: now.strftime("%H:%M:%S"),
        FMT_TOK_TIME: now.strftime("%H:%M"),
        FMT_TOK_DAY: now.strftime("%A"),
        FMT_TOK_MONTH: now.strftime("%B"),
        FMT_TOK_YEAR: now.strftime("%Y")
    }

def bot_fmt_tokens(bot):
    return {
        FMT_TOK_BOT_NAME: bot.client.user.name
    }

def validate_format_tokens(phrase):
    try:
        phrase.format(**format_args)
    except KeyError:
        return False

    return True

def text_looks_like_url(text):
    if (not text.startswith('http://')) and (not text.startswith('www.')):
        return False

    space_count = 0
    dotcount = 0
    slashcount = 0

    for c in text:
        if c.isspace():
            space_count += 1
        elif c == '.':
            dotcount += 1
        elif c in ['\\', '/']:
            slashcount += 1

    # If it starts with 'http://' or 'www.', has no spaces, 1 or more dots, and
    # 1 or more slashes, then it's probably a long-ish URL
    return (space_count == 0) and (dotcount > 0) and (slashcount > 0)

def mockify_text(text):
    text = text.strip().lower()

    # If message resembles a URL, don't mockify
    if text_looks_like_url(text):
        return None

    return ''.join([text[i] if i % 2 else text[i].upper() for i in range(len(text))])

def parse_mention(mention):
    ret = None

    if mention.startswith('<@') and mention.endswith('>'):
        # Mention of member without nickname
        intval = mention[2:-1]
    elif mention.startswith('<@!') and mention.endswith('>'):
        # Mention of member with nickname
        intval = mention[3:-1]
    else:
        return None

    try:
        ret = int(intval)
    except ValueError:
        return None

    return ret

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

def truncate_text(text, size=80):
    if len(text) > size:
        text = text[:size - 4] + ' ...'

    return text
