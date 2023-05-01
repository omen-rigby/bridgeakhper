from telegram import Update
from telegram.parsemode import ParseMode
from telegram.ext import *
from util import remove_suits
from keyboard import *
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
from tourney_db import TourneyDB

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
    return context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode=ParseMode.HTML)


def result(update: Update, context: CallbackContext):
    context.user_data["result"] = send(chat_id=update.effective_chat.id,
                                       text=f"Enter result:\nNS: {CARET}\nEW: \nContract: \nLead: \nResult: \nScore: ",
                                       reply_buttons=pairs_keyboard(update, context),
                                       context=context)


def inline_key(update: Update, context: CallbackContext):
    key = update["callback_query"]["data"]
    if key.startswith("bm:"):
        key = key.split("bm:")[1]
        result_data = context.user_data["result"]

        if key.isdigit():
            next_field = result_data.text.split(CARET)[1].lstrip("\n")
            if not next_field.startswith("Lead:") and \
                    int(result_data.text.split(CARET)[0].split(": ")[-1] + key) > context.bot_data["maxpair"]:
                # bad number submitted
                new_text = re.sub(f"\n([^:]+): .*{CARET}", f"\n\g<1>: {CARET}", result_data.text,
                                  flags=re.MULTILINE)
                new_text = f"Incorrect pair number, try again\n{new_text}"
                reply_markup = context.user_data["markups"][-1]
            else:
                if next_field.startswith("Lead:"):
                    new_text = re.sub(f"{CARET}", f"{key.upper()}{CARET}", result_data.text)
                    prev, tail = new_text.split(key + CARET)
                    if prev[-1] in SUITS_UNICODE:
                        new_text = f"{prev[:-1]}{key}{prev[-1]}{CARET}{tail}"
                else:
                    new_text = re.sub(f"{CARET}\n([^:]+): ", f"{key.upper()}\n\g<1>: {CARET}", result_data.text,
                                      flags=re.MULTILINE)
                if next_field.startswith("EW: "):
                    context.user_data["markups"] = [pairs_keyboard(update, context)]
                    reply_markup = pairs_keyboard(update, context, exclude=key)
                    context.user_data["markups"].append(reply_markup)
                else:
                    reply_markup = contracts_keyboard(update)
                    if context.user_data["markups"][-1] != reply_markup:
                        context.user_data["markups"].append(reply_markup)

            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                           message_id=result_data.message_id,
                                                                           reply_markup=reply_markup,
                                                                           text=new_text,
                                                                           parse_mode=ParseMode.HTML)
        elif key in SUITS_UNICODE or key == "NT" or key.lower() in hands:
            old_string = result_data.text.split(CARET)[0].split("\n")[-1]
            if key.lower() in hands:
                new_string = re.sub(f'[{hands}]$', "", old_string, flags=re.IGNORECASE)
                new_text = result_data.text.replace(old_string, new_string)
                if not CONTRACT_RE.match(new_string.split(": ")[1] + key):
                    # bad contract submitted
                    new_text = re.sub(f"\n([^:]+): .*{CARET}", f"\n\g<1>: {CARET}", result_data.text,
                                      flags=re.MULTILINE)
                    new_text = f"Incorrect contract, try again\n{new_text}"
                    reply_markup = contracts_keyboard(update)
                else:
                    new_text = re.sub(f"{CARET}\n([^:]+): ", f" {key.upper()}\n\g<1>: {CARET}", new_text,
                                      flags=re.MULTILINE)
                    reply_markup = lead_keyboard(update)
                    context.user_data["markups"].append(reply_markup)
            else:
                new_string = remove_suits(old_string.replace("NT", ""))
                new_text = result_data.text.replace(old_string, new_string)
                new_text = new_text.replace(CARET, key.upper() + CARET)
                reply_markup = contracts_keyboard(update)

            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                      message_id=result_data.message_id,
                                                                      reply_markup=reply_markup,
                                                                      text=new_text,
                                                                      parse_mode=ParseMode.HTML)
        elif key in ("x", "xx"):
            new_text = result_data.text.replace("x", "")
            new_text = re.sub(CARET, key + CARET, new_text, flags=re.MULTILINE)
            reply_markup = contracts_keyboard(update)
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                           message_id=result_data.message_id,
                                                                           reply_markup=reply_markup,
                                                                           text=new_text,
                                                                           parse_mode=ParseMode.HTML)
        elif result_re.match(key) or key == "pass" or ADJ_RE.match(key):
            new_text = result_data.text.replace(CARET, f"{key}")
            contract = result_data.text.split("Contract: ")[1].split("\n")[0].lower().replace("nt", "n")

            if key == "pass":
                score = 0
            elif ADJ_RE.match(key):
                # 1 stands for adjusted score
                score = 1

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
            board_number = context.user_data["board"].number
            ns = result_data.text.split("NS: ")[1].split("\n")[0]
            ew = result_data.text.split("EW: ")[1].split("\n")[0]
            contract = result_data.text.split("Contract: ")[1].split("\n")[0].lower().replace("nt", "n")

            if contract == "_":
                contract = key
                declarer = ""
                tricks = ""
                lead = ""
            else:
                contract, declarer = contract.split(" ")
                lead = result_data.text.split("Lead: ")[1].split("\n")[0]
                tricks = key

            conn = TourneyDB.connect()
            cursor = conn.cursor()
            statement = f"""INSERT INTO protocols (number, ns, ew, contract, declarer, lead, result, score)
                VALUES({board_number}, '{ns}', '{ew}', '{contract}', '{declarer}', '{lead}', '{tricks}', '{score}')
ON CONFLICT ON CONSTRAINT protocols_un DO UPDATE 
  SET contract = excluded.contract, lead = excluded.lead, result = excluded.result, score = excluded.score;"""
            cursor.execute(statement)
            conn.commit()
            conn.close()
            new_text = new_text.replace("Score:", f"Score: {score}\nResult for board #{board_number} is saved")
            lst = NAVIGATION_KEYBOARD + [InlineKeyboardButton('next board', callback_data='board'),
                                         InlineKeyboardButton('another result', callback_data='result')]
            reply_markup = InlineKeyboardMarkup([lst])
            context.user_data["markups"].append(reply_markup)
            context.user_data["result"] = context.bot\
                .editMessageText(chat_id=result_data["chat"]["id"],
                                 message_id=result_data.message_id,
                                 text=new_text,
                                 reply_markup=reply_markup,
                                 parse_mode=ParseMode.HTML
                                 )
        elif key == "more":
            reply_markup = contracts_keyboard(update, include_arbitral=True)
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                      message_id=result_data.message_id,
                                                                      text=result_data.text,
                                                                      reply_markup=reply_markup,
                                                                      parse_mode=ParseMode.HTML)

        elif CARD_RE.match(key):
            key = key.replace(key[0], SUITS_UNICODE["shdc".index(key[0])])
            new_text = re.sub(f"([{SUITS_UNICODE}][0-9AQKTJ])?{CARET}\n([^:]+): ", f"{key.upper()}\n\g<2>: {CARET}", result_data.text, flags=re.MULTILINE)
            reply_markup = results_keyboard(context)
            context.user_data["markups"].append(reply_markup)
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                      message_id=result_data.message_id,
                                                                      text=new_text,
                                                                      reply_markup=reply_markup,
                                                                      parse_mode=ParseMode.HTML)
        elif key == "nolead":
            new_text = re.sub(f"([{SUITS_UNICODE}][0-9AQKTJ])?{CARET}\n([^:]+): ", f"\n\g<2>: {CARET}",
                              result_data.text, flags=re.MULTILINE)
            reply_markup = results_keyboard(context)
            context.user_data["markups"].append(reply_markup)
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                      message_id=result_data.message_id,
                                                                      text=new_text,
                                                                      reply_markup=reply_markup,
                                                                      parse_mode=ParseMode.HTML)
        elif key == "restart":
            previous_result = context.user_data["result"]
            board_number = context.user_data["board"].number
            ns = previous_result.text.split("NS: ")[1].split("\n")[0]
            ew = previous_result.text.split("EW: ")[1].split("\n")[0]
            conn = TourneyDB.connect()
            cursor = conn.cursor()
            statement = f"""delete from protocols where number={board_number} and ns={ns}"""
            cursor.execute(statement)
            conn.commit()
            conn.close()
            return result(update, context)
        elif key == "rmall":
            number = context.user_data["board"].number
            conn = TourneyDB.connect()
            cursor = conn.cursor()
            statement = f"""select * from protocols where number={number}"""
            cursor.execute(statement)
            current_protocol = cursor.fetchall()
            statement = f"""delete from protocols where number={number}"""
            cursor.execute(statement)
            conn.commit()
            conn.close()
            if current_protocol:
                text = "Removed results:\n"
                text += '\n'.join([" ".join(map(lambda x: str(x).upper(), r[1:7])) for r in current_protocol])\
                    + '\n' + result_data.text
            else:
                text = result_data.text
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                      message_id=result_data.message_id,
                                                                      text=text,
                                                                      reply_markup=pairs_keyboard(update, context),
                                                                      parse_mode=ParseMode.HTML)
        elif key == "back":
            if f": {CARET}" in result_data.text:
                new_text = re.sub(f"\n([^:]+): {CARET}", f"{CARET}\n\g<1>: ", result_data.text,
                                  flags=re.MULTILINE)
                context.user_data["markups"].pop()
            elif CARET not in result_data.text:
                new_text = re.sub(f": (.*)\nScore: .*", f": \g<1>{CARET}\nScore: ", result_data.text,
                                  flags=re.MULTILINE)
                while not new_text.split(CARET)[0].split(": ")[-1]:
                    new_text = re.sub(f"\n([^:]+): {CARET}", f"{CARET}\n\g<1>: ", new_text,
                                      flags=re.MULTILINE)
                context.user_data["markups"].pop()

            else:
                new_text = re.sub(f"\n([^:]+): .*{CARET}", f"\n\g<1>: {CARET}", result_data.text,
                              flags=re.MULTILINE)
            reply_markup = context.user_data["markups"][-1]
            context.user_data["result"] = context.bot \
                .editMessageText(chat_id=result_data["chat"]["id"],
                                 message_id=result_data.message_id,
                                 text=new_text,
                                 reply_markup=reply_markup,
                                 parse_mode=ParseMode.HTML
                                 )
        elif key == "wrongdirection":
            context.user_data["reverted_directions"] = not context.user_data.get("reverted_directions")
            reply_markup = pairs_keyboard(update, context, reverted=context.user_data["reverted_directions"])
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                      message_id=result_data.message_id,
                                                                      reply_markup=reply_markup,
                                                                      text=result_data.text,
                                                                      parse_mode=ParseMode.HTML)
        elif OPPS_RE.match(key):
            match = OPPS_RE.match(key)
            ns = match.group(1)
            ew = match.group(2)
            new_text = re.sub(f"{CARET}\n([^:]+): ", f"{ns}\n\g<1>: {CARET}", result_data.text,
                              flags=re.MULTILINE)
            new_text = re.sub(f"{CARET}\n([^:]+): ", f"{ew}\n\g<1>: {CARET}", new_text,
                              flags=re.MULTILINE)
            reply_markup = contracts_keyboard(update)
            context.user_data["markups"] = [pairs_keyboard(update, context, use_movement=False),
                                            pairs_keyboard(update, context, exclude=ns, use_movement=False),
                                            reply_markup]
            context.user_data["result"] = context.bot.editMessageText(chat_id=result_data["chat"]["id"],
                                                                      message_id=result_data.message_id,
                                                                      reply_markup=reply_markup,
                                                                      text=new_text,
                                                                      parse_mode=ParseMode.HTML)

    elif CARD_RE.match(key):
        suit = key[0]
        card = key[1:].replace("10", "T")
        board = context.user_data["board"]
        hand = context.user_data["currentHand"]
        suit_before = hand.text.split("\n")["shdc".index(suit)].replace("10", "T")
        if card in suit_before:
            suit = suit_before.replace(card, "")
        else:
            suit = suit_before[0] + "".join(sorted(suit_before[1:] + card, key=lambda c: CARDS.index(c)))
        text = hand.text.replace(suit_before.replace("T", "10"), suit.replace("T", "10"))
        context.user_data["currentHand"] = context.bot.editMessageText(chat_id=hand["chat"]["id"],
                                                                       message_id=hand.message_id,
                                                                       text=text,
                                                                       reply_markup=board.get_remaining_cards(),
                                                                       parse_mode=ParseMode.HTML)

        if len(text.replace("10", "T")) == 20:
            send(chat_id=update.effective_chat.id,
                 text=f"Next hand?",
                 reply_buttons=("OK", "Cancel"),
                 context=context)
    elif key == "board":
        from command_handlers import CommandHandlers
        CommandHandlers.board(update, context)
    elif key == "result":
        result(update, context)

