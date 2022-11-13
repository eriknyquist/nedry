# Implements a TwitchMonitor class that interacts with the twitch API to
# provide information about the status of streamers being monitored

import twitch
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class InvalidTwitchUser(Exception):
    """
    Raised when an invalid twitch username is provided
    """
    pass


class TwitchChannel(object):
    """
    Holds all the bits of information we care about for a single twitch streamer
    """
    count = 0

    def __init__(self, user, username):
        self.user = user
        self.username = username
        self.is_live = False if user is None else user.is_live
        self.name = "Unknown" if user is None else user.display_name
        self.url = "Unknown" if user is None else "https://twitch.tv/" + user.display_name


class TwitchMonitor(object):
    """
    Qeurys that status of a list of twitch streamers periodically to determine
    when they start streaming
    """
    def __init__(self, twitch_client_id, twitch_client_secret, usernames):
        self.helix = twitch.Helix(twitch_client_id, twitch_client_secret)
        self.client = None
        self.users = []
        self.usernames = {x.lower(): (self.helix.user(x) is not None) for x in usernames}

    def add_usernames(self, names):
        lnames = [x.lower() for x in names]
        names_to_add = {}

        for n in lnames:
            if self.helix.user(n) is None:
                raise InvalidTwitchUser("Twitch user '%s' does not exist" % n)

            names_to_add[n] = True

        self.usernames.update(names_to_add)

    def remove_usernames(self, names):
        for name in names:
            lname = name.lower()
            if lname not in self.usernames:
                continue

            del self.usernames[lname]

    def clear_usernames(self):
        self.usernames = {}

    def username_added(self, name):
        return name.lower() in self.usernames

    def read_streamer_info(self, username):
        user = self.helix.user(username)
        return TwitchChannel(user, username)

    def read_all_streamer_info(self):
        return [self.read_streamer_info(u) for u in self.usernames]
