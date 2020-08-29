from twitch import TwitchClient


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

    @property
    def url(self):
        return self.channel.url

class TwitchMonitor(object):
    def __init__(self, twitch_client_id, usernames):
        self.client = TwitchClient(client_id=twitch_client_id)
        self.users = self.translate_usernames(usernames)

    def translate_username(self, name):
        ret = self.client.users.translate_usernames_to_ids([name])
        if len(ret) > 0:
            return ret

        return None

    def translate_usernames(self, names, max_per_request=16):
        users = []

        while len(names) > 0:
            req = names[:max_per_request]
            users.extend(self.client.users.translate_usernames_to_ids(req))
            names = names[max_per_request:]

        return users

    def read_streamer_info(self, user):
        channel = self.client.channels.get_by_id(user.id)
        stream = self.client.streams.get_stream_by_user(user.id)
        return TwitchChannel(channel, stream)

    def read_all_streamer_info(self):
        return [self.read_streamer_info(u) for u in self.users]
