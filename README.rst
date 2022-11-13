twitch_monitor_discord_bot
==========================

This is a discord bot which will periodically check a list of twitch streamers,
and post an announcement on a specific discord channel when a streamer goes live.
It also does some other silly/fun things.

Install
=======

Install for Python3 using ``pip``:

::

    python3 -m pip install twitch_monitor_discord_bot

Quick start
===========

Initial configuration
---------------------

#. Run the package as a module with no arguments, which will create an empty configuration
   file called ``default_bot_config.json`` in your current directory and exit immediately.

   ::

       $ python -m twitch_monitor_discord_bot

       [2021-09-19 16:44:40,468][INFO][config:141]: saving configuration to default_bot_config.json
       Created default config file 'default_bot_config.json', please add required parameters

#. Most of the behaviours of this bot can be configured via discord messages while the
   bot is up and running, but there are a few parameters that need to be set in the configuration
   file first, to get the bot talking. Populate these required parameters in the .json file:

   #. ``twitch_client_id``: Twitch client ID must be entered here as a string.
      You must have a twitch account, and register an application to obtain a client ID for your application.
      `instructions here <https://dev.twitch.tv/docs/authentication/register-app>`_.

   #. ``twitch_client_secret``: Twitch client secret must be entered here as a string.
      You must have a twitch account, and register an application to obtain a client secret for your application.
      `instructions here <https://dev.twitch.tv/docs/authentication/register-app>`_.

   #. ``discord_bot_api_token``: Discord bot API token must be entered here as a string.
      `Create a new bot application, and generate/copy token on the "Bot" page <https://discord.com/developers/applications>`_
      (NOTE: make sure to enable all Privileged Gateway Intents for your bot application).

   #. ``discord_server_id``: Discord server ID (the server that you want the bot to
      connect to) must be entered here as an integer.
      `How to find discord user/server/message IDs <https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID->`_

   #. ``discord_server_channel_name``: Discord channel name (the channel within the discord
      server where the bot should post updates about twitch streamers that are being monitored)
      must be entered here as a string.

   #. ``discord_admin_users``: A list of discord user IDs as integers may be  entered here.
      Admin users have access to the full set of discord commands that the bot can accept.
      At the very least, you'll probably want to add your own discord user ID here so that
      you have full control of the bot.
      `How to find discord user/server/message IDs <https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID->`_

   #. ``host_streamer``: If you are a streamer yourself, enter your twitch name here as a string,
      so that the bot can avoid posting notifications about other streamers when you are live.
      (NOTE: this is optional, you may set this to null or an empty string if desired)

#. Once all required parameters have been set in the .json file, run the package as a module
   again, but this time pass your configuration file as an argument:

   ::

       $ python -m twitch_monitor_discord_bot default_bot_config.json


   If configured correctly, then the bot should now connect to your discord server.

Interacting with the bot on discord
-----------------------------------

Whenever your bot is online in the discord server, you can issue commands to the bot
by putting a mention of the bot's discord name at the beginning of the message, e.g.
``@BotName !command``. The only command you really need to know is the ``help`` command;
if you say ``@BotName !help``, then the bot will show you what commands are available
and show you how to get help with individual commands.

The first thing you'll probably want to do is add some twitch streamers to monitor--
there's a command for that! Try ``@BotName !help addstreamers`` to learn how to do that.


Configuration file details
==========================

This section covers all configuration file parameters, including those not covered
in the Quick Start section. The configuration file must be a .json file of the following form:

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
        "command_log_file" : "/home/user/twitch_monitor_bot_command_log.txt",
        "startup_message": "Hello! I am a bot who can monitor twitch streams for you.",
        "streamers_to_monitor": [
            "mrsketi",
            "none_of_many"
        ],
        "stream_start_messages": [
            "{streamer_name} is now streaming! watch it here: {stream_url}",
            "{streamer_name} is doing something, go see it here: {stream_url}"
        ]
    }

Description of fields
---------------------

* ``twitch_client_id``: Enter your Twitch client ID here.

* ``discord_bot_api_token``: Enter the API token for your discord bot application here.

* ``discord_server_id``: Enter the server ID for the server you want the bot to connect to here.

* ``discord_channel_name``: Enter the name of the channel you want the bot to connect to here.

* ``poll_period_seconds``: Enter the desired delay (in seconds) between checking if all streamers are live here.

* ``host_streamer``: Enter the name of your own twitch channel here (optional).

* ``silent_when_host_streaming``: If true, no announcements about other streams will be made when host streamer is live.

* ``discord_admin_users``: Multiple discord user ID numbers can be added here. Users added
  here will be allowed to configure the bot by sending commands in discord.

* ``command_log_file``: Enter desired filename to log commands received from discord messages.
  Set to "null" if you don't want to log commands.

* ``config_write_delay_seconds``: Enter the desired cooldown time (in seconds) for commands that
  write changes to the bot config file here (makes it more difficult for someone with admin privileges to spam the disk).

* ``startup_message``: Enter the message you would like the bot to send when it comes online after being started up here.
  Message may contain the following format tokens:

  * ``{date}`` : will be replaced with current date in DD/MM/YYY format
  * ``{time}`` : will be replaced with current time in HH:MM:SS format
  * ``{day}`` : will be replaced with the name of the current weekday (e.g. "Monday")
  * ``{month}`` : will be replaced with the name of the current month (e.g. "January")
  * ``{year}`` : will be replaced with the current year (e.g. "2022")


* ``streamers_to_monitor``: Enter the list of streamer names to monitor here.

* ``stream_start_messages``: Multiple messages can be defined here to be used as announcements
  for streamers going live. Messages may contain the following format tokens:

  * ``{streamer_name}`` : will be replaced with the name of the streamer
  * ``{stream_url}`` : will be replaced with the stream URL on twitch.com
  * ``{date}`` : will be replaced with current date in DD/MM/YYY format
  * ``{times}`` : will be replaced with current time in HH:MM:SS format
  * ``{time}`` : will be replaced with current time in HH:MM format
  * ``{day}`` : will be replaced with the name of the current weekday (e.g. "Monday")
  * ``{month}`` : will be replaced with the name of the current month (e.g. "January")
  * ``{year}`` : will be replaced with the current year (e.g. "2022")

Bot command reference
=====================

Command ``help``
----------------

::

   
   help [command]
   
   Shows helpful information about the given command. Replace [command] with the
   command you want help with.
   
   All discord users may use this command.

Command ``quote``
-----------------

::

   
   quote
   
   Displays a random famous quote
   
   All discord users may use this command.

Command ``mock``
----------------

::

   
   mock [mention]
   
   Repeat everything said by a specific user in a "mocking" tone. Replace [mention]
   with a mention of the discord user you want to mock.
   
   All discord users may use this command.

Command ``unmock``
------------------

::

   
   unmock [mention]
   
   Stop mocking the mentioned user. Replace [mention] with a mention of the discord user
   you want to stop mocking.
   
   All discord users may use this command.

Command ``apologise``
---------------------

::

   
   apologise [mention]
   
   Apologize to a specific user for having mocked them. Replace [mention]
   with a mention of the discord user you want to apologize to.
   
   All discord users may use this command.

Command ``apologize``
---------------------

::

   
   apologize [mention]
   
   Apologize to a specific user for having mocked them. Replace [mention]
   with a mention of the discord user you want to apologize to.
   
   All discord users may use this command.

Command ``listmocks``
---------------------

::

   
   listmocks
   
   List the name & discord IDs of all users currently being mocked
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``mockson``
-------------------

::

   
   mockson
   
   Disable all mocking until 'mocksoff' command is sent
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``mocksoff``
--------------------

::

   
   mocksoff
   
   Re-enable mocking after disabling
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``clearmocks``
----------------------

::

   
   clearmocks
   
   Clear all users that are currently being mocked
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``streamers``
---------------------

::

   
   streamers
   
   Shows a list of streamers currently being monitored.
   
   Example:
   
   @BotName !streamers
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``addstreamers``
------------------------

::

   
   addstreamers [name] ...
   
   Adds one or more new streamers to list of streamers being monitored. Replace
   [name] with the twitch name(s) of the streamer(s) you want to monitor.
   
   Example:
   
   @BotName !addstreamers streamer1 streamer2 streamer3
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``removestreamers``
---------------------------

::

   
   removestreamers [name] ...
   
   Romoves one or more streamers from the  list of streamers being monitored. Replace [name]
   with the twitch name(s) of the streamer(s) you want to remove.
   
   Example:
   
   @BotName !removestreamers streamer1 streamer2 streamer3
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``clearallstreamers``
-----------------------------

::

   
   clearallstreamers
   
   Clears the list of streamers currently being monitored.
   
   Example:
   
   @BotName !clearallstreamers
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``phrases``
-------------------

::

   
   phrases
   
   Shows a numbered list of phrases currently in use for stream announcements.
   
   @BotName !phrases
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``addphrase``
---------------------

::

   
   addphrase [phrase]
   
   Adds a new phrase to be used for stream annnouncements. The following format
   tokens may be used within a phrase:
   
       {streamer_name} : replaced with the streamer's twitch name
       {stream_url}    : replaced with the stream URL on twitch.tv
       {date}          : replaced with current date in DD/MM/YYY format
       {time}          : replaced with current time in HH:MM:SS format
       {day}           : replaced with the name of the current weekday (e.g. "Monday")
       {month}         : replaced with the name of the current month (e.g. "January")
       {year}          : replaced with the current year (e.g. "2022")
   
   Example:
   
   @BotName !addphrase "{streamer_name} is now streaming at {stream_url}!"
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``removephrase``
------------------------

::

   
   removephrase [number]
   
   Removes a phrase from the list of phrases being used for stream announcements.
   [number] must be replaced with the number for the desired phrase, as shown in the
   numbered list produced by the 'addphrase' command.
   
   Example:
   
   @BotName !removephrase 4
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``nocompetition``
-------------------------

::

   
   nocompetition [enabled]
   
   [enabled] must be replaced with either 'true' or 'false'. If true, then no
   announcements about other streams will be made while the host streamer is streaming.
   If false, then announcements will always be made, even if the host streamer is streaming.
   
   (To check if nocompetition is enabled, run the command with no true/false argument)
   
   Example:
   
   @BotName !nocompetition
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

Command ``say``
---------------

::

   
   say [stuff to say]
   
   Causes the bot to send a message in the announcements channel, immediately, containing
   whatever you type in place of [stuff to say].
   
   Example:
   
   @BotName !say Good morning
   
   Only discord users registered in 'admin_users' in the bot config. file may use this command.

