# bridgeakhper
Telegram-based solution for bridge scoring.
Inspired by @elizaveta2810 and tested in Yerevan bridge club.

# Getting started
Create a new telegram bot for your club using @BotFather and edit config.json.
Optionally: bot is configured to be launched on Heroku.

## Config
Config values are stored in two locations:
1. config.json file
2. Heroku env variables (currently BOT_TOKEN, DIRECTORS & PORT are supported)

tournament_title: Enter any string, e.g. Griffins Beltane MP

directors: list of directors. They will be able to start session and generate the results.

token: Enter token of your bot. You can find in chat history for @BotFather.

movement: "mitchell"  (not implemented) or "howell"

full (not implemented): whether to have maximum number of rounds available. 
If set to false, bot would ask for the number of rounds (to be implemented).

score: mp or imp (not implemented)

neuberg: MP only. If true, uses [Neuberg formula](https://en.wikipedia.org/wiki/Neuberg_formula) for more fair result in case of adjusted score. Default: true. 

validate_lead (not implemented): Whether to check the submitted first lead card against the deal data in the DB. Use responsively. 
Could be unsafe if turned on, e.g. anyone can find out if a certain card is present in the opp's hand. Default: false

## Players database (optional)
Use this step to unify the way player names appear in the results.
Launch players.py file. It will create players.db file. 
Open it with any db editor, e.g. "DB Browser for SQLite" for Win or DBeaver for Linux/Mac.
Add the data for permanent players of your club. 

Why do you need it? It helps to correct typos and implements "ladies first" convention.
## Starting the bot
Launch tg_input.py. This will start your bot, but not your session. 
Make sure your computer has a stable internet connection. You can use your home computer,
all the steps below (except for the weighted scores) can be done from mobile.  
Optionally: use Heroku free account to host the bot if the above option doesn't suit you.

## Starting the session
1. Visit your bot in telegram from a TD's account. 
    Issue /session command (not available through main menu, just type it in).
    Then submit the number of boards and pairs (and the number of rounds for non-full tournaments).
2. Ask each partnership to submit their names by issuing /names command or enter them by yourself when registration 
   is closed.
    Names can be separated by any character or no character at all. 
    Only the first or last name may be submitted (works randomly if it is not unique). 
    Script looks for submitted names in the players.db.
    
3.  New result is submitted by /board command. If no hand data is available, bot will ask to enter the hand first,
    and then the result.
4. When all results are submitted, TD issues /end command, which generates 3 PDF files with Standings, 
   Personal results and Travellers (may take a while), and sends them to TD's chat (DM),
   so they can perform sanity check before publishing them.
   Also, you can use /boards command to get just the list of boards with double-dummy analysis.
   
# Limitations
1. Tested on Win10 & Linux.
2. Cannot handle multi-session tournaments
3. Cannot handle weighted scores. For now only 50/50 and 60/40 can be adjusted. 


# Notes for developers
Please make sure not to push telegram bot token into the repo. It makes your bot vulnerable.
