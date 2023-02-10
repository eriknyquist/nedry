import unittest
import os
from setuptools import setup, find_packages

from nedry import __version__

HERE = os.path.abspath(os.path.dirname(__file__))
README = os.path.join(HERE, "README.rst")
REQS = os.path.join(HERE, "requirements.txt")

with open(README, 'r') as f:
    long_description = f.read()

with open(REQS, 'r') as fh:
    requirements = [r.strip() for r in fh.readlines()]

setup(
    name='nedry',
    version=__version__,
    description=('A fun & useful discord bot with a modular plugin system'),
    long_description=long_description,
    url='http://github.com/eriknyquist/nedry',
    author='Erik Nyquist',
    author_email='eknyquist@gmail.com',
    license='Apache 2.0',
    python_requires='>=3.9',
    packages=find_packages(),
    package_dir={'nedry': 'nedry'},
    package_data={'nedry':  ['quotedb.json',
                            os.path.join('builtin_plugins', 'writing_prompts.txt')]},
    include_package_data=True,
    zip_safe=False,
    install_requires=requirements
)
