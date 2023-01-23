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
    plugin_name = "should_be_short_and_easy_to_copy_paste"
    plugin_version = "whatever"
    plugin_short_description = "Short description of the plugin, no line breaks"
    plugin_long_description = "Longer description, as many line breaks as you like"

    def __init__(self, discord_bot):
        """
        :param bot: discord bot object, which allows you to send messages to discord channels,\
            among other things
        """
        self.discord_bot = discord_bot
        self.enabled = False

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

    def add_plugin_class(self, cls):
        name = cls.plugin_name.lower()
        if name in self._plugin_modules:
            raise NameError("Plugin name %s already exists" % name)

        self._plugin_modules[name] = cls(self._discord_bot)
        logger.info("loaded built-in %s %s" % (cls.plugin_name, cls.plugin_version))

    def check_and_load_object(self, obj, filepath):
        name = obj.plugin_name.lower()
        if inspect.isclass(obj) and issubclass(obj, PluginModule) and (obj != PluginModule):
            if name in self._plugin_modules:
                raise NameError("Plugin name %s already exists" % name)

            self._plugin_modules[name] = obj(self._discord_bot)
            logger.info("%s %s loaded from %s" % (name, obj.plugin_version, filepath))

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

    def get_plugins_by_name(self, names):
        return self._plugins_by_name(names)

    def is_valid_plugin_name(self, name):
        return name.lower() in self._plugin_modules

    def enable_plugins(self, plugin_names=None):
        """
        Call open method on multiple specific plugins by name

        :param plugin_names: names of plugins to open. If unset, all plugins will be opened.
        """
        for plugin in self._plugins_by_name(plugin_names):
            if plugin.enabled:
                # Plugin is already enabled
                continue

            plugin.open()
            plugin.enabled = True

    def disable_plugins(self, plugin_names=None):
        """
        Call close method on multiple specific plugins by name

        :param plugin_names: names of plugins to close. If unset, all plugins will be closed.
        """
        for plugin in self._plugins_by_name(plugin_names):
            if not plugin.enabled:
                # Plugin is already disabled
                continue

            plugin.close()
            plugin.enabled = False

    def enabled_plugins(self):
        """
        Return a list of all plugin module instances that are currently enabled

        :return: list of enabled PluginModule instances
        """
        ret = []
        for i in self._plugin_modules:
            if self._plugin_modules[i].enabled:
                ret.append(self._plugin_modules[i])

        return ret

    def disabled_plugins(self):
        """
        Return a list of all plugin module instances that are currently disabled

        :return: list of enabled PluginModule instances
        """
        ret = []
        for i in self._plugin_modules:
            if not self._plugin_modules[i].enabled:
                ret.append(self._plugin_modules[i])

        return ret

    def stop(self):
        """
        Disable/close all plugins and stop plugin manager
        """
        logger.debug("Stopping")
        # Disable all enabled plugins
        for n in self._plugin_modules:
            plugin = self._plugin_modules[n]
            if plugin.enabled:
                plugin.close()
                plugin.enabled = False
