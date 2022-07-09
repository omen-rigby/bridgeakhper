import logging
from inline_key import *
from board import Board
from result_getter import ResultGetter
from generate import generate
import os


PORT = int(os.environ.get('PORT', 5000))
TOKEN = CONFIG["token"]
DIRECTORS = CONFIG["directors"]
URL = f"https://api.telegram.org/bot{TOKEN}"
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)


def start(update: Update, context: CallbackContext):
    send(chat_id=update.effective_chat.id,
         text="Started bridgemate. What do you want to do?",
         reply_buttons=("/board",),
         context=context)


def board(update: Update, context: CallbackContext):
    all_boards = list(range(1, context.bot_data["maxboard"] + 1))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("select * from protocols")
    protocols = cursor.fetchall()
    unfinished = []
    for i in all_boards:
        played = set([p[1:3] for p in protocols if p[0] == i])
        if len(list(chain(*played))) < context.bot_data["maxpair"] - 1:
            unfinished.append(i)
    context.user_data["board"] = Board()
    send(chat_id=update.effective_chat.id,
         text="Enter board number",
         reply_buttons=unfinished,
         context=context)


def start_session(update: Update, context: CallbackContext):
    if update.effective_chat.username in DIRECTORS:
        generate()
        context.bot_data["maxboard"] = 0
        context.bot_data["maxpair"] = 0
        context.user_data["currentHand"] = None
        context.user_data["result"] = None
        send(chat_id=update.effective_chat.id,
             text="Started session. Enter number of boards",
             reply_buttons=[],
             context=context)
    else:
        return missing(update, context)


def missing(update, context):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
    statement = f"""REPLACE INTO names (number, partnership)
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
            # TODO: seems no longer needed
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
        w = board.get_w_hand().replace("T", "10")
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


def end(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if update.effective_chat.username not in DIRECTORS:
        send(chat_id=chat_id, text="You don't have enough rights to see tourney results", context=context)
        return
    paths = ResultGetter(boards=context.bot_data["maxboard"], pairs=context.bot_data["maxpair"]).process()

    for path in paths:
        context.bot.send_document(chat_id, open(path, 'rb'))


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
    updater.dispatcher.add_handler(CommandHandler("missing", missing))

    updater.dispatcher.add_handler(CommandHandler("result", result))
    updater.dispatcher.add_handler(CallbackQueryHandler(inline_key))
    updater.dispatcher.add_handler(CommandHandler("end", end))
    if 'DYNO' in os.environ:
        updater.start_webhook(listen="0.0.0.0",
                                  port=int(PORT),
                                  url_path=TOKEN)
        updater.bot.setWebhook('https://bridgeakhper.herokuapp.com/' + TOKEN)
    else:
        updater.start_polling()

    updater.idle()
