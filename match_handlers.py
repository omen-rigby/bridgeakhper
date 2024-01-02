from math import log10
from imps import vp
from inline_key import *
from players import *


class MatchHandlers:

    @staticmethod
    def match_score(update: Update, context: CallbackContext):
        context.user_data["match_result"]['score'] = None
        send(chat_id=update.effective_chat.id,
             text=f"Type results in IMPs for team A, e.g. -42",
             reply_buttons=[], context=context)

    @staticmethod
    def team_b(update: Update, context: CallbackContext):
        context.user_data["match_result"]['players']['B'] = []
        send(chat_id=update.effective_chat.id,
             text=f"Type players names for team B in separate messages",
             reply_buttons=[], context=context)

    @staticmethod
    def calculate(update: Update, context: CallbackContext):
        try:
            imps = int(update.message.text)
        except:
            send(chat_id=update.effective_chat.id,
                 text=f"Invalid result. Type in IMPs for team A, e.g. -42",
                 reply_buttons=[], context=context)
            return
        match_vps = vp(imps, boards=context.user_data["match_result"]['boards'])
        # AM
        # formula was designed for VP30 scale, so 1.5 is a workaround coefficient
        boards = context.user_data["match_result"]['boards']
        players = context.user_data["match_result"]['players']
        boards_coeff = 1 + log10(boards / 32) if boards >= 16 else 0
        a_rank = sum(p[1] for p in players['A']) / len(players['A'])
        b_rank = sum(p[1] for p in players['B']) / len(players['B'])
        ranks_coeff_a = (b_rank * b_rank + 4) / (a_rank + 1)
        ranks_coeff_b = (a_rank * a_rank + 4) / (b_rank + 1)
        status_coeff = 0.5  # TODO: add RA Championship variation with coefficient 1 or 2
        masterpoints_a = max(0, round((match_vps * 1.5 / 10 - 1) * boards_coeff * ranks_coeff_a * status_coeff))
        masterpoints_b = max(0, round(((20 - match_vps) * 1.5 / 10 - 1) * boards_coeff * ranks_coeff_b * status_coeff))
        if masterpoints_b + masterpoints_a == 0:
            # Winner's MPs are rounded to 1 if 0:0
            if match_vps >= 10:
                masterpoints_a = 1
            if match_vps <= 10:
                masterpoints_b = 1
        # RU http://old.bridgesport.ru/tools/mb_calc.htm function calculateMatch
        a_ru_rank = sum(p[2] for p in players['A']) / len(players['A'])
        b_ru_rank = sum(p[2] for p in players['B']) / len(players['B'])
        kd = 2.2 * log10(boards) - 2
        if match_vps > 10:
            kq = 0.2 / 1.6 ** b_ru_rank if b_ru_rank > 0 else 0.2 - 0.12 * b_ru_rank
            masterpoints_a_ru = round(50 * kq * kd * (match_vps / 5 - 2))
            masterpoints_b_ru = 0
        elif match_vps < 10:
            kq = 0.2 / 1.6 ** a_ru_rank if a_ru_rank > 0 else 0.2 - 0.12 * a_ru_rank
            masterpoints_b_ru = round(50 * kq * kd * ((20 - match_vps) / 5 - 2))
            masterpoints_a_ru = 0
        else:
            masterpoints_a_ru = masterpoints_b_ru = 0

        conn = Players.connect()
        cursor = conn.cursor()
        cursor.execute('select distinct id from matches')
        new_id = max([c[0] for c in cursor.fetchall()]) + 1
        match_date = context.user_data["match_result"]['date']
        for team in 'AB':
            for player in players[team]:
                mps = masterpoints_a if team == 'A' else masterpoints_b
                mps_ru = masterpoints_a_ru if team == 'A' else masterpoints_b_ru
                if mps > 0 or mps_ru > 0:
                    cursor.execute(f"""insert into matches ("id", "date", player, masterpoints, masterpoints_ru) 
                                           VALUES({new_id}, '{match_date}', '{player[0]}', {mps}, {mps_ru})""")
                    cursor.execute(f"select rating, last_year from players where TRIM(full_name)='{player[0]}'")
                    rating, last_year = cursor.fetchone()
                    cursor.execute(f"""update players set rating={rating + mps}, last_year={last_year + mps} 
                                           where TRIM(full_name)='{player[0]}'""")
        send(update.effective_chat.id, f'''VP: {round(match_vps, 2)} : {round(20 - match_vps, 2)}
Masterpoints: {masterpoints_a}:{masterpoints_b}
Masterpoints RU: {masterpoints_a_ru}:{masterpoints_b_ru}''', context=context)
        conn.commit()
        conn.close()
        context.user_data["match_result"] = None

    @staticmethod
    def add_match(update: Update, context: CallbackContext):
        if not context.user_data.get("match_result"):
            context.user_data["match_result"] = {'date': '', 'players': {}}
            # TODO: add telegram date selector widget if https://bugs.telegram.org/c/3144 ever gets fixed
            send(chat_id=update.effective_chat.id,
                 text=f"Enter match date, e.g. 2023/09/28",
                 reply_buttons=[], context=context)
        elif not context.user_data["match_result"]['date']:
            if re.match('\d{4}/\d{2}/\d{2}', update.message.text):
                context.user_data["match_result"]['date'] = update.message.text
                context.user_data["match_result"]['boards'] = None
                send(chat_id=update.effective_chat.id,
                     text=f"Enter the number of boards",
                     reply_buttons=[], context=context)
            else:
                send(chat_id=update.effective_chat.id,
                     text=f"Invalid date format, try again",
                     reply_buttons=[], context=context)
                return
        else:
            name = update.message.text
            player = Players.lookup(name, ALL_PLAYERS, single=True)[0]
            team = 'B' if context.user_data["match_result"]['players'].get('B') is not None else 'A'
            context.user_data["match_result"]['players'][team].append(player)
            send(chat_id=update.effective_chat.id,
                 text=f"Added player {player[0]} to team {team}",
                 reply_buttons=['/teamB' if team == 'A' else '/matchscore'], context=context)
