# Implements a TwitchMonitor class that interacts with the twitch API to
# provide information about the status of streamers being monitored

import time
import logging
import threading

from nedry import events
from nedry.event_types import EventType

import twitch


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
    def __init__(self, config):
        self.helix = None
        self.users = []
        self.config = config
        self.usernames = {}
        self.request_complete = threading.Event()
        self.discord_connected = threading.Event()
        self.stopped = threading.Event()
        self.request_complete.set()
        self.last_host_obj = None
        self.streamers = {}

        self.thread = threading.Thread(target=self._streamer_check_loop)
        self.thread.daemon = True
        self.thread_running = False

        events.subscribe(EventType.DISCORD_CONNECTED, self._on_discord_connected)

        if self.config.config.twitch_client_id and self.config.config.twitch_client_secret:
            self.reconnect(self.config.config.twitch_client_id, self.config.config.twitch_client_secret)
        else:
            logger.warning("Can't monitor twitch streamers yet, no twitch client ID/secret is set")

    def _on_discord_connected(self):
        self.discord_connected.set()

    def reconnect(self, client_id, client_secret):
        self.request_complete.wait()

        try:
            new_helix = twitch.Helix(client_id, client_secret)
        except:
            return False

        usernames = self.config.config.streamers_to_monitor
        self.helix = new_helix
        self.usernames = {x: (self.helix.user(x.strip()) is not None) for x in usernames}
        logger.info("Connected to twitch")

        if not self.thread_running:
            self.thread.start()
            self.thread_running = True
            logger.info("Started twitch monitor thread")

        return True

    def _check_streamers(self):
        channels = self.read_all_streamer_info()

        # See if host stream status changed state
        host_is_streaming = False
        if self.config.config.host_streamer is not None:
            host = self.read_streamer_info(self.config.config.host_streamer)
            host_is_streaming = host.is_live
            if self.last_host_obj is not None:
                if self.last_host_obj.is_live != host.is_live:
                    if host.is_live:
                        events.emit(EventType.HOST_STREAM_STARTED)
                        host_stream_started = True
                    else:
                        events.emit(EventType.HOST_STREAM_ENDED)

            self.last_host_obj = host

        # Check for any announcements that need to be made
        for c in channels:
            if c.user is None:
                del self.usernames[c.username]
                self.usernames[c.username] = False
                continue

            if c.name in self.streamers:
                if c.is_live != self.streamers[c.name].is_live:
                    if c.is_live:
                        logger.info("streamer %s went live" % c.name)
                        events.emit(EventType.TWITCH_STREAM_STARTED, c.name, c.url)
                    else:
                        logger.info("streamer %s is no longer live" % c.name)
                        events.emit(EventType.TWITCH_STREAM_ENDED, c.name, c.url)

            self.streamers[c.name] = c

    def _check_streamers_retry(self, max_retries=5):
        retry_count = 0

        while True:
            try:
                self._check_streamers()
            except ConnectionResetError as e:
                if retry_count >= max_retries:
                    raise e

                retry_count += 1
                logger.warning(f"ConnectionResetError occurred, retrying ({retry_count}/{max_retries})")
                continue
            else:
                break

    def _streamer_check_loop(self):
        self.discord_connected.wait()

        last_check_time = time.time()
        self._check_streamers_retry()

        while True:
            # Wait for the poll period to expire
            while (time.time() - last_check_time) < self.config.config.poll_period_seconds:
                time.sleep(1.0)
                if self.stopped.is_set():
                    return

            last_check_time += self.config.config.poll_period_seconds
            self._check_streamers_retry()

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

    def _read_streamer_info(self, username):
        user = self.helix.user(username)
        return TwitchChannel(user, username)

    def read_streamer_info(self, username):
        self.request_complete.clear()
        ret = self._read_streamer_info(username)
        self.request_complete.set()
        return ret

    def read_all_streamer_info(self):
        self.request_complete.clear()
        all_info = [self._read_streamer_info(u) for u in self.usernames]
        self.request_complete.set()
        return all_info

    def stop(self):
        self.stopped.set()
        self.thread.join()
