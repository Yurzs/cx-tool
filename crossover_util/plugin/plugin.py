import importlib
import inspect
import platform
import sys
import typing
from enum import Enum
from functools import cached_property, partial
from typing import List, Type


if typing.TYPE_CHECKING:
    from crossover_util.config import UtilConfig
    from crossover_util.plugin.context import PluginContext
    from click import Group


class Platform(str, Enum):
    linux = "linux"
    macos = "darwin"


class Architecture(str, Enum):
    x86_64 = "x86_64"
    arm64 = "arm64"


class Plugin:
    name: str
    platforms: List[Platform] = [Platform.macos, Platform.linux]
    arch: List[Architecture] = [Architecture.x86_64, Architecture.arm64]

    __REGISTRY__ = {}

    def __init__(self, config: "UtilConfig"):
        self.config = config

    @property
    def data(self):
        return self.config.get_plugin_data(self)

    @cached_property
    def cli(self) -> "Group":
        from click import Group

        group = Group(self.name, help=self.__doc__)

        self.config.plugin_cli.add_command(group)

        return group

    def cli_command(self, name: str):
        def wrapper(f: clickable):
            return self.cli.command(
                name,
                context_settings=dict(
                    allow_extra_args=True,
                ),
                no_args_is_help=bool(set(inspect.signature(f.f).parameters) - {"self"}),
            )(f.with_plugin(self))

        return wrapper

    def on_load(self): ...

    def on_unload(self): ...

    def on_start(self, ctx: "PluginContext"): ...

    def on_stop(self, ctx: "PluginContext"): ...

    @classmethod
    def find_plugins_in_module(cls, module_name: str) -> List[Type["Plugin"]]:
        """Find Plugins in module."""

        plugins = []

        if module_name not in cls.__REGISTRY__:
            for item in importlib.import_module(module_name).__dict__:
                if isinstance(item, type) and issubclass(cls, Plugin):
                    plugins.append(item)

        return plugins

    @classmethod
    def get_plugin(cls, name: str):
        """Get plugin by name."""

        return cls.__REGISTRY__.get(name)

    @classmethod
    def add_plugin(cls, plugin: "Plugin"):
        import click

        if sys.platform not in plugin.platforms:
            return

        if platform.machine() not in plugin.arch:
            return

        if plugin.name in cls.__REGISTRY__:
            click.echo(
                f"Plugin with name `{plugin.name}` already exists in other package."
            )
        else:
            cls.__REGISTRY__[plugin.name] = plugin

    @classmethod
    def all_plugins(cls) -> List["Plugin"]:
        return list(cls.__REGISTRY__.values())

    @classmethod
    def import_plugins(cls, plugin_module: str, config: "UtilConfig"):
        """Import and init plugins."""

        for plugin in cls.find_plugins_in_module(plugin_module):
            if sys.platform not in plugin.platforms:
                continue

            cls.add_plugin(plugin(config))


class clickable:  # noqa
    def __init__(self, f):
        self.f = f
        self.orig_func = f

    def with_plugin(self, plugin: "Plugin") -> "clickable":
        self.f = partial(self.f, plugin)
        return self

    def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs)

    @property
    def __doc__(self):
        return self.orig_func.__doc__


class CrossOverControlPlugin:
    def kill_crossover(self):
        raise NotImplementedError()

    def install(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()

    def run_crossover(self):
        raise NotImplementedError()
