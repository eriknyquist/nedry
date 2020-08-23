import os

from twitch import TwitchClient

CLIENTID_ENV_VAR = "SKETIBOT_TWITCH_CLIENTID"

CHANNEL_NAMES = [
    'mrsketi',
    'mrgregles'
]

class TwitchChannel(object):
    def __init__(self, channel, stream):
        self.channel = channel
        self.stream = stream

    @property
    def is_live(self):
        return self.stream is not None

    @property
    def name(self):
        return self.channel.name

def main():
    if CLIENTID_ENV_VAR not in os.environ:
        print("Please set environment variable '%s'." % CLIENTID_ENV_VAR)
        return

    client_id = os.environ[CLIENTID_ENV_VAR]
    client = TwitchClient(client_id=client_id)
    users = client.users.translate_usernames_to_ids(CHANNEL_NAMES)

    channels = []
    for user in users:
        channel = client.channels.get_by_id(user.id)
        stream = client.streams.get_stream_by_user(user.id)
        channels.append(TwitchChannel(channel, stream))

    for c in channels:
        print("%s, live=%s" % (c.name, c.is_live))

if __name__ == "__main__":
    main()
