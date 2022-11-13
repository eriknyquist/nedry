#. Bump the version number in twitch_monitor_discord_bot/__init__.py
#. Bump the version number in the top title in README.rst
#. Delete the final "Bot command reference" section in README.rst
#. Re-generate the "Bot command reference" section (python generate_command_docs.py >> README.rst)
#. Generate PDF version of README (rst2pdf README.rst twitch_monitor_discord_bot_x.x.x_documentation.pdf)
#. Make a new commit, adding all changed files
#. Tag the new commit with the next version and push (git tag vx.x.x && git push origin master --tags)
#. Build the wheel file (python setup.py bdist_wheel)
#. Make a new release on github, against tag vx.x.x, release name should match the tag name. Make sure to add the PDF API docs file and the wheel file.
#. Push wheel file to pypi (python -m twine upload dist/twitch_monitor_discord_bot-x.x.x-py3-none-any.whl)
