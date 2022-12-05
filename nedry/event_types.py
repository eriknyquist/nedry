
class EventType(object):
    """
    Enumerates all event types that are managed by the events module
    """
    # Events 0 through 999 are reserved for discord-related events

    # Discord message sent by server member in a public channel,
    # or directly to the bot in a DM
    DISCORD_MESSAGE_RECEIVED = 0

    # Discord message sent by server member in a public channel,
    # or directly to the bot in a DM, and which begins with a direct mention
    # of the bot's name in the discord server.
    DISCORD_BOT_MENTION = 1

    # New member joined the discord server
    NEW_DISCORD_MEMBER = 2

    # Connected to discord server (this sometimes takes a few seconds after startup)
    DISCORD_CONNECTED = 3
    

    # Events 1000 through 1999 are reserved for twitch-related events

    # Monitored twitch stream started
    TWITCH_STREAM_STARTED = 1000

    # Monitored twitch stream started
    TWITCH_STREAM_ENDED = 1001

    # Host twitch streamer started streaming
    HOST_STREAM_STARTED = 1002

    # Host twitch streamer stopped streaming
    HOST_STREAM_ENDED = 1003

