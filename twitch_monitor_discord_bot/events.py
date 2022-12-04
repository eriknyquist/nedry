from twitch_monitor_discord_bot.event_types import EventType


class Event(object):
    """
    Generic event class, use to define all events
    """
    def __init__(self, event_type):
        self._event_type = event_type
        self._handlers = []

    def add_handler(self, handler):
        if handler not in self._handlers():
            self._handlers.append()

        return self

    def remove_handler(self, handler):
        try:
            self._handlers.remove(handler)
        except ValueError:
            pass

        return self

    def emit(self, *event_args, **event_kwargs):
        for handler in self._handlers:
            handler(*event_args, **event_kwargs)

        return self


_event_typenames = [x for x in dir(EventType) if not callable(getattr(EventType, x)) and not x.startswith("__")]
_event_types = [getattr(EventType, x) for x in _event_typenames]
_events = {x: Event(x) for x in _event_types}


def subscribe(event_type, handler):
    """
    Subscribe to an event
    """
    if event_type not in _events:
        raise ValueError("Invalid event type (%d)" % event_type)

    _events[event_type].add_handler(handler)

def unsubscribe(event_type, handler):
    if event_type not in _events:
        raise ValueError("Invalid event type (%d)" % event_type)

    _events[event_type].remove_handler(handler)

def emit(event_type, *event_args, **event_kwargs):
    if event_type not in _events:
        raise ValueError("Invalid event type (%d)" % event_type)

    _events[event_type].emit(*event_args, **event_kwargs)
