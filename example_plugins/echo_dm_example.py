from nedry.event_types import EventType
from nedry import events
from nedry.plugin import PluginModule


class EchoDmExample(PluginModule):
    """
    Simple plugin that subscribes to the EventType.DISCORD_BOT_MENTION event,
    and whenever a message starting with a bot mention is seen in any public channel
    on discord, sends a DM to the author of the message containing whataver text
    they typed after the mention.
    """
    plugin_name = "Example plugin"
    plugin_version = "1.0.0"
    plugin_short_description = "Simple example illustrating the plugin system"
    plugin_long_description = ""

    def _on_mention(self, message, text_without_mention):
        # Whenever anybody mentions the bot in a public channel, take the
        # text after the mention and echo it back to the same user in a DM
        self.discord_bot.send_dm(message.author, message.content)

    def open(self):
        """
        Enables plugin operation; subscribe to events and/or initialize things here
        """
        # Subscribe to the DISCORD_BOT_MENTION event, which will call our handler
        # with the text after the mention, whenever a message starting with a bot
        # mention is seen in any public discord channel
        events.subscribe(EventType.DISCORD_BOT_MENTION, self._on_mention)

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        # Unsubscribe from the DISCORD_BOT_MENTION event, so that the plugin will
        # stop doing its thing if disabled
        events.unsubscribe(EventType.DISCORD_BOT_MENTION, self._on_mention)
