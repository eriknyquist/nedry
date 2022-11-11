# Implements a TwitchMonitor class that interacts with the twitch API to
# provide information about the status of streamers being monitored

import twitch


class InvalidTwitchUser(Exception):
    """
    Raised when an invalid twitch username is provided
    """
    pass


class TwitchChannel(object):
    """
    Holds all the bits of information we care about for a single twitch streamer
    """
    def __init__(self, user):
        self.user = user

    @property
    def is_live(self):
        return self.user.is_live

    @property
    def name(self):
        return self.user.display_name

    @property
    def url(self):
        return "https://twitch.tv/" + self.user.display_name


class TwitchMonitor(object):
    """
    Qeurys that status of a list of twitch streamers periodically to determine
    when they start streaming
    """
    def __init__(self, twitch_client_id, twitch_client_secret, usernames):
        self.helix = twitch.Helix(twitch_client_id, twitch_client_secret)
        self.client = None
        self.users = []
        self.usernames = [x.lower() for x in usernames]

    def add_usernames(self, names):
        lnames = [x.lower() for x in names]

        for n in lnames:
            if self.helix.user(n) is None:
                raise InvalidTwitchUser("Twitch user '%s' does not exist" % n)

        self.usernames.extend(lnames)

    def remove_usernames(self, names):
        for name in names:
            lname = name.lower()
            if lname not in self.usernames:
                continue

            self.usernames.remove(lname)

    def clear_usernames(self):
        self.usernames = []

    def username_added(self, name):
        return name in self.usernames

    def read_streamer_info(self, username):
        user = self.helix.user(username)
        return TwitchChannel(user)

    def read_all_streamer_info(self):
        return [self.read_streamer_info(u) for u in self.usernames]
