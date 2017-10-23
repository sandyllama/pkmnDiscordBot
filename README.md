# pkmnDiscordBot

Discord Bot used to automate and manage competitive Pokémon Draft Leagues.

Tested on Python 3.5+

--------------------------------------------------------------------------------------------------

Features:
- Can be used to manage an arbitrary number of players within an 11 slot roster GBA-style snake draft.
- Allows for queuing of drafts ahead of time.
  - Keep your draft running quickly by queuing multiple picks in a row.
  - In the event that another player drafts one of your queued choices, you will be alerted.
- The bot provides searching features to help you with your picks - search by type or tier.
  - Additionally, you may check which types are in high demand.
  - A recommendation heuristic is also provided to advise your picks.

--------------------------------------------------------------------------------------------------

To-Do:
- Add support for Mega Evolutions.
- Add support for Tiered and Point drafts.

--------------------------------------------------------------------------------------------------

Setup

To set up the bot, you need to register a new bot on the Discord app page, get a token, etc. There are plenty of guides for this available. The token will be used to connect the bot to your server. You must edit pkmnDraftBot.py with your token -- the location is marked clearly within the source.

The app and supporting data file (pkmnDraftBot.py, pkmnList.txt) must be placed in a directory together. The Python app needs to run indefinitely, as long as the draft is running. I would recommend using `screen` or `nohup` to accomplish this.

In the event that the bot crashes due to Discord outages/hiccups, simply restart the app; your draft will be able to resume from its previous position. These issues are thankfully infrequent enough that this shouldn't be an issue.

All participating players will need to register with the `!register` command before the draft begins. Use the `!help` command for more info.
