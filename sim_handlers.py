import itertools
import os
import csv
import time

from inline_key import send
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import *
from util import connect_mdb


class SimHandlers:
    mdb_path = 'templates/mdb.bws'
    starting_index = 600

    @staticmethod
    def start_sim_tourney(update: Update, context: CallbackContext):
        context.bot_data["results"] = []
        context.bot_data["names"] = []
        context.bot_data["numbers"] = []

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
        if context.bot_data.get("results") is None:
            context.bot.send_message(chat_id=update.message.from_user.id,
                                     text="Simultaneous tournament not started")
        filename = update.message.document.get_file().download()
        agg_conn = connect_mdb(SimHandlers.mdb_path)
        agg_cur = agg_conn.cursor()
        conn = connect_mdb(filename)
        cursor = conn.cursor()
        cursor.execute(f"select ID, [Section], [Table], [Round], Board, PairNS, PairEW, Declarer," \
                        " [NS/EW], Contract, [Result], LeadCard, Remarks from ReceivedData")
        results = cursor.fetchall()
        if filename in context.bot_data["results"]:
            section = context.bot_data["results"].index(filename)
            agg_cur.execute(f"delete from ReceivedData where Section={section}")
        else:
            section = len(context.bot_data["numbers"]) + 1
        agg_cur.execute('select PairNS, PairEW from ReceivedData')
        numbers = agg_cur.fetchall()
        last = max(itertools.chain(*numbers)) if numbers else SimHandlers.starting_index - 2
        first = last + 1 - (last + 1) % 10 + 10
        context.bot_data["numbers"].append(first)
        current_increment = min(itertools.chain(*[r[5:7] for r in results])) - 1
        increment = first - current_increment
        for r in results:
            rows = f"({section}, {r[2]}, {r[3]}, {r[4]}, {r[5] + increment}, {r[6] + increment}, {r[7] + increment}, " \
                   f"'{r[8]}', '{r[9]}', '{r[10]}', '{r[11]}', '{r[12]}')"
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
    def upload_csv(update: Update, context: CallbackContext):
        if context.bot_data.get("results") is None:
            context.bot.send_message(chat_id=update.message.from_user.id,
                                     text="Simultaneous tournament not started")
        timeout = 10 + time.time()
        while not context.user_data.get("bws_uploaded") and time.time() < timeout:
            pass
        if time.time() > timeout:
            context.bot.send_message(chat_id=update.message.from_user.id,
                                     text="BWS not received")
            return
        filename = update.message.document.get_file().download()
        agg_conn = connect_mdb(SimHandlers.mdb_path)
        agg_cur = agg_conn.cursor()
        agg_cur.execute('select section, PairNS, PairEW from ReceivedData')
        results = agg_cur.fetchall()
        max_session = max([r[0] for r in results]) if results else 0
        with open(filename, encoding='cp1251') as players_file:
            contents = players_file.read().split('\n')[:-1]
            if max_session:
                # mdb id already processed
                first = context.bot_data["numbers"][-1]
            else:
                first = SimHandlers.starting_index
            for i, row in enumerate(csv.reader(contents, delimiter=';', quotechar='"')):
                row[0] = i + 1 + first
                context.bot_data['names'].append(row)

        os.remove(filename)
        context.user_data["bws_uploaded"] = False

        send(chat_id=update.message.from_user.id,
             text="Results are added",
             context=context)

    @staticmethod
    def list_venues(update: Update, context: CallbackContext):
        if context.bot_data["results"]:
            send(chat_id=update.message.from_user.id,
                 text="Loaded bws files: \n" + "\n".join(context.bot_data["results"]),
                 context=context)
        else:
            send(chat_id=update.message.from_user.id, text="No results yet", context=context)

    @staticmethod
    def aggregate(update: Update, context: CallbackContext):
        players_path = 'players.csv'
        with open(players_path, 'w', newline='', encoding="cp1251") as csvfile:
            writer = csv.writer(csvfile, delimiter=';', quotechar='"')
            writer.writerows(context.bot_data['names'])

        context.bot.send_document(update.message.from_user.id, open(SimHandlers.mdb_path, 'rb'))
        context.bot.send_document(update.message.from_user.id, open(players_path, 'rb'))
        agg_conn = connect_mdb(SimHandlers.mdb_path)
        agg_cur = agg_conn.cursor()
        agg_cur.execute("")
        tables = 0  # TODO: add metadata
        #send("")

