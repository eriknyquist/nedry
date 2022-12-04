# Implements routines for reading a random quote from a .json file, and replacing
# a random noun or verb with the work "donk"

import string
import os
import json
import random

import nltk
#nltk.download('punkt')
#nltk.download('averaged_perceptron_tagger')

package_dir = os.path.dirname(os.path.realpath(__file__))
DEFAULT_JSON_FILE = os.path.join(package_dir, "quotedb.json")


def _retrieve_quote(json_filename):
    """
    Retrieve a random quote entry from json_filename, very quickly,
    without loading the entire file into memory

    :param str json_filename: Name of .json file to open

    :return: Tuple of the form: (str(quote_text), str(quote_author))
    :rtype: tuple
    """
    text = b''

    with open(json_filename, "rb") as fh:
        fh.seek(0, 2)    # Seek to the end of the file
        fsize = fh.tell() # File size

        # Seek to random file offset
        offs = int((fsize - 1) * random.random())
        fh.seek(offs, 0)

        ch = None
        depth = 0

        # Keep reading single chars backwards until we see an open brace
        while True:
            ch = fh.read(1)

            if ch == b'{':
                text += b'{'
                break

            fh.seek(-2, 1)

        ch = fh.read(1)
        # Now, keep reading single chars until the corresponding closing brace
        while ch != '\n':
            text += ch

            if ch == b'{':
                depth += 1
            elif ch == b'}':
                if depth == 0:
                    break
                else:
                    depth -= 1

            ch = fh.read(1)

        # Should have a parse-able JSON string by now
        decoded = text.decode("utf8")
        attrs = json.loads(decoded)
        return attrs["q"], attrs["a"]


def _find_words_with_tag(text, find_tag):
    sentences = nltk.sent_tokenize(text)
    spans = []
    position = 0

    for sentence in sentences:
        tagged = nltk.pos_tag(nltk.word_tokenize(str(sentence)))

        for i in range(len(tagged)):
            word, tag = tagged[i]
            if (tag in string.punctuation) or (tag == 'POS') or (word == "'nt"):
                continue

            end = position + len(word)
            if (tag == find_tag):
                spans.append((position, end, False))
            elif (find_tag == 'NN') and (tag == 'NNS'):
                spans.append((position, end, True))

            position = end
            while (position < len(text)) and not text[position].isalpha():
                position += 1

    return spans

def _pre_clean(text):
    text = ' '.join(text.split())
    text = text.replace('cannot', 'can not')
    return text

def _post_clean(text):
    # Capitalize
    text = text[0].upper() + text[1:]

    # Remove spaces before commas
    fields = text.split(',')
    text = ','.join([x.rstrip() for x in fields])

    # Remove spaces before periods
    fields = text.split('.')
    text = '.'.join([x.rstrip() for x in fields])

    # Make sure all periods have a space after them
    text = '. '.join([x.strip() for x in text.split('.')])

    return text.strip()

def _process_quote(text):
    sentences = [x.strip() for x in text.split('.')]
    spans = []
    pos = 0

    # Search all sentences for nouns
    for s in sentences:
        vspans = _find_words_with_tag(s, 'NN')

        for start, end, plural in vspans:
            spans.append((start + pos, end + pos, plural))

        extra = 1 if s == '' else 2
        pos += len(s) + extra

    if spans:
        return spans

    pos = 0

    # Search all sentences for verbs
    for s in sentences:
        vspans = _find_words_with_tag(s, 'VB')

        for start, end, plural in vspans:
            spans.append((start + pos, end + pos, plural))

        extra = 1 if s == '' else 2
        pos += len(s) + extra

    return spans

def get_donk_quote(json_filename=DEFAULT_JSON_FILE):
    """
    Retrieve a famous quote with some qord automatically replaced with "donk"

    :param str json_filename: Name of .json file containing quotes

    :return: Tuple of the form (str(quote_text), str(quote_author))
    :rtype: tuple
    """
    quote = None
    words = None
    spans = []

    # Keep grabbing quotes until we get one with at least one verb or noun
    while not spans:
        text, author = _retrieve_quote(json_filename)
        text = _pre_clean(text)
        spans = _process_quote(text)

    # Replace first or last word?
    first = bool(random.getrandbits(1))
    if first:
        span = spans[0]
    else:
        span = spans[-1]

    header = text[:span[0]]
    end = text[span[1]:]
    is_plural = span[2]

    replacement = " donk%s " % ("s" if is_plural else "")
    quote_text = (header.strip() + replacement + end.strip()).strip()
    return _post_clean(quote_text), author
