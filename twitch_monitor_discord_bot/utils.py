import datetime

FMT_TOK_STREAMER_NAME = "streamer_name"
FMT_TOK_STREAM_URL = "stream_url"

FMT_TOK_DATE = "date"
FMT_TOK_TIME = "time"
FMT_TOK_DAY = "day"
FMT_TOK_MONTH = "month"
FMT_TOK_YEAR = "year"


format_args = {
    FMT_TOK_STREAMER_NAME: None,
    FMT_TOK_STREAM_URL: None,
    FMT_TOK_DATE: None,
    FMT_TOK_TIME: None,
    FMT_TOK_DAY: None,
    FMT_TOK_MONTH: None,
    FMT_TOK_YEAR: None
}

def streamer_fmt_tokens(name, url):
    return {FMT_TOK_STREAMER_NAME: name, FMT_TOK_STREAMER_URL: url}

def datetime_fmt_tokens():
    now = datetime.datetime.now()
    return {
        FMT_TOK_DATE: now.strftime("%d/%m/%Y"),
        FMT_TOK_TIME: now.strftime("%H:%M:%S"),
        FMT_TOK_DAY: now.strftime("%A"),
        FMT_TOK_MONTH: now.strftime("%B"),
        FMT_TOK_YEAR: now.strftime("%Y")
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
