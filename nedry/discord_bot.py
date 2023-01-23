# Implements a DiscordBot class that provides a interface for interacting
# with discord's bot API
import queue
import os
import discord
import asyncio
import logging
import random
import threading

from nedry.command_processor import CommandProcessor, nedry_command_list, COMMAND_PREFIX
from nedry.event_types import EventType
from nedry import events, utils


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

main_event_loop = asyncio.get_event_loop()


class MessageResponse(object):
    """
    Represents a message being sent by the bot back to discord, in response to a
    command
    """
    def __init__(self, response_data, channel=None, member=None):
        self.channel = channel
        self.member = member
        self.response_data = response_data

class DiscordBot(object):
    """
    Wraps some interactions with the discord bot API, handles running the
    CommandProcessor when commands are received from discord messages
    """
    def __init__(self, config, twitch_monitor):
        self.message_limit = 1600
        self.token = config.config.discord_bot_api_token
        self.guild_id = config.config.discord_server_id
        self.channel_name = config.config.discord_channel_name
        self.config = config

        #intents = discord.Intents.default()
        #intents.members = True
        #intents.messages = True
        #intents.message_content = True
        #intents.guilds = True
        #intents.guild_messages = True
        #self.client = discord.Client(intents=intents)
        self.client = discord.Client(intents=discord.Intents().all())
        self.guild = None
        self.cmdprocessor = CommandProcessor(config, self, twitch_monitor, nedry_command_list)
        self.guild_available = threading.Event()
        self.channel = None
        self.plugin_manager = None

        events.subscribe(EventType.TWITCH_STREAM_STARTED, self._on_twitch_stream_started)
        events.subscribe(EventType.HOST_STREAM_STARTED, self._on_host_stream_started)
        events.subscribe(EventType.HOST_STREAM_ENDED, self._on_host_stream_ended)

        self._host_streaming = False

        @self.client.event
        async def on_guild_unavailable(guild):
            logger.info("disconnected from guild \"%s\"", guild.name)
            self.guild = None

        @self.client.event
        async def on_guild_available(guild):
            logger.info("connected to guild \"%s\"", guild.name)

            if self.guild_id == guild.id:
                self.guild = guild

                self.channel = self.get_channel_by_name(self.channel_name)

            if self.channel is None:
                logger.error("Unable to find discord channel '%s'" % self.channel_name)

            self.guild_available.set()

        @self.client.event
        async def on_connect():
            self.on_connect()

        @self.client.event
        async def on_disconnect():
            self.on_disconnect()

        @self.client.event
        async def on_member_join(member):
            self.on_member_join(member)

        @self.client.event
        async def on_message(message):
            resp = None

            if (self.mention() in message.content) or (self.nickmention() in message.content):
                resp = self.on_mention(message)
            else:
                resp = self.on_message(message)

            if resp is None:
                return

            if resp.member is not None:
                # Response should be sent in a DM to given member
                self._dm_response(message, resp)
            elif resp.channel is not None:
                # Response should be sent on the given channel
                self._channel_response(resp.channel, resp)
            else:
                raise RuntimeError("malformed response: either member or "
                                   "channel must be set")

    def get_channel_by_name(self, name):
        if self.guild is None:
            return None

        for c in self.guild.text_channels:
            if c.name == name:
                return c

        return None

    def _dm_response(self, message, resp):
        self.send_dm(message.author, resp.response_data)

    def _channel_response(self, channel, resp):
        self.send_message(channel, resp.response_data)

    def _split_message_on_limit(self, message):
        msgs = []
        code_marker_count = 0
        current_message = ""
        inside_code_marker = False

        for line in message.split("\n"):
            if current_message == "":
                if inside_code_marker:
                    current_message += "```"
                    inside_code_marker = False

            if len(current_message) + len(line) > self.message_limit:
                # This line would exceed message limit, time for a new message
                inside_code_marker = (code_marker_count % 6) != 0
                code_marker_count = 0

                if inside_code_marker:
                    current_message += '\n```'

                msgs.append(current_message)
                current_message = ""
                continue

            code_marker_count += line.count('```')

            if current_message == "```":
                line = line.lstrip()

            current_message += line + "\n"

        if current_message:
            msgs.append(current_message)

        return msgs

    def change_channel(self, new_channel_name):
        name = new_channel_name.strip()
        chan = self.get_channel_by_name(name)
        if chan is None:
            return False

        self.channel_name = name
        self.channel = chan
        return True

    def _on_twitch_stream_started(self, name, url):
        if self.config.config.silent_when_host_streaming:
            if self._host_streaming:
                # Don't send stream announcements if host is streaming
                return

        fmt_args = utils.streamer_fmt_tokens(name, url)
        fmt_args.update(utils.bot_fmt_tokens(self))
        fmt_args.update(utils.datetime_fmt_tokens())
        fmtstring = random.choice(self.config.config.stream_start_messages)
        self.send_stream_announcement(fmtstring.format(**fmt_args))

    def _on_host_stream_started(self):
        self._host_streaming = True

    def _on_host_stream_ended(self):
        self._host_streaming = False

    def add_command(self, cmd_word, cmd_handler, admin_only, helptext):
        self.cmdprocessor.add_command(cmd_word, cmd_handler, admin_only, helptext)

    def remove_command(self, cmd_word):
        self.cmdprocessor.remove_command(cmd_word)

    def mention(self):
        """
        Returns the text for a mention of the bot
        """
        return "<@%d>" % self.client.user.id

    def nickmention(self):
        return"<@!%d>" % self.client.user.id

    def run(self):
        self.client.run(self.token)

    def stop(self):
        logger.debug("Stopping")
        asyncio.run(self.client.close())
        self.cmdprocessor.close()

    def send_message(self, channel, message):
        messages = self._split_message_on_limit(message)
        for message in messages:
            asyncio.run_coroutine_threadsafe(channel.send(message), main_event_loop)

    def send_stream_announcement(self, message):
        asyncio.run_coroutine_threadsafe(self.channel.send(message), main_event_loop)

    async def _send_dm_async(self, member, message):
        channel = await member.create_dm()
        await channel.send(message)

    def send_dm(self, member, message):
        messages = self._split_message_on_limit(message)
        for message in messages:
            asyncio.run_coroutine_threadsafe(self._send_dm_async(member, message), main_event_loop)

    def message_history(self, channel, limit=20):
        async def _get_messages(chan, lim):
            return await chan.history(limit=lim).flatten()

        fut = asyncio.run_coroutine_threadsafe(_get_messages(channel, limit), main_event_loop)
        async def _await_fut():
            await fut

        asyncio.run_coroutine_threadsafe(_await_fut(), main_event_loop)
        return fut.result(1)

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_member_join(self, member):
        events.emit(EventType.NEW_DISCORD_MEMBER, member)

    def on_message(self, message):
        events.emit(EventType.DISCORD_MESSAGE_RECEIVED, message)

        resp = self.cmdprocessor.process_message(message)

        if resp is not None:
            return MessageResponse(resp, channel=message.channel)

        return None

    def on_mention(self, message):
        if message.author.id == self.client.user.id:
            # Ignore mentions of ourself from ourself
            return None

        msg = message.content.replace(self.mention(), '', 1).strip()

        if not msg.strip().startswith(COMMAND_PREFIX):
            # Only emit mention event if message is not a command
            events.emit(EventType.DISCORD_BOT_MENTION, message, msg)

        resp = self.cmdprocessor.process_command(message.channel, message.author, msg)

        if resp is not None:
             return MessageResponse(resp, channel=message.channel)

        return None
