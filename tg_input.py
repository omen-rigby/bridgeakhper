import time
from telegram import Update
from telegram.ext import *
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
from constants import CARDS
import sqlite3
import logging

TOKEN = "Hidden"
URL = f"https://api.telegram.org/bot{TOKEN}"
db_path = "{}/boards.db".format(time.strftime("%Y-%m-%d"))
print(db_path)
hands = "NESW"
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.DEBUG)


class Board:
    def __init__(self):
        self.number = 0
        self.n = self.w = self.s = self.e = ""

    def set_number(self, number):
        self.number = number

    @property
    def current_hand(self):
        for h in "nesw":
            if self.__getattribute__(h):
                continue
            return h

    def set_hand(self, cards):
        seat = self.current_hand
        logging.debug(seat)
        self.__setattr__(seat.lower(), cards)
        cards = cards.lower().replace("10", "t").split(" ")
        for suit, holding in zip("shdc", cards):
            self.__setattr__(seat.lower() + suit, holding.replace("-", ""))

    def get_w_hand(self):
        w = []
        for suit in "shdc":
            cards = "".join(CARDS)
            for seat in "nes":
                for c in self.__getattribute__(f"{seat}{suit}"):
                    cards = cards.replace(c, "")
                    self.__setattr__(f"w{suit}", cards)
            w.append(cards or "-")
        return " ".join(w)

    def save(self):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        statement = f"""
        INSERT INTO boards (number, ns, nh, nd, nc, es, eh, ed, ec, ss, sh, sd, sc, ws, wh, wd, wc)
        VALUES({self.number}, '{self.ns}', '{self.nh}', '{self.nd}', '{self.nc}', '{self.es}', '{self.eh}', '{self.ed}', '{self.ec}', '{self.ss}', '{self.sh}', '{self.sd}', '{self.sc}', '{self.ws}', '{self.wh}', '{self.wd}', '{self.wc}');"""
        print(statement)
        cursor.execute(statement)
        conn.commit()
        conn.close()


def send(chat_id, text, reply_buttons=None, context=None):
    reply_buttons = list(reply_buttons) if reply_buttons else []
    if len(reply_buttons) > 10:
        reply_buttons = [reply_buttons[:9], reply_buttons[9:18], reply_buttons[18:]]
    else:
        reply_buttons = [reply_buttons] if reply_buttons else []

    # elif len(reply_buttons) < 5:
    #     pass
    markup = ReplyKeyboardMarkup(reply_buttons)
    context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)


def start(update: Update, context: CallbackContext):
    send(chat_id=update.effective_chat.id,
         text="Started bridgemate. What do you want to do?",
         reply_buttons=("/board",),
         context=context)


def board(update: Update, context: CallbackContext):
    all_boards = list(range(1,28))
    context.user_data["board"] = Board()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("Select number from boards")
    added = list(set([c[0] for c in cursor.fetchall()]))
    buttons = [l for l in all_boards if l not in added]
    send(chat_id=update.effective_chat.id,
         text="Enter board number",
         reply_buttons=buttons,
         context=context)


def start_session(update: Update, context: CallbackContext):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    statement = """CREATE TABLE "boards" (
	"number"	INTEGER,
	"ns"	TEXT,
	"nh"	TEXT,
	"nd"	TEXT,
	"nc"	TEXT,
	"es"	TEXT,
	"eh"	TEXT,
	"ed"	TEXT,
	"ec"	TEXT,
	"ss"	TEXT,
	"sh"	TEXT,
	"sd"	TEXT,
	"sc"	TEXT,
	"ws"	TEXT,
	"wh"	TEXT,
	"wd"	TEXT,
	"wc"	TEXT
)"""
    cursor.execute(statement)
    conn.commit()
    conn.close()
    send(chat_id=update.effective_chat.id,
         text="Started session. What do you want to do?",
         reply_buttons=("/board",),
         context=context)


def board_number(update: Update, context: CallbackContext):
    context.user_data["board"].number = update.message.text
    send(chat_id=update.effective_chat.id,
         text="Enter N hand e.g. KQJ107632 - A54 T64 (10 and T are interchangeable)",
         context=context)


def hand(update: Update, context: CallbackContext):
    board = context.user_data["board"]

    board.set_hand(update.message.text)
    if board.current_hand == "w":
        w = board.get_w_hand()
        if len(w.replace("-", "").replace(" ", "")) != 13:
            send(chat_id=update.effective_chat.id,
                 text=f"Wrong number of cards if left for west: {w}",
                 reply_buttons=("OK", "Cancel"),
                 context=context)
            return cancel(update, context)
        else:
            send(chat_id=update.effective_chat.id,
                 text=f"W hand should be: {w}",
                 reply_buttons=("OK", "Cancel"),
                 context=context)
    else:
        send(chat_id=update.effective_chat.id,
             text=f"Enter {board.current_hand.upper()} hand",
             context=context)


def save(update: Update, context: CallbackContext):
    board = context.user_data["board"]
    board.save()
    send(chat_id=update.effective_chat.id,
         text=f"Board {board.number} is saved",
         reply_buttons=("/board",),
         context=context)


def cancel(update: Update, context: CallbackContext):
    number = context.user_data["board"].number
    context.user_data["board"] = Board()
    context.user_data["board"].number = number

    send(chat_id=update.effective_chat.id,
         text="Enter N hand again",
         context=context)


if __name__ == '__main__':
    updater = Updater(token=TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('session', start_session))
    updater.dispatcher.add_handler(CommandHandler('board', board))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex("^\d+$"), board_number))
    hand_re = " ".join(["[0-9akqjtAKQJT-]+"] * 4)
    updater.dispatcher.add_handler(MessageHandler(Filters.regex(f"^{hand_re}$"), hand))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("OK"), save))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Cancel"), cancel))

    updater.start_polling()
