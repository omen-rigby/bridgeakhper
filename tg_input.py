import shutil
import logging
from inline_key import *
from board import Board
from scoring import Scoring
from result_getter import ResultGetter
from generate import generate
from util import is_director
from movements.parse_mov import get_movement

PORT = int(os.environ.get('PORT', 8443))
if "DYNO" in os.environ:
    TOKEN = os.environ["BOT_TOKEN"]
else:
    TOKEN = CONFIG["token"]
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
    if is_director(update):
        generate()
        context.bot_data["maxboard"] = 0
        context.bot_data["maxpair"] = 0
        context.user_data["currentHand"] = None
        context.user_data["result"] = None
        send(chat_id=update.effective_chat.id,
             text="Started session. Enter scoring",
             reply_buttons=Scoring.all(),
             context=context)
    else:
        return missing(update, context)


def missing(update, context):
    conn = sqlite3.connect(db_path)
    boards_num = context.bot_data.get("maxboard")
    pairs_num = context.bot_data.get("maxpair")
    cursor = conn.cursor()
    cursor.execute('select * from boards')
    submitted_boards = [b[0] for b in cursor.fetchall()]
    boards = ", ".join([str(b) for b in range(1, boards_num + 1) if b not in submitted_boards])
    cursor.execute('select * from protocols')
    protocols = list(set(cursor.fetchall()))
    boards_with_missing_results = ", ".join([str(i) for i in range(1, boards_num + 1)
                                            if len([p for p in protocols if p[0] == i]) < pairs_num // 2])
    cursor.execute('select * from names')
    names = len(cursor.fetchall())
    if boards_num and pairs_num:
        send(chat_id=update.effective_chat.id,
             text=f"""Active session: {pairs_num} pairs
Missing boards: {boards}
Missing results for boards: {boards_with_missing_results}
Submitted {names} names""",
             reply_buttons=[],
             context=context)
    else:
        send(chat_id=update.effective_chat.id,
             text=f"""Session not started yet""",
             reply_buttons=[],
             context=context)
    conn.close()


def scoring(update: Update, context: CallbackContext):
    CONFIG["scoring"] = update.message.text
    if is_director(update):
        send(chat_id=update.effective_chat.id,
             text="Enter number of boards",
             reply_buttons=[],
             context=context)


def names(update: Update, context: CallbackContext):
    context.user_data["names"] = 0
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("Select number from names")
    added = list(set([c[0] for c in cursor.fetchall()]))
    if CONFIG["scoring"] == Scoring.match:
        added = ["AB"[a // 3 + 1] + str(a % 3 + 1) for a in added]
        all_pairs = ["A1", "A2", "A3", "B1", "B2", "B3"]
    else:
        all_pairs = range(1, context.bot_data["maxpair"] + 1)
    buttons = [l for l in all_pairs if l not in added]
    conn.close()

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
        if CONFIG["scoring"] == Scoring.match:
            pair_number = update.message.text[1] + "AB".index(update.message.text[0]) * 3
        else:
            pair_number = int(update.message.text)
        context.user_data["names"] = pair_number
        send(chat_id=update.effective_chat.id,
             text=f"Enter names for pair #{update.message.text}",
             reply_buttons=[],
             context=context)
        return
    if context.bot_data["maxboard"] and context.bot_data["maxpair"]:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"Select * from boards where number={update.message.text}")
        brd = cursor.fetchall()
        if brd:
            brd = brd[0]
            if context.user_data.get("view_board"):
                if not brd:
                    send(update.effective_chat.id, "Board not found", [], context)
                else:
                    n, ns, nh, nd, nc, es, eh, ed, ec, ss, sh, sd, sc, ws, wh, wd, wc = map(
                        lambda x: str(x).upper().replace("T", "10"), brd)
                    send(update.effective_chat.id, f"""Board {n}:
{ns:^24}
{nh:^24}
{nd:^24}
{nc:^24}
{ws:<18}{es}
{wh:<18}{eh}
{wd:<18}{ed}
{wc:<18}{ec}
{ss:^24}
{sh:^24}
{sd:^24}
{sc:^24}
""", [], context)
                context.user_data["view_board"] = False
                return
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
        context.bot_data["movement"] = get_movement(context.bot_data["maxpair"])
        send(chat_id=update.effective_chat.id,
             text="Enter board number",
             reply_buttons=list(range(1, context.bot_data["maxboard"] + 1)),
             context=context)
    else:
        if CONFIG["scoring"] == Scoring.match:
            context.bot_data["maxboard"] = int(update.message.text)
            context.bot_data["maxpair"] = 4
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
    hand = context.user_data["currentHand"]["text"].replace("10", "T")
    if len(hand) != 20:
        send(chat_id=update.effective_chat.id,
             text=f"Hand has incorrect number of cards ({len(hand) - 7}). Try again",
             reply_buttons=(),
             context=context)
        context.user_data["currentHand"] = send(chat_id=update.effective_chat.id,
                                                text=context.user_data["currentHand"]["text"],
                                                reply_buttons=board.get_remaining_cards(),
                                                context=context)
        return

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
    if not is_director(update):
        send(chat_id=chat_id, text="You don't have enough rights to see tourney results", context=context)
        return
    if 'DYNO' in os.environ:
        context.bot.send_document(chat_id, open(db_path, 'rb'))
    try:
        paths = ResultGetter(boards=context.bot_data["maxboard"], pairs=context.bot_data["maxpair"]).process()
        for path in paths:
            context.bot.send_document(chat_id, open(path, 'rb'))
    except Exception as e:
        send(chat_id=chat_id, text=f"Result getter failed with error: {e}", context=context)

    if 'DYNO' in os.environ:
        shutil.rmtree(date)


def view_board(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if not is_director(update):
        send(chat_id=chat_id, text="You don't have enough rights to see tourney boards", context=context)
        return
    context.user_data["view_board"] = True
    send(chat_id=chat_id, text=f"Enter board number",
         reply_buttons=range(1, context.bot_data["maxboard"] + 1), context=context)


def get_boards_only(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if not is_director(update):
        send(chat_id=chat_id, text="You don't have enough rights to see tourney boards", context=context)
        return
    path = ResultGetter(boards=context.bot_data["maxboard"], pairs=context.bot_data["maxpair"]).boards_only()
    context.bot.send_document(chat_id, open(path, 'rb'))


if __name__ == '__main__':
    updater = Updater(token=TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('session', start_session))
    updater.dispatcher.add_handler(CommandHandler('board', board))
    updater.dispatcher.add_handler(CommandHandler('names', names))

    # User input
    updater.dispatcher.add_handler(MessageHandler(Filters.regex("^\d+$"), number))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("OK"), ok))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Save"), save))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Restart"), restart))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Cancel"), cancel))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex(Scoring.re()), scoring))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex(" .* "), names_text))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex("\w+-\w+"), names_text))
    updater.dispatcher.add_handler(CallbackQueryHandler(inline_key))
    # Results
    updater.dispatcher.add_handler(CommandHandler("result", result))
    updater.dispatcher.add_handler(CommandHandler("missing", missing))
    updater.dispatcher.add_handler(CommandHandler("view_board", view_board))
    updater.dispatcher.add_handler(CommandHandler("boards", get_boards_only))
    updater.dispatcher.add_handler(CommandHandler("end", end))
    if 'DYNO' in os.environ:
        updater.start_webhook(listen="0.0.0.0",
                              port=int(PORT),
                              url_path=TOKEN,
                              webhook_url=f"https://bridgeakhper.herokuapp.com/{TOKEN}"
                              )
    else:
        updater.start_polling()

    updater.idle()
