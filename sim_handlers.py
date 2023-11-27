import itertools
import os
import csv
import time
import sqlite3

from inline_key import send
from telegram import Update
from telegram.ext import *
from util import connect_mdb, revert_name, decorate_all_functions
from constants import SUITS, SUITS_UNICODE
from functools import wraps
from config import CONFIG


def command_eligibility(func):
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext):
        if CONFIG["city"]:
            send(chat_id=update.effective_chat.id, text="Use regular bot", context=context)
            raise Exception("Bad command")
    return wrapper


@decorate_all_functions(command_eligibility)
class SimHandlers:
    mdb_path = 'templates/mdb.bws'
    starting_index = 600

    @staticmethod
    def start_sim_tourney(update: Update, context: CallbackContext):
        context.bot_data["results"] = []
        context.bot_data["venues"] = []
        context.bot_data["names"] = []
        context.bot_data["numbers"] = []
        context.bot_data["tables"] = 0
        ms_conn = connect_mdb(SimHandlers.mdb_path)
        ms_cursor = ms_conn.cursor()
        ms_cursor.execute('delete from ReceivedData')
        ms_conn.commit()
        ms_conn.close()
        send(chat_id=update.message.from_user.id,
             text="Started simultaneous tournament.\nAwaiting results from venues...",
             context=context)

    @staticmethod
    def upload_mdb(update: Update, context: CallbackContext):
        """
        Results are added in the section, the venue is encoded by the tens digit of table number
        """
        if context.bot_data.get("results") is None:
            context.bot.send_message(chat_id=update.message.from_user.id,
                                     text="Simultaneous tournament not started")
        filename = update.message.document.get_file().download()
        agg_conn = connect_mdb(SimHandlers.mdb_path)
        agg_cur = agg_conn.cursor()
        conn = connect_mdb(filename)
        cursor = conn.cursor()
        real_name = update.message.document.file_name
        cursor.execute("select Name from Session")
        fetch_res = cursor.fetchone()[0]
        city = fetch_res if fetch_res != "Bridge game" else real_name
        bot_results = context.bot_data["results"]
        replacing_section = real_name in bot_results or city in bot_results
        if replacing_section:
            section = bot_results.index(real_name) if real_name in bot_results else bot_results.index(city)
            agg_cur.execute(
                f'select PairNS,PairEW from ReceivedData where [Table]<{10*(section + 1)} and [Table] > {10 * section}'
            )
            pairs = agg_cur.fetchall()
            pairs_unique = set(itertools.chain(*pairs))
            existing_tables = len(pairs_unique) // 2
            agg_cur.execute(f"delete from ReceivedData where [Table] < {10*(section + 1)} and [Table] > {10 * section}")
            context.bot_data["tables"] -= existing_tables
            first = min(pairs_unique)
            context.bot_data["names"] = [x for x in context.bot_data["names"] if x[0] not in pairs_unique]
            context.bot_data["numbers"].remove(first - 1)
            context.bot_data["numbers"].append(first - 1)
        else:
            section = len(context.bot_data["numbers"])
            context.bot_data["venues"].append(city)
            agg_cur.execute('select PairNS, PairEW from ReceivedData')
            numbers = agg_cur.fetchall()
            last = max(itertools.chain(*numbers)) if numbers else SimHandlers.starting_index - 2
            first = last + 1 - (last + 1) % 10 + 10
            context.bot_data["numbers"].append(first)

        cursor.execute(f"""select ID, [Section], [Table], [Round], Board, PairNS, PairEW, Declarer,
[NS/EW], Contract, [Result], LeadCard, Remarks from ReceivedData""")
        results = cursor.fetchall()
        tables = len(set(itertools.chain(*[r[5:7] for r in results]))) // 2
        context.bot_data["tables"] += tables
        first_pair = min(itertools.chain(*[r[5:7] for r in results]))
        current_increment = first_pair - 1 - (first_pair % 10 == 2)  # odd without 1st pair
        increment = first - current_increment
        for r in results:
            rows = f"(1, {r[2] + section * 10}, {r[3]}, {r[4]}, {r[5] + increment}, {r[6] + increment}, " \
                   f"{r[7] + increment}, '{r[8]}', '{r[9]}', '{r[10]}', '{r[11]}', '{r[12]}')"
            insert = f"INSERT INTO ReceivedData (Section, Table, Round, Board, PairNS, PairEW, Declarer, [NS/EW]," \
                     f" Contract, Result, LeadCard, Remarks) VALUES {rows};"
            agg_cur.execute(insert)
        agg_conn.commit()
        context.bot_data["results"].append(update.message.document.file_name)
        conn.close()
        agg_conn.close()
        os.remove(filename)
        context.user_data["bws_uploaded"] = True

    @staticmethod
    def upload_sqlite(update: Update, context: CallbackContext):
        """
        Results are added in the section, the venue is encoded by the tens digit of table number
        """
        if context.bot_data.get("results") is None:
            context.bot.send_message(chat_id=update.message.from_user.id,
                                     text="Simultaneous tournament not started")
        filename = update.message.document.get_file().download()
        agg_conn = connect_mdb(SimHandlers.mdb_path)
        agg_cur = agg_conn.cursor()
        conn = sqlite3.connect(filename)
        cursor = conn.cursor()
        real_name = update.message.document.file_name
        # Handles city (12).db
        city = real_name.split('.')[0].split('(')[0].strip()
        bot_results = context.bot_data["results"]
        replacing_section = real_name in bot_results or city in bot_results
        if replacing_section:
            section = bot_results.index(real_name) if real_name in bot_results else bot_results.index(city)
            agg_cur.execute(
                f'select PairNS,PairEW from ReceivedData where [Table]<{10 * (section + 1)} and [Table] > {10 * section}'
            )
            pairs = agg_cur.fetchall()
            pairs_unique = set(itertools.chain(*pairs))
            existing_tables = len(pairs_unique) // 2
            agg_cur.execute(
                f"delete from ReceivedData where [Table] < {10 * (section + 1)} and [Table] > {10 * section}")
            context.bot_data["tables"] -= existing_tables
            first = min(pairs_unique)
            context.bot_data["names"] = [x for x in context.bot_data["names"] if x[0] not in pairs_unique]
            context.bot_data["numbers"].remove(first - first % 10)
            context.bot_data["numbers"].append(first - first % 10)
        else:
            section = len(context.bot_data["numbers"])
            context.bot_data["venues"].append(city)
            agg_cur.execute('select PairNS, PairEW from ReceivedData')
            numbers = agg_cur.fetchall()
            last = max(itertools.chain(*numbers)) if numbers else SimHandlers.starting_index - 2
            first = last + 1 - (last + 1) % 10 + 10
            context.bot_data["numbers"].append(first)
        cursor.execute('select * from protocols where number > 0')
        protocols = cursor.fetchall()
        players = max(max(p[1] for p in protocols), max(p[2] for p in protocols))
        all_pairs = set(itertools.chain(*[r[1:3] for r in protocols]))
        tables = len(all_pairs) // 2
        context.bot_data["tables"] += tables
        first_pair = min(all_pairs)
        current_increment = first_pair - 1 - (first_pair % 10 == 2)  # odd without 1st pair
        increment = first - current_increment
        increment = increment - increment % 10  # paranoid check
        for i, p in enumerate(protocols):
            number, ns, ew, contract, declarer, lead, result, score = p[:8]
            if score == 1:
                remarks = contract.replace('/', '%-') + '%'
                contract = ''
            else:
                remarks = ''
            # PASS is played by NS
            decl_num = ew if declarer and declarer.lower() in 'ew' else ns
            contract = contract.upper().replace('XX', ' xx').replace('X', ' x')
            if contract and contract[0].isdigit():
                contract = f"{contract[0]} {contract[1:]}"
                if contract[2] == "N" and (len(contract) == 3 or contract[3] != "T"):
                    contract = contract.replace('N', 'NT')
            for new, old in zip(SUITS, SUITS_UNICODE):
                lead = lead.replace(old, new)
                contract = contract.replace(old, new.upper())
            lead = lead.upper()
            declarer = declarer.upper()
            # The two numbers below have no meaning yet look consistent
            table = (ns - 1) // 2 + 1 + section * 10
            round_n = (ns + ew - 1) % (players - 1) + 1
            rows = f"({i + 1}, 1, {table}, {round_n}, {number}, {ns + increment}, {ew + increment}, " \
                   f"{decl_num + increment}, '{declarer}', '{contract}', '{result}', '{lead}', '{remarks}')"

            insert = f"INSERT INTO ReceivedData (ID, Section, Table, Round, Board, PairNS, PairEW, Declarer, [NS/EW]," \
                     f" Contract, Result, LeadCard, Remarks) VALUES {rows};"
            agg_cur.execute(insert)
        agg_conn.commit()
        context.bot_data["results"].append(update.message.document.file_name)
        cursor.execute("select number, partnership, rank_ru from names order by number")
        names = cursor.fetchall()
        for (number, partnership, rank_ru) in names:
            names = partnership.split(' & ')
            rank = str(rank_ru).replace('.', ",")
            context.bot_data['names'].append([increment + number, revert_name(names[0]),
                                              # '0' is for rating
                                              revert_name(names[1]), '0', rank, city])
        conn.close()
        agg_conn.close()
        os.remove(filename)

        context.bot.send_message(chat_id=update.message.from_user.id,
                                 text=f"Uploaded {city} results")

    @staticmethod
    def upload_csv(update: Update, context: CallbackContext):
        if context.bot_data.get("results") is None:
            context.bot.send_message(chat_id=update.message.from_user.id,
                                     text="Simultaneous tournament not started")
        timeout = 15 + time.time()
        while not context.user_data.get("bws_uploaded") and time.time() < timeout:
            pass
        if time.time() > timeout:
            context.bot.send_message(chat_id=update.message.from_user.id,
                                     text="BWS not received")
            return
        filename = update.message.document.get_file().download()
        agg_conn = connect_mdb(SimHandlers.mdb_path)
        agg_cur = agg_conn.cursor()
        agg_cur.execute('select [Table], PairNS, PairEW from ReceivedData')
        results = agg_cur.fetchall()
        agg_conn.close()
        max_session = max([r[0] for r in results]) // 10 + 1 if results else 0
        city = context.bot_data["venues"][-1]
        with open(filename, encoding='cp1251') as players_file:
            contents = players_file.read().split('\n')[:-1]
            if max_session:
                # mdb id already processed
                first = context.bot_data["numbers"][-1]
            else:
                first = SimHandlers.starting_index
            for i, row in enumerate(csv.reader(contents, delimiter=';', quotechar='"')):
                row[0] = i + 1 + first
                row.append(city)
                context.bot_data['names'].append(row)

        os.remove(filename)
        context.user_data["bws_uploaded"] = False

        send(chat_id=update.message.from_user.id,
             text="Results are added",
             context=context)

    @staticmethod
    def list_venues(update: Update, context: CallbackContext):
        if context.bot_data["venues"]:
            send(chat_id=update.message.from_user.id,
                 text="Loaded bws files: \n" + "\n".join(context.bot_data["venues"]),
                 context=context)
        else:
            send(chat_id=update.message.from_user.id, text="No results yet", context=context)

    @staticmethod
    def aggregate(update: Update, context: CallbackContext):
        players_path = 'players.csv'
        with open(players_path, 'w', newline='', encoding="cp1251") as csvfile:
            writer = csv.writer(csvfile, delimiter=';', quotechar='"')
            writer.writerows(sorted(context.bot_data['names'], key=lambda x: x[0]))

        context.bot.send_document(update.message.from_user.id, open(SimHandlers.mdb_path, 'rb'))
        context.bot.send_document(update.message.from_user.id, open(players_path, 'rb'))
        venues = len(context.bot_data["venues"])
        tables = context.bot_data["tables"]
        pairs = len(context.bot_data['names'])
        send(chat_id=update.effective_chat.id,
             text=f"Total venues: {venues}\nTotal tables: {tables}\nTotal pairs: {pairs}",
             context=context)

