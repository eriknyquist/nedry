import logging

from nedry.event_types import EventType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Event(object):
    """
    Generic event class, use to define all events
    """
    def __init__(self, event_type):
        self._event_type = event_type
        self._handlers = []

    def add_handler(self, handler, first=False):
        """
        Register a handler to this event

        :param handler: the handler to add
        :param bool first: if True, handler will be inserted to the first position\
            of the handler list, so that it runs first when the event is emitted. Otherwise,\
            handler will be appended to the list.
        """
        if handler not in self._handlers:
            if first:
                self._handlers.insert(0, handler)
            else:
                self._handlers.append(handler)

        return self

    def remove_handler(self, handler):
        """
        Unregister a handler from this event

        :param handler: the handler to unregister
        """
        try:
            self._handlers.remove(handler)
        except ValueError:
            pass

        return self

    def emit(self, *event_args, **event_kwargs):
        for handler in self._handlers:
            stop_processing_events = handler(*event_args, **event_kwargs)
            if stop_processing_events:
                break

        return self


_event_typenames = [x for x in dir(EventType) if not callable(getattr(EventType, x)) and not x.startswith("__")]
_event_types = [getattr(EventType, x) for x in _event_typenames]
_events = {x: Event(x) for x in _event_types}


def subscribe(event_type, handler, first=False):
    """
    Subscribe to an event, handler will be called when event is emitted

    :param nedry.event_types.EventType event_type: event type to subscribe to
    :param handler: handler to run when event is emitted
    :param bool first: If true, this handler will run before other handlers when event is emitted
    """
    if event_type not in _events:
        raise ValueError("Invalid event type (%d)" % event_type)

    _events[event_type].add_handler(handler, first)

def unsubscribe(event_type, handler):
    """
    Unsubscribe from an event

    :param nedry.event_types.EventType event_type: event type to ubsubscribe from
    :param handler: handler that was passed when subscribing
    """
    if event_type not in _events:
        raise ValueError("Invalid event type (%d)" % event_type)

    _events[event_type].remove_handler(handler)

def emit(event_type, *event_args, **event_kwargs):
    """
    Emit an event, all handlers will be called with provided args

    :param nedry.event_types.EventType event_type: event type to ubsubscribe from
    """
    if event_type not in _events:
        raise ValueError("Invalid event type (%d)" % event_type)

    logger.debug("event(%d), %s, %s" % (event_type, event_args, event_kwargs))
    _events[event_type].emit(*event_args, **event_kwargs)
