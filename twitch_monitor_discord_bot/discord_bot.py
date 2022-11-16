# Implements a DiscordBot class that provides a interface for interacting
# with discord's bot API

import os
import discord
import asyncio
import logging
import threading

from twitch_monitor_discord_bot.command_processor import CommandProcessor, twitch_monitor_bot_command_list

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

        self.cmdprocessor = CommandProcessor(config, self, twitch_monitor, twitch_monitor_bot_command_list)
        self.guild_available = threading.Event()
        self.channel = None

        @self.client.event
        async def on_guild_available(guild):
            logger.info("connected to guild \"%s\"", guild.name)

            if self.guild_id == guild.id:
                for c in guild.text_channels:
                    if c.name == self.channel_name:
                        self.channel = c
                        break

            if self.channel is None:
                raise RuntimeError("Unable to find channel '%s'" % self.channel_name)

            self.guild_available.set()

        @self.client.event
        async def on_connect():
            self.on_connect()

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
                await message.author.create_dm()
                await message.author.dm_channel.send(resp.response_data)
            elif resp.channel is not None:
                # Response should be sent on the given channel
                await resp.channel.send(resp.response_data)
            else:
                raise RuntimeError("malformed response: either member or "
                                   "channel must be set")

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
        logger.info("Stopping")
        asyncio.run(self.client.close())
        self.cmdprocessor.close()

    def send_message(self, message):
        asyncio.run_coroutine_threadsafe(self.channel.send(message), main_event_loop)

    def on_connect(self):
        pass

    def on_member_join(self, member):
        logger.info("%s joined the server" % member.name)

    def on_message(self, message):
        resp = self.cmdprocessor.process_message(message)

        if resp is not None:
            return MessageResponse(resp, channel=message.channel)

        return None

    def on_mention(self, message):
        msg = message.content.replace(self.mention(), '').replace(self.nickmention(), '')
        resp = self.cmdprocessor.process_command(message.channel, message.author, msg)

        if resp is not None:
            return MessageResponse(resp, channel=message.channel)

        return None
