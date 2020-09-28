twitch_monitor_discord_bot
==========================

This is a discord bot which will periodically check a list of twitch streamers,
and post an announcement on a specific discord channel when a streamer goes live.

Install
=======

Install for Python3 using ``pip``:

::

    python3 -m pip install twitch_monitor_discord_bot

Usage
=====

Run ``twitch_monitor_discord_bot`` as a python module:

::

    python3 -m twitch_monitor_discord_bot bot_config.json

Where ``bot_config.json`` is your configuration file. See the following section
for details about creating a configuration file.

Configuration file
------------------

The configuration file must be a .json file of the following form:

::

    {
        "twitch_client_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "discord_bot_api_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "discord_server_id": 123456789123456789,
        "discord_channel_name": "my-discord-channel",
        "poll_period_seconds": 60,
        "config_write_delay_seconds": 60,
        "host_streamer": "my-twitch-streamer-name",
        "silent_when_host_streaming": true,
        "discord_admin_users" : [422222187366187010, 487222187346187011],
        "startup_message": "Hello! I am a bot who can monitor twitch streams for you.",
        "streamers_to_monitor": [
            "mrsketi",
            "none_of_many"
        ]
        "stream_start_messages": [
            "{streamer_name} is now streaming! watch it here: {stream_url}",
            "{streamer_name} is doing something, go see it here: {stream_url}"
        ]
    }

Description of fields
#####################

* ``twitch_client_id``: Enter your Twitch client ID here.

* ``discord_bot_api_token``: Enter the API token for your discord bot application here.

* ``discord_server_id``: Enter the server ID for the server you want the bot to connect to here.

* ``discord_channel_name``: Enter the name of the channel you want the bot to connect to here.

* ``poll_period_seconds``: Enter the desired delay (in seconds) between checking if all streamers are live here.

* ``host_streamer``: Enter the name of your own twitch channel here (optional).

* ``silent_when_host_streaming``: If true, no announcements about other streams will be made when host streamer is live.

* ``discord_admin_user``: Multiple discord user ID numbers can be added here. Users added
  here will be allowed to configure the bot by sending commands in discord.

* ``config_write_delay_seconds``: Enter the desired cooldown time (in seconds) for commands that
  write changes to the bot config file here (makes it more difficult for someone with admin privileges to spam the disk).

* ``startup_message``: Enter the message you would like the bot to send when it comes online after being started up here.

* ``streamers_to_monitor``: Enter the list of streamer names to monitor here.

* ``stream_start_messages``: Multiple messages can be defined here to be used as announcements
  for streamers going live. Messages may contain the following format tokens:

  * ``{streamer_name}``: will be replaced with the name of the streamer
  * ``{stream_url}``: will be replaced with the stream URL on twitch.com
