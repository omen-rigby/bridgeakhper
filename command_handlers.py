import shutil
from board import Board
from result_getter import ResultGetter
from generate import generate
from movements.parse_mov import get_movement
from players import *
from shutil import copyfile
from inline_key import *
from functools import wraps


def decorate_all_functions(function_decorator):
    def decorator(cls):
        for name, obj in vars(cls).items():
            if callable(obj) and name != 'end':
                setattr(cls, name, function_decorator(obj))
        return cls
    return decorator


def not_in_group(func):
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext):
        if update.effective_chat.id < 0:
            send(chat_id=update.effective_chat.id, text="This bot shouldn't be called in groups", context=context)
            context.bot.deleteMessage(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            raise Exception("Bad command")
        return func(update, context)
    return wrapper


@decorate_all_functions(not_in_group)
class CommandHandlers:
    @staticmethod
    def start(update: Update, context: CallbackContext):
        send(chat_id=update.effective_chat.id,
             text="Started bridgemate. What do you want to do?",
             reply_buttons=("/board",),
             context=context)

    @staticmethod
    def board(update: Update, context: CallbackContext):
        all_boards = list(range(1, context.bot_data["maxboard"] + 1))
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        cursor.execute("select * from protocols")
        protocols = cursor.fetchall()
        conn.close()
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

    @staticmethod
    def init(update: Update, context: CallbackContext):
        context.bot_data["maxboard"] = 0
        context.bot_data["maxpair"] = 0
        context.user_data["currentHand"] = None
        context.user_data["result"] = None
        CONFIG["tourney_coeff"] = 0.25
        send(chat_id=update.effective_chat.id,
             text="Started session. Enter scoring",
             reply_buttons=["MPs", "IMPs", "Cross-IMPs"],
             context=context)

    @staticmethod
    def clear_db(update: Update, context: CallbackContext):
        TourneyDB.clear_tables()
        CommandHandlers.init(update, context)

    @staticmethod
    def start_session(update: Update, context: CallbackContext):
        if is_director(update):
            if db_path.startswith('postgres:'):
                conn = TourneyDB.connect()
                cursor = conn.cursor()
                for table in ('boards', 'protocols', 'names'):
                    cursor.execute(f'select * from {table} LIMIT 1')
                    if cursor.fetchall():
                        break
                else:
                    return CommandHandlers.init(update, context)
                return send(chat_id=update.effective_chat.id,
                            text="Session exists in database. Remove and start new tournament?",
                            reply_buttons=["Clear", "Reuse"],
                            context=context)
            generate()
            CommandHandlers.init(update, context)
        else:
            return CommandHandlers.missing(update, context)

    @staticmethod
    def missing(update, context):
        conn = TourneyDB.connect()
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

    @staticmethod
    def scoring(update: Update, context: CallbackContext):
        CONFIG["scoring"] = update.message.text
        if is_director(update):
            send(chat_id=update.effective_chat.id,
                 text="Enter number of boards",
                 reply_buttons=[],
                 context=context)

    @staticmethod
    def names(update: Update, context: CallbackContext):
        context.user_data["names"] = 0
        conn = TourneyDB.connect()
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

    @staticmethod
    def freeform(update: Update, context: CallbackContext):
        text = update.message.text
        if context.user_data.get("tournament_title"):
            return CommandHandlers.title(update, context)
        if re.match('.*[-–—].*', text) or re.match(' .* ', text):
            return CommandHandlers.names_text(update, context)

    @staticmethod
    def names_text(update: Update, context: CallbackContext):
        global ALL_PLAYERS
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        statement = f"""INSERT INTO names (number, partnership)
                        VALUES({context.user_data["names"]}, '{update.message.text}') ON CONFLICT (number) DO UPDATE 
      SET partnership = excluded.partnership;"""
        cursor.execute(statement)
        conn.commit()
        conn.close()
        context.user_data["names"] = None
        found_pair_data = Players.lookup(update.message.text, ALL_PLAYERS)
        found_pair = " - ".join(p[0] for p in found_pair_data)
        send(chat_id=update.effective_chat.id,
             text=f"Identified as {found_pair}. What's next?",
             reply_buttons=("/names", "/board"),
             context=context)

    @staticmethod
    def number(update: Update, context: CallbackContext):
        if context.user_data.get("names", -1) == 0:
            pair_number = int(update.message.text)
            context.user_data["names"] = pair_number
            send(chat_id=update.effective_chat.id,
                 text=f"Enter names for pair #{pair_number}",
                 reply_buttons=[],
                 context=context)
            return
        if context.user_data.get("rounds"):
            context.user_data["rounds"] = False
            CONFIG["rounds"] = int(update.message.text)
            send(chat_id=update.effective_chat.id,
                 text=f"The number of rounds is set to {update.message.text}",
                 reply_buttons=[], context=context)
            return
        if context.bot_data["maxboard"] and context.bot_data["maxpair"]:
            conn = TourneyDB.connect()
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
                elif context.user_data.get("remove_board"):
                    context.user_data["remove_board"] = False
                    board_number = update.message.text.strip()
                    conn = TourneyDB.connect()
                    cursor = conn.cursor()
                    cursor.execute(f"delete from boards where number={board_number}")
                    conn.commit()
                    conn.close()
                    send(chat_id=update.effective_chat.id,
                         text=f"board #{board_number} has been removed",
                         reply_buttons=[], context=context)
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
            context.bot_data["maxboard"] = int(update.message.text)
            send(chat_id=update.effective_chat.id,
                 text="Enter the number of pairs",
                 reply_buttons=[],
                 context=context)

    @staticmethod
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
        if board.current_hand == "w":
            w = board.get_w_hand().replace("T", "10")
            send(chat_id=update.effective_chat.id,
                 text=f"W hand should be: {w}",
                 reply_buttons=[],
                 context=context)
            board.save()
            send(chat_id=update.effective_chat.id,
                 text=f"Board {board.number} is saved",
                 reply_buttons=("/board", "/result", "/restart"),
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

    @staticmethod
    def cancel(update: Update, context: CallbackContext):
        board = context.user_data["board"]
        board.unset_hand()
        hand = board.current_hand.upper()
        send(chat_id=update.effective_chat.id,
             text=f"Enter {hand} hand again",
             reply_buttons=[],
             context=context)
        context.user_data["currentHand"] = send(chat_id=update.effective_chat.id,
                                                text="♠\n♥\n♦\n♣",
                                                reply_buttons=board.get_remaining_cards(),
                                                context=context)

    @staticmethod
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

    @staticmethod
    def end(update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        if not is_director(update):
            send(chat_id=chat_id, text="You don't have enough rights to see tourney results", context=context)
            return
        if 'BOT_TOKEN' in os.environ and update.effective_chat.id > 0:
            path = TourneyDB.dump() if 'CURRENT_TOURNEY' in os.environ else db_path
            context.bot.send_document(chat_id, open(path, 'rb'))
            if 'CURRENT_TOURNEY' in os.environ:
                os.remove(path)
        try:
            context.bot_data['result_getter'] = ResultGetter(boards=context.bot_data["maxboard"],
                                                             pairs=context.bot_data["maxpair"])
            paths = context.bot_data['result_getter'].process()
            for path in paths:
                context.bot.send_document(chat_id, open(path, 'rb'))
                os.remove(path)
        except Exception as e:
            send(chat_id=chat_id, text=f"Result getter failed with error: {e}", context=context)
            raise

        if 'BOT_TOKEN' in os.environ and 'CURRENT_TOURNEY' not in os.environ:
            current_dir = os.getcwd()
            new_dir = f"{current_dir}/{date}"
            shutil.rmtree(new_dir)

    @staticmethod
    def remove_board(update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        if not is_director(update):
            send(chat_id=chat_id, text="You don't have enough rights to remove boards", context=context)
            return

        context.user_data["remove_board"] = True
        send(chat_id=update.effective_chat.id,
             text=f"Enter the number of board to remove",
             reply_buttons=[], context=context)

    @staticmethod
    def view_board(update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        if not is_director(update):
            send(chat_id=chat_id, text="You don't have enough rights to see tourney boards", context=context)
            return
        context.user_data["view_board"] = True
        send(chat_id=chat_id, text=f"Enter board number",
             reply_buttons=range(1, context.bot_data["maxboard"] + 1), context=context)

    @staticmethod
    def tourney_coeff(update: Update, context: CallbackContext):
        if context.user_data.get("tourney_coeff"):
            context.user_data["tourney_coeff"] = False
            new_coeff = float(update.message.text)
            CONFIG["tourney_coeff"] = new_coeff
            send(chat_id=update.effective_chat.id,
                 text=f"New tournament coefficient is {new_coeff}",
                 reply_buttons=[], context=context)
        else:
            context.user_data["tourney_coeff"] = True
            send(chat_id=update.effective_chat.id,
                 text=f"Enter new tounrey coeff (0.25 is the default)",
                 reply_buttons=[], context=context)

    @staticmethod
    def add_player(update: Update, context: CallbackContext):
        if context.user_data.get("add_player"):
            context.user_data["add_player"] = False
            first, last, gender, rank, rank_ru = update.message.text.split(" ")
            Players.add_new_player(first, last, gender, rank, rank_ru)
            global ALL_PLAYERS
            ALL_PLAYERS = Players.get_players()
        else:
            context.user_data["add_player"] = True
            send(chat_id=update.effective_chat.id,
                 text=f"Enter space-separated first name, last name, gender, rank, rank RU",
                 reply_buttons=[], context=context)

    @staticmethod
    def update_player(update: Update, context: CallbackContext):
        if context.user_data.get("update_player"):
            context.user_data["update_player"] = False
            last, rank, rank_ru = update.message.text.split(" ")
            Players.update(last, rank, rank_ru)
            global ALL_PLAYERS
            ALL_PLAYERS = Players.get_players()
        else:
            context.user_data["update_player"] = True
            send(chat_id=update.effective_chat.id,
                 text=f"Enter space-separated last name, rank, rank RU",
                 reply_buttons=[], context=context)

    @staticmethod
    def get_boards_only(update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        if not is_director(update):
            send(chat_id=chat_id, text="You don't have enough rights to see tourney boards", context=context)
            return
        path = ResultGetter(boards=context.bot_data["maxboard"], pairs=context.bot_data["maxpair"]).boards_only()
        context.bot.send_document(chat_id, open(path, 'rb'))

    @staticmethod
    def td_list(update: Update, context: CallbackContext):
        send(chat_id=update.message.chat_id, text=", ".join(DIRECTORS), context=context)

    @staticmethod
    def store(update: Update, context: CallbackContext):
        context.bot_data['result_getter'].save()

    @staticmethod
    def correct(update: Update, context: CallbackContext):
        context.bot_data['result_getter'].save(correction=True)

    @staticmethod
    def load_db(update: Update, context: CallbackContext):
        path = f'{date}/boards.db'
        if os.stat(path):
            os.remove(path)
        copyfile('testboards.db', path)

    @staticmethod
    def custom_movement(update: Update, context: CallbackContext):
        context.bot_data["movement"] = None

    @staticmethod
    def rounds(update: Update, context: CallbackContext):
        if not context.user_data.get("rounds"):
            context.user_data["rounds"] = True
            send(chat_id=update.effective_chat.id,
                 text=f"Enter the number of rounds",
                 reply_buttons=[], context=context)

    @staticmethod
    def title(update: Update, context: CallbackContext):
        if context.user_data.get("tournament_title"):
            context.user_data["tournament_title"] = False
            CONFIG["tournament_title"] = update.message.text
            send(chat_id=update.effective_chat.id,
                 text=f"Set tournament title to {update.message.text}",
                 reply_buttons=[], context=context)
        else:
            context.user_data["tournament_title"] = True
            send(chat_id=update.effective_chat.id,
                 text=f"Enter new tournament title",
                 reply_buttons=[], context=context)

    @staticmethod
    def monthly_report(update: Update, context: CallbackContext):
        send(chat_id=update.effective_chat.id,
             text=Players.monthly_report(),
             reply_buttons=[], context=context)

    @staticmethod
    def help_command(update: Update, context: CallbackContext):
        text = """General commands:
    /session: shows session info
    /board: starts deal entry flow
    /names: starts names entry flow"""
        if is_director(update):
            text = text.replace('shows session info', 'starts new session without db cleanup')
            text += """

    TD only commands:
    /tdlist: prints all TDs for the session
    /title: adds turney title
    /tourneycoeff: updates tournament coefficient
    /rounds: adjust the number of rounds  
    /custommovement: turns off preset movement
    /loaddb: (debug only) loads test set of boards and results from repo
    /rmboard: removes all hands for the specified board
    /restart: when submitting hands, reset all hands and starts again from N
    /result: starts board result entry flow
    /missing: shows session info
    /viewboard: shows 4 hands for specified board
    /addplayer: adds a new player to players DB
    /updateplayer: updates existing player record in players DB
    /boards: gets boards without results as pdf
    /end: gets tourney results, sends you raw db file & resulting pdfs, clears all data,
    /store: saves tourney results to yerevanbridge site db
    /monthlyreport: generates table with monthly MPs for RU players
            """

        send(chat_id=update.message.chat_id, text=text, context=context)