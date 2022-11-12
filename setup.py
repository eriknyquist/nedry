import unittest
import os
from setuptools import setup

from twitch_monitor_discord_bot import __version__

HERE = os.path.abspath(os.path.dirname(__file__))
README = os.path.join(HERE, "README.rst")
REQS = os.path.join(HERE, "requirements.txt")

with open(README, 'r') as f:
    long_description = f.read()

with open(REQS, 'r') as fh:
    requirements = [r.strip() for r in fh.readlines()]

setup(
    name='twitch_monitor_discord_bot',
    version=__version__,
    description=('A discord bot for monitoring twitch streams'),
    long_description=long_description,
    url='http://github.com/eriknyquist/twitch_monitor_discord_bot',
    author='Erik Nyquist',
    author_email='eknyquist@gmail.com',
    license='Apache 2.0',
    packages=['twitch_monitor_discord_bot'],
    package_dir={'twitch_monitor_discord_bot': 'twitch_monitor_discord_bot'},
    package_data={'twitch_monitor_discord_bot': [os.path.join('twitch_monitor_discord_bot', 'quotedb.json')]},
    include_package_data=True,
    zip_safe=False,
    install_requires=requirements
)
