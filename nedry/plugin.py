import inspect
import os
import importlib
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PluginModule(object):
    """
    Abstract implementation of a PluginModule class that represents a
    modular / pluggable behaviour of the bot
    """
    plugin_name = ""
    plugin_short_description = "Short description of the plugin, no line breaks"
    plugin_long_description = "Longer description, as many line breaks as you like"

    def __init__(self, discord_bot):
        """
        :param bot: discord bot object, which allows you to send messages to discord channels,\
            among other things
        """
        self.discord_bot = discord_bot

    def open(self):
        """
        Enables plugin operation; subscribe to events and/or initialize things here
        """
        raise NotImplementedError()

    def close(self):
        """
        Disables plugin operation; unsubscribe from events and/or tear down things here
        """
        raise NotImplementedError()


class PluginModuleManager(object):
    """
    Helper class for loading/managing/running plugin modules
    """
    def __init__(self, discord_bot, plugin_dirs):
        self._plugin_dirs = plugin_dirs
        self._plugin_modules = {}
        self._discord_bot = discord_bot

    def check_and_load_object(self, obj, filepath):
        if inspect.isclass(obj) and issubclass(obj, PluginModule) and (obj != PluginModule):
            if obj.plugin_name in self._plugin_modules:
                raise NameError("Plugin name %s already exists" % obj.plugin_name)

            self._plugin_modules[obj.plugin_name] = obj(self._discord_bot)
            logger.info("Loaded %s plugin from %s" % (obj.__name__, filepath))

    def load_plugins_from_file(self, filepath):
        spec = importlib.util.spec_from_file_location("Plugin%d" % len(self._plugin_modules),
                                                      filepath)

        try:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except:
            return

        attr_names = dir(mod)
        for n in attr_names:
            self.check_and_load_object(getattr(mod, n), filepath)

    def load_plugins_from_directory(self, directory):
        for filename in os.listdir(directory):
            self.load_plugins_from_file(os.path.join(directory, filename))

    def load_plugins_from_directories(self):
        for d in self._plugin_dirs:
            if os.path.isdir(d):
                self.load_plugins_from_directory(d)

    def _plugins_by_name(self, plugin_names):
        if plugin_names is None:
            return self._plugin_modules.values()

        return [self._plugin_modules[n] for n in plugin_names if n in self._plugin_modules]

    def open_plugins(self, plugin_names=None):
        """
        Call open method on multiple specific plugins by name

        :param plugin_names: names of plugins to open. If unset, all plugins will be opened.
        """
        for plugin in self._plugins_by_name(plugin_names):
            plugin.open()

    def close_plugins(self, plugin_names=None):
        """
        Call close method on multiple specific plugins by name

        :param plugin_names: names of plugins to close. If unset, all plugins will be opened.
        """
        for plugin in self._plugins_by_name(plugin_names):
            plugin.close()
