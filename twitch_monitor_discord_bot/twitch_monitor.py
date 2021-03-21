# Implements a TwitchMonitor class that interacts with the twitch API to
# provide information about the status of streamers being monitored

from twitch import TwitchClient


class TwitchChannel(object):
    """
    Holds all the bits of information we care about for a single twitch streamer
    """
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
    """
    Qeurys that status of a list of twitch streamers periodically to determine
    when they start streaming
    """
    def __init__(self, twitch_client_id, usernames):
        self.client = TwitchClient(client_id=twitch_client_id)
        self.users = []
        self.usernames = [x.lower() for x in usernames]
        self._update_users()

    def _update_users(self):
        self.users = self.translate_usernames(self.usernames)

    def _user_by_name(self, name):
        lname = name.lower()
        for i in range(len(self.users)):
            user = self.users[i]
            if user.name.lower() == lname:
                return user, i

        return None, None

    def add_usernames(self, names):
        lnames = [x.lower() for x in names]
        self.usernames.extend(lnames)
        users = self.translate_usernames(lnames)
        self.users.extend(users)

    def remove_usernames(self, names):
        for name in names:
            user, index = self._user_by_name(name)
            if user is None:
                continue

            del self.users[index]

            if name not in self.usernames:
                continue

            self.usernames.remove(name)

    def clear_usernames(self):
        self.users = []
        self.usernames = []

    def username_added(self, name):
        return name in self.usernames

    def translate_username(self, name):
        ret = self.client.users.translate_usernames_to_ids([name])
        if len(ret) > 0:
            return ret[0]

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
