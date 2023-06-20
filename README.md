# bridgeakhper
Telegram-based solution for bridge scoring.
Inspired by @elizaveta2810 and tested in Yerevan bridge club.

# Getting started 
## Cloud setup
Below are the steps for a typical cloud setup. Feel free to adjust it to meet your needs.
Cloud setup works faster than local and doesn't depend on 
* Create a new telegram bot for your club using @BotFather and edit config.json.
* Create a player database. We use ElephantSQL free tier, but local DB is also supported.
* Create a fly.io account and install flyctl.
* Install docker.
* Follow [this](https://bakanim.xyz/posts/deploy-telegram-bot-to-fly-io/) guide for the flyctl setup.
## Local setup
### Players database (optional)
Use this step to unify the way player names appear in the results.
Launch players.py file. It will create players.db file. 
Open it with any db editor, e.g. "DB Browser for SQLite" for Win or DBeaver for Linux/Mac.
Add the data for permanent players of your club. 

Why do you need it? It helps to correct typos and implements "ladies first" convention.
### Starting the bot
Launch tg_input.py. This will start your bot, but not your session. 
Make sure your computer has a stable internet connection. You can use your home computer,
all the steps below (except for the weighted scores) can be done from mobile.  

## Config
Config values are stored in two locations:
1. config.json file
2. Fly.IO secrets (currently BOT_TOKEN, WEBHOOK_URL, PLAYERS_DB & DIRECTOR are used).

tournament_title: Enter any string, e.g. Griffins Beltane MP

directors: list of directors. They will be able to start session and generate the results.

token: Enter token of your bot. You can find in chat history for @BotFather.

is_mitchell: mitchell or howell

scoring: MPs or IMPs or Cross-IMPs. Changed on the fly, config value is used for debugging purposes.

neuberg: MP only. If true, uses [Neuberg formula](https://en.wikipedia.org/wiki/Neuberg_formula) for more fair result in case of adjusted score. Default: true. 

validate_lead (not implemented): Whether to check the submitted first lead card against the deal data in the DB. Use responsively. 
Could be unsafe if turned on, e.g. anyone can find out if a certain card is present in the opp's hand. Default: false


## Starting the session
1. Visit your bot in Telegram from a TD's account. 
    Issue /session command (not available through main menu, just type it in). This will create tournament DB 
   locally/on the server depending on your setup.
    Then submit scoring, number of boards and pairs (and the number of rounds for non-full tournaments).
2. Ask each partnership to submit their names by issuing /names command or enter them by yourself when registration 
   is closed.
    Names can be separated by any character or no character at all. 
    Only the first or last name may be submitted (works randomly if it is not unique). 
    Script looks for submitted names in the players DB.
    
3.  New result is submitted by /board command. If no hand data is available, bot will ask to enter the hand first,
    and then the result.
4. When all results are submitted, TD issues /end command, which generates 3 PDF files with Standings, 
   Personal results and Travellers (may take a while), and sends them to TD's chat (DM),
   so they can perform sanity check before publishing them.
   Also, you can use /boards command to get just the list of boards with double-dummy analysis.
   
    Notice the highlighted scores in Scorecards.pdf output file. They indicate suspicious results.
   It could be wrong declarer or contract or just inaccurate defense.
   
## Commands
* /session starts a new session (without cleanup) if TD, otherwise shows missing boards, names, and results
* /board starts adding result flow. Will ask for hands not submitted yet.
* /names adds players names to tourney DB
* /result overrides the necessity to submit hand before score

### TD only
* /end generates reports, cleans DB
* /viewboard outputs all hands for a submitted board. Can be used to help players remember which cards they had held.
* /missing shows missing boards, names, and results
* /addplayer adds player to players DB
* /updateplayer updates player record
* /tdlist lists all TDs
* /loaddb (debugging only) loads tournament DB from testboards.db file.
* /boards gets report with boards without scores


## Movements
Optionally provide a movement file in the /movements folder to describe movement. This saves 1 tap for protocol, 
but prevents mistakes when submitting the pair numbers. Use any editor that supports encoding/decoding to see what's 
inside existing .mov files.

# Limitations
1. Tested on Win10 & Linux.
2. Cannot handle multi-session tournaments
3. Cannot handle weighted scores. For now only 50/50 and 60/40 can be adjusted. 


# Notes for developers
Please make sure not to push telegram bot token into the repo. It makes your bot vulnerable.
