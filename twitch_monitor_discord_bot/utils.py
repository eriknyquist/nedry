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

def mockify_text(text):
    return ''.join([text[i] if i % 2 else text[i].upper() for i in range(len(text))])

