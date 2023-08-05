import psycopg2
import urllib.parse as up
import sqlite3
import os
import csv
from constants import db_path, SUITS, SUITS_UNICODE
from players import Players
from util import connect_mdb, revert_name
up.uses_netloc.append("postgres")


class TourneyDB:
    @staticmethod
    def connect(local=None):
        if not local and db_path.startswith('postgres:'):
            url = up.urlparse(db_path)
            return psycopg2.connect(database=url.path[1:],
                                    user=url.username,
                                    password=url.password,
                                    host=url.hostname,
                                    port=url.port
                                    )
        else:
            path = local or db_path
            return sqlite3.connect(path)

    @staticmethod
    def _create_tables(conn, flavor='sqlite'):
        int_type = 'int4' if flavor == 'postgres' else 'integer'
        float_type = 'float4' if flavor == 'postgres' else 'float'
        cursor = conn.cursor()
        statement = f"""CREATE TABLE "boards" (
                                "number"	{int_type}  PRIMARY KEY,
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
        statement = f"""CREATE TABLE "protocols" (
                                        "number"	{int_type},
                                        "ns"	{int_type},
                                        "ew"	{int_type},
                                        "contract"	TEXT,
                                        "declarer"	TEXT,
                                        "lead"	TEXT,
                                        "result"  TEXT,
                                        "score"	{int_type},
                                        "mp_ns" {float_type},
                                        "mp_ew" {float_type}
                                    )"""
        cursor.execute(statement)
        if flavor == 'postgres':
            constraint = 'ALTER TABLE public.protocols ADD CONSTRAINT protocols_un UNIQUE ("number",ns,ew);'
            cursor.execute(constraint)
        statement = f"""CREATE TABLE "names" (
                                        "number"	{int_type}  PRIMARY KEY,
                                        "partnership"	TEXT,
                                        "penalty"   {float_type} DEFAULT 0
                                    )"""
        cursor.execute(statement)

        statement = f"""CREATE TABLE "config" (
                                        "key"	TEXT  PRIMARY KEY,
                                        "value"	TEXT
                                    )"""
        cursor.execute(statement)

        statement = f"""CREATE TABLE "movements" (
                                        "tables"	{int_type},
                                        "movement"	TEXT,
                                        "is_mitchell"  {int_type if flavor != 'postgres' else 'bool'}  NOT NULL DEFAULT 0,
                                        "initial_board_sets"  TEXT
                                    )"""
        cursor.execute(statement)
        conn.commit()

    @staticmethod
    def create_tables(flavor='sqlite'):
        conn = TourneyDB.connect()
        TourneyDB._create_tables(conn, flavor=flavor)
        conn.close()

    @staticmethod
    def clear_tables():
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        for table in ('names', 'protocols', 'boards'):
            cursor.execute(f"delete from {table}")
        conn.commit()
        conn.close()

    @staticmethod
    def dump():
        dump_path = "boards.db"
        if os.path.exists(dump_path):
            os.remove(dump_path)
        conn = TourneyDB.connect(local=dump_path)
        cursor = conn.cursor()
        TourneyDB._create_tables(conn)
        conn2 = TourneyDB.connect()
        cur2 = conn2.cursor()
        cur2.execute("select * from names")
        names = cur2.fetchall()
        for d in names:
            rows = f"({d[0]}, '{d[1]}')"
            insert = f"""INSERT INTO names (number, partnership) VALUES {rows};"""
            cursor.execute(insert)
        cur2.execute("select * from boards")
        boards = cur2.fetchall()
        for d in boards:
            rows = f"({d[0]}" + "".join(f", '{dd}'" for dd in d[1:]) + ')'
            insert = f"""INSERT INTO boards (number, ns, nh, nd, nc, es, eh, ed, ec, ss, sh, sd, sc, ws, wh, wd, wc) 
VALUES {rows};"""
            cursor.execute(insert)
        cur2.execute("select number, ns, ew, contract, declarer, lead, result, score from protocols")
        boards = cur2.fetchall()
        for d in boards:
            rows = f"({d[0]}, {d[1]}, {d[2]}, '{d[3]}', '{d[4]}', '{d[5]}', '{d[6]}', {d[7]})"

            insert = f"INSERT INTO protocols (number, ns, ew, contract, declarer, lead, result, score) VALUES {rows};"
            cursor.execute(insert)
        cur2.execute("select key, value from config")
        for key, value in cur2.fetchall():
            rows = f"('{key}', '{value}')"
            insert = f"INSERT INTO config (key, value) VALUES {rows};"
            cursor.execute(insert)
        cur2.execute("select tables, movement, is_mitchell, initial_board_sets from movements")
        for tables, movement, is_mitchell, board_sets in cur2.fetchall():
            rows = f"({tables}, '{movement}', {is_mitchell}, '{board_sets}')"
            insert = f"INSERT INTO movements (tables, movement, is_mitchell, initial_board_sets) VALUES {rows};"
            cursor.execute(insert)
        conn.commit()
        conn.close()
        conn2.close()
        return dump_path

    @staticmethod
    def to_access(city):
        mdb_path = "templates/mdb.bws"
        ms_conn = connect_mdb(mdb_path)
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        cursor.execute('select * from protocols where number > 0')
        protocols = cursor.fetchall()
        players = max(max(p[1] for p in protocols), max(p[2] for p in protocols))
        ms_cursor = ms_conn.cursor()
        ms_cursor.execute('delete from ReceivedData')
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
            table = (ns - 1) // 2 + 1
            round_n = (ns + ew - 1) % (players - 1) + 1
            rows = f"({i + 1}, 1, {table}, {round_n}, {number}, {ns}, {ew}, {decl_num}, " \
                   f"'{declarer}', '{contract}', '{result}', '{lead}', '{remarks}')"

            insert = f"INSERT INTO ReceivedData (ID, Section, Table, Round, Board, PairNS, PairEW, Declarer, [NS/EW]," \
                     f" Contract, Result, LeadCard, Remarks) VALUES {rows};"
            ms_cursor.execute(insert)
        ms_cursor.execute(f'update Session set Name="{city}"')
        ms_conn.commit()
        ms_conn.close()
        cursor.execute("select * from names order by number")
        raw = cursor.fetchall()
        players = Players.get_players()
        players_path = 'players.csv'
        with open(players_path, 'w', newline='', encoding="cp1251") as csvfile:
            writer = csv.writer(csvfile, delimiter=';', quotechar='"')
            for number, raw_pair in enumerate(raw):
                raw_data = Players.lookup(raw_pair[1], players)
                rank = str((raw_data[0][2] + raw_data[1][2])/2).replace('.', ",")
                writer.writerow([number + 1,
                                 revert_name(raw_data[0][0]),
                                 revert_name(raw_data[1][0]), '0', rank])

        conn.close()
        return mdb_path, players_path


if __name__ == "__main__":
    TourneyDB.create_tables('postgres')


