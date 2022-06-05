from itertools import chain
from telegram import Update
from telegram.parsemode import ParseMode
from telegram.ext import *
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup, InlineKeyboardButton
from constants import *
from board import Board
import sqlite3
import logging

TOKEN = "token"
DIRECTORS = ['omen_rigby']
URL = f"https://api.telegram.org/bot{TOKEN}"
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.DEBUG)


NAVIGATION_KEYBOARD = InlineKeyboardMarkup(
    [[InlineKeyboardButton("back",  callback_data="bm:left"),
      InlineKeyboardButton("save",  callback_data="bm:enter")]])
CONTRACTS_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton(text=str(i), callback_data=f"bm:{i}") for i in range(1, 8)],
    [InlineKeyboardButton(s, callback_data=f"bm:{s}") for s in list(reversed(SUITS_UNICODE)) + ["NT"]],
    [InlineKeyboardButton(text=x, callback_data=f"bm:{x}") for x in ["x", "xx", "pass"]],
    [InlineKeyboardButton(s, callback_data=f"bm:{s}") for s in list("NESW")],
])


def lead_keyboard():
    rows = []

    for i, s in enumerate(SUITS_UNICODE):
        suit_cards = [InlineKeyboardButton(text, callback_data="bm:" + "shdc"[i] + text)
                      for text in SUITS_UNICODE[i] + "AKQJT98765432"]
        half = (len(suit_cards) + 1) // 2
        rows.extend([suit_cards[:half], suit_cards[half:]])

    return InlineKeyboardMarkup(rows)


def pairs_keyboard(context, exclude=0):
    pairs = context.bot_data["maxpair"]
    board = context.user_data["board"].number
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"Select ns,ew from protocols where number={board}")
    denied = list(set(chain(*[c for c in cursor.fetchall()])))
    conn.close()
    allowed = [b for b in range(1, pairs + 1) if b not in denied and b != int(exclude)]
    rows = []
    for i in range(len(allowed) // 7):
        rows.append([InlineKeyboardButton(text=str(p), callback_data=f"bm:{p}") for p in allowed[7 * i:7 + 7 * i]])
    if pairs % 7:
        rows.append([InlineKeyboardButton(text=str(p), callback_data=f"bm:{p}") for p in allowed[len(allowed) // 7 * 7:]])
    return InlineKeyboardMarkup(rows)

def results_keyboard(context):
    result = context.user_data["result"]
    level = int(result.text.split("Contract: ")[1][0])

    rows = [[InlineKeyboardButton(text="=", callback_data=f"bm:=")] + \
                [InlineKeyboardButton(text=f"+{i}", callback_data=f"bm:+{i}") for i in range(1, 8 - level)],

            [InlineKeyboardButton(text=f"-{i}", callback_data=f"bm:-{i}") for i in range(1, level + 7)]]
    return InlineKeyboardMarkup(rows)


def send(chat_id, text, reply_buttons=None, context=None):
    if isinstance(reply_buttons, InlineKeyboardMarkup):
        markup = reply_buttons
    else:
        reply_buttons = list(reply_buttons) if reply_buttons else []
        if len(reply_buttons) > 10:
            reply_buttons = [reply_buttons[:9], reply_buttons[9:18], reply_buttons[18:]]
        else:
            reply_buttons = [reply_buttons] if reply_buttons else []
        if reply_buttons:
            markup = ReplyKeyboardMarkup(reply_buttons, one_time_keyboard=True, resize_keyboard=True)
        else:
            markup = ReplyKeyboardMarkup(reply_buttons, one_time_keyboard=True, resize_keyboard=True)
        print(markup)
    return context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode=ParseMode.HTML)


def start(update: Update, context: CallbackContext):
    send(chat_id=update.effective_chat.id,
         text="Started bridgemate. What do you want to do?",
         reply_buttons=("/board",),
         context=context)


def board(update: Update, context: CallbackContext):
    all_boards = list(range(1, context.bot_data["maxboard"] + 1))
    context.user_data["board"] = Board()
    send(chat_id=update.effective_chat.id,
         text="Enter board number",
         reply_buttons=all_boards,
         context=context)


def start_session(update: Update, context: CallbackContext):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if update.effective_chat.username in DIRECTORS:
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
        try:
            cursor.execute(statement)
        except:
            pass
        conn.commit()

        context.bot_data["maxboard"] = 0
        context.bot_data["maxpair"] = 0
        context.user_data["currentHand"] = None
        context.user_data["result"] = None
        send(chat_id=update.effective_chat.id,
             text="Started session. Enter number of boards",
             reply_buttons=[],
             context=context)
    else:
        cursor.execute('select * from boards')
        boards = len(cursor.fetchall())
        cursor.execute('select * from protocols')
        protocols = len(cursor.fetchall())
        cursor.execute('select * from names')
        names = len(cursor.fetchall())
        boards_num = context.bot_data.get("maxboard")
        pairs_num = context.bot_data.get("maxpair")
        if boards_num and pairs_num:
            send(chat_id=update.effective_chat.id,
                 text=f"""Active session: {pairs_num} pairs
Submitted {boards} of {boards_num} boards
Submitted {protocols} results
Submitted {names} names""",
                 reply_buttons=[],
                 context=context)
        else:
            send(chat_id=update.effective_chat.id,
                 text=f"""Session not started yet""",
                 reply_buttons=[],
                 context=context)
    conn.close()


def names(update: Update, context: CallbackContext):
    context.user_data["names"] = 0
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("Select number from names")
    added = list(set([c[0] for c in cursor.fetchall()]))
    conn.close()
    all_pairs = range(1, context.bot_data["maxpair"] + 1)
    buttons = [l for l in all_pairs if l not in added]
    send(chat_id=update.effective_chat.id,
         text="Enter pair number",
         reply_buttons=buttons,
         context=context)


def names_text(update: Update, context: CallbackContext):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    statement = f"""INSERT INTO names (number, partnership)
                    VALUES({context.user_data["names"]}, '{update.message.text}');"""
    cursor.execute(statement)
    conn.commit()
    conn.close()
    context.user_data["names"] = None
    send(chat_id=update.effective_chat.id,
         text=f"What's next?",
         reply_buttons=("/names", "/board"),
         context=context)


def number(update: Update, context: CallbackContext):
    if context.user_data.get("names", -1) == 0:
        pair_number = int(update.message.text)
        context.user_data["names"] = pair_number
        send(chat_id=update.effective_chat.id,
             text=f"Enter names for pair #{pair_number}",
             reply_buttons=[],
             context=context)
        return
    if context.bot_data["maxboard"] and context.bot_data["maxpair"]:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"Select number from boards where number={update.message.text}")
        if cursor.fetchall():
            context.user_data["board"] = Board(number=update.message.text)
            conn.close()
            return result(update, context)
        context.user_data["board"] = Board()
        context.user_data["board"].number = update.message.text
        send(chat_id=update.effective_chat.id,
             text="Enter N hand",
             reply_buttons=[],
             context=context)

        hand = send(chat_id=update.effective_chat.id,
             text="♠\n♥\n♦\n♣",
             reply_buttons=context.user_data["board"].get_remaining_cards(),
             context=context)
        context.user_data["currentHand"] = hand
    elif context.bot_data["maxboard"]:
        context.bot_data["maxpair"] = int(update.message.text)
        send(chat_id=update.effective_chat.id,
             text="Enter board number",
             reply_buttons=list(range(1, context.bot_data["maxboard"] + 1)),
             context=context)
    else:
        context.bot_data["maxboard"] = int(update.message.text)
        send(chat_id=update.effective_chat.id,
                     text="Enter the number of pairs",
                     reply_buttons=[],
                     context=context)


def inline_key(update: Update, context: CallbackContext):
    key = update["callback_query"]["data"]
    if key.startswith("bm:"):
        key = key.split("bm:")[1]
        result_data = context.user_data["result"]

        if key.isdigit():
            next_field = result_data.text.split(CARET)[1].lstrip("\n")
            if next_field.startswith("Lead:"):
                new_text = re.sub(f"{CARET}", f"{key.upper()}{CARET}", result_data.text)
            else:
                new_text = re.sub(f"{CARET}\n([^:]+): ", f"{key.upper()}\n\g<1>: {CARET}", result_data.text, flags=re.MULTILINE)
            if next_field.startswith("EW: "):
                reply_markup = pairs_keyboard(context, exclude=key)
            else:
                reply_markup = CONTRACTS_KEYBOARD
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                           message_id=result_data.message_id,
                                                                           reply_markup=reply_markup,
                                                                           text=new_text,
                                                                           parse_mode=ParseMode.HTML)
        elif key in SUITS_UNICODE or key == "NT" or key.lower() in hands:
            if key.lower() in hands:
                new_text = re.sub(f"{CARET}\n([^:]+): ", f" {key.upper()}\n\g<1>: {CARET}", result_data.text, flags=re.MULTILINE)
                reply_markup = lead_keyboard()
            else:
                new_text = result_data.text.replace(CARET, key.upper() + CARET)
                reply_markup = CONTRACTS_KEYBOARD
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                      message_id=result_data.message_id,
                                                                      reply_markup=reply_markup,
                                                                      text=new_text,
                                                                      parse_mode=ParseMode.HTML)
        elif key in ("x", "xx"):
            if key == "pass":
                new_text = re.sub(f"{CARET}\n([^:]+): ", f"{key.upper()}\n\g<1>: {CARET}", result_data.text, flags=re.MULTILINE)
                new_text = re.sub(f"{CARET}\n([^:]+): ", f"\n\g<1>: {CARET}", new_text)


            else:
                new_text = re.sub(CARET, key + CARET, result_data.text, flags=re.MULTILINE)
            if key == "pass":
                reply_markup = NAVIGATION_KEYBOARD
            else:
                reply_markup = CONTRACTS_KEYBOARD
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                           message_id=result_data.message_id,
                                                                           reply_markup=reply_markup,
                                                                           text=new_text,
                                                                           parse_mode=ParseMode.HTML)
        elif result_re.match(key) or key == "pass":
            new_text = result_data.text.replace(CARET, f"{key}")
            contract = result_data.text.split("Contract: ")[1].split("\n")[0].lower().replace("nt", "n")

            if key == "pass":
                score = 0
            else:
                level = int(contract[0]) + 6
                denomination = contract[1]
                multiplier = "x" * contract.count("x")
                declarer = contract[-1]

                if key == "=":
                    tricks_taken = level
                else:
                    tricks_taken = eval(f"{level}{key}")
                score = context.user_data["board"].get_total_points(declarer, denomination, level,
                                                            tricks_taken, multiplier)
            new_text = new_text.replace("Score:", f"Score: {score}")
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                           message_id=result_data.message_id,
                                                                           text=new_text,
                                                                           reply_markup=NAVIGATION_KEYBOARD,
                                                                           parse_mode=ParseMode.HTML
                                                                      )
        elif CARD_RE.match(key):
            key = key.replace(key[0], SUITS_UNICODE["shdc".index(key[0])])
            new_text = re.sub(f"{CARET}\n([^:]+): ", f"{key.upper()}\n\g<1>: {CARET}", result_data.text, flags=re.MULTILINE)
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                           message_id=result_data.message_id,
                                                                           text=new_text,
                                                                           reply_markup=results_keyboard(context),
                                                                           parse_mode=ParseMode.HTML)


        elif key == "enter":
            board_number = context.user_data["board"].number
            ns = result_data.text.split("NS: ")[1].split("\n")[0]
            ew = result_data.text.split("EW: ")[1].split("\n")[0]
            contract = result_data.text.split("Contract: ")[1].split("\n")[0].lower().replace("nt", "n")

            if contract == "pass":
                score = 0
                declarer = ""
                tricks = ""
                lead = ""
            else:
                contract, declarer = contract.split(" ")
                lead = result_data.text.split("Lead: ")[1].split("\n")[0]
                tricks = result_data.text.split("Result: ")[1].split("\n")[0]
                score = int(result_data.text.split("Score: ")[1].split("\n")[0])


            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            statement = f"""
                    INSERT INTO protocols (number, ns, ew, contract, declarer, lead, result, score)
                    VALUES({board_number}, '{ns}', '{ew}', '{contract}', '{declarer}', '{lead}', '{tricks}', '{score}');"""
            cursor.execute(statement)
            conn.commit()
            conn.close()
            send(chat_id=update.effective_chat.id,
                 text=f"Result for board #{board_number} is saved",
                 reply_buttons=("/board",),
                 context=context)
        elif key == "left":
            return result(update, context)

    elif CARD_RE.match(key):
        suit = key[0]
        card = key[1]
        board = context.user_data["board"]
        hand = context.user_data["currentHand"]
        suit_before = hand.text.split("\n")["shdc".index(suit)]
        if card in suit_before:
            suit = suit_before.replace(card, "")
        else:
            suit = suit_before[0] + "".join(sorted(suit_before[1:] + card, key=lambda c: CARDS.index(c)))
        text = hand.text.replace(suit_before, suit)
        context.user_data["currentHand"] = context.bot.editMessageText(chat_id=hand["chat"]["id"],
                                                                       message_id=hand.message_id,
                                                                       text=text,
                                                                       reply_markup=board.get_remaining_cards(),
                                                                       parse_mode=ParseMode.HTML)
        if len(text) == 20:
            send(chat_id=update.effective_chat.id,
                 text=f"Next hand?",
                 reply_buttons=("OK", "Cancel"),
                 context=context)


def save(update: Update, context: CallbackContext):
    board = context.user_data["board"]
    board.save()
    result(update, context)
    # send(chat_id=update.effective_chat.id,
    #      text=f"Board {board.number} is saved",
    #      reply_buttons=("/board",),
    #      context=context)


def ok(update: Update, context: CallbackContext):
    board = context.user_data["board"]
    board.set_hand(context.user_data["currentHand"]["text"])
    if board.current_hand is None:
        board.save()
        send(chat_id=update.effective_chat.id,
             text=f"Board {board.number} is saved",
             reply_buttons=("/board",),
             context=context)
    elif board.current_hand == "w":
        w = board.get_w_hand()
        send(chat_id=update.effective_chat.id,
             text=f"W hand should be: {w}",
             reply_buttons=("Save", "Restart"),
             context=context)
    else:
        seat = board.current_hand.upper()
        send(chat_id=update.effective_chat.id,
             text=f"Enter {seat} hand",
             reply_buttons=[],
             context=context)

        context.user_data["currentHand"] = send(chat_id=update.effective_chat.id,
                                                text="♠\n♥\n♦\n♣",
                                                reply_buttons=board.get_remaining_cards(),
                                                context=context)


def cancel(update: Update, context: CallbackContext):
    board = context.user_data["board"]
    board.unset_hand()
    send(chat_id=update.effective_chat.id,
         text="Enter N hand again",
         reply_buttons=[],
         context=context)
    context.user_data["currentHand"] = send(chat_id=update.effective_chat.id,
         text="♠\n♥\n♦\n♣",
         reply_buttons=board.get_remaining_cards(),
         context=context)


def restart(update: Update, context: CallbackContext):
    board = context.user_data["board"]
    # if board.current_hand is None:
    number = board.number
    context.user_data["board"] = Board()
    context.user_data["board"].number = number
    board = context.user_data["board"]

    send(chat_id=update.effective_chat.id,
         text="Enter N hand again",
         reply_buttons=[],
         context=context)
    context.user_data["currentHand"] = send(chat_id=update.effective_chat.id,
         text="♠\n♥\n♦\n♣",
         reply_buttons=board.get_remaining_cards(),
         context=context)


def result(update: Update, context: CallbackContext):
    context.user_data["result"] = send(chat_id=update.effective_chat.id,
                                       text=f"Enter result:\nNS: {CARET}\nEW: \nContract: \nLead: \nResult: \nScore: ",
                                       reply_buttons=pairs_keyboard(context),
                                       context=context)


if __name__ == '__main__':
    updater = Updater(token=TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('session', start_session))
    updater.dispatcher.add_handler(CommandHandler('board', board))
    updater.dispatcher.add_handler(CommandHandler('names', names))

    updater.dispatcher.add_handler(MessageHandler(Filters.regex("^\d+$"), number))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("OK"), ok))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Save"), save))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Restart"), restart))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Cancel"), cancel))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex(" .* "), names_text))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex("\w+-\w+"), names_text))

    updater.dispatcher.add_handler(CommandHandler("result", result))
    updater.dispatcher.add_handler(CallbackQueryHandler(inline_key))

    updater.start_polling()
