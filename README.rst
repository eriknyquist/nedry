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
        "host_streamer": "my-twitch-streamer-name",
        "silent_when_host_streaming": true,
        "streamers_to_monitor": [
            "mrsketi"
        ]
        "stream_start_messages": [
            "{streamer_name} is now streaming! watch it here: {stream_url}"
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

* ``streamers_to_monitor``: Enter the list of streamer names to monitor here.

* ``stream_start_messages``: Multiple messages can be defined here to be used as announcements
  for streamers going live. Messages may contain the following format tokens:

  * ``{streamer_name}``: will be replaced with the name of the streamer
  * ``{stream_url}``: will be replaced with the stream URL on twitch.com
