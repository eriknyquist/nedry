import os
import discord
import threading


class MessageResponse(object):
    def __init__(self, response_data, channel=None, member=None):
        self.channel = channel
        self.member = member
        self.response_data = response_data

class DiscordBot(object):
    def __init__(self, token, guild_id, channel_name):
        self.token = token
        self.guild_id = guild_id
        self.channel_name = channel_name
        self.client = discord.Client()

        self.thread = threading.Thread(target=self.thread_task)
        self.thread.start()

        self.channel = None

        @self.client.event
        async def on_guild_available(guild):
            if self.guild_id == guild.id:
                for c in guild.text_channels:
                    if c.name == self.channel_name:
                        self.channel = c
                        break

            if self.channel is None:
                raise RuntimeError("Unable to find channel '%s'" % CHANNEL_NAME)

        @self.client.event
        async def on_connect():
            self.on_connect()

        @self.client.event
        async def on_member_join(member):
            self.on_member_join(member)

        @self.client.event
        async def on_message(message):
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

    def run(self):
        self.client.run(self.token)

    def thread_task(self):
        pass

    async def send_message(self, message):
        await self.channel.send(message)

    def on_connect(self):
        pass

    def on_member_join(self, member):
        pass

    def on_message(self, message):
        pass

def main():
    bot = build_sketi_bot()
    bot.run()

if __name__ == "__main__":
    main()
