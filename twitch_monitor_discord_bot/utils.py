FMT_TOK_STREAMER_NAME = "streamer_name"
FMT_TOK_STREAM_URL = "stream_url"

format_args = {
    FMT_TOK_STREAMER_NAME: None,
    FMT_TOK_STREAM_URL: None
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
