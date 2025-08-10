import psycopg2
import urllib.parse as up
import sqlite3
import os
from constants import db_path
from players import Players

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
                            );"""
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
                                        "mp_ew" {float_type},
                                        "round_number" {int_type},
                                        "table_number" {int_type}
                                    );"""
        cursor.execute(statement)
        if flavor == 'postgres':
            constraint = 'ALTER TABLE protocols ADD CONSTRAINT protocols_un UNIQUE ("number",ns,ew);'
            cursor.execute(constraint)
        statement = f"""CREATE TABLE "names" (
                                        "number"	{int_type}  PRIMARY KEY,
                                        "partnership"	TEXT,
                                        "penalty"   {float_type} DEFAULT 0,
                                        "rank"  {float_type},
                                        "rank_ru"  {float_type},
                                        "id_ru1" {int_type} DEFAULT 0,
                                        "id_ru2" {int_type} DEFAULT 0
                                    );"""
        cursor.execute(statement)

        statement = f"""CREATE TABLE "config" (
                                        "key"	TEXT  PRIMARY KEY,
                                        "value"	TEXT,
                                        "comment" TEXT
                                    );"""
        cursor.execute(statement)

        statement = f"""CREATE TABLE "movements" (
                                        "tables"	{int_type},
                                        "movement"	TEXT,
                                        "is_mitchell"  {int_type if flavor != 'postgres' else 'bool'}  NOT NULL DEFAULT 0,
                                        "is_barometer"  {int_type if flavor != 'postgres' else 'bool'}  NOT NULL DEFAULT 0,
                                        "initial_board_sets"  TEXT
                                    );"""
        cursor.execute(statement)
        if flavor == 'postgres':
            # 'ALTER TABLE public.names ALTER COLUMN penalty SET DEFAULT 0;'
            # 'ALTER TABLE public.boards ADD CONSTRAINT boards_pk PRIMARY KEY ("number");'
            # 'ALTER TABLE public.names ADD CONSTRAINT names_pk PRIMARY KEY ("number");'
            constraints = """ALTER TABLE ONLY protocols ADD CONSTRAINT protocols_un UNIQUE (number, ns, ew);"""
            cursor.execute(constraints)
        conn.commit()

    @staticmethod
    def create_tables(flavor='sqlite'):
        conn = TourneyDB.connect()
        TourneyDB._create_tables(conn, flavor=flavor)
        conn.close()

    @staticmethod
    def clear_tables(tables=('names', 'protocols', 'boards')):
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        for table in tables:
            cursor.execute(f"delete from {table}")
        conn.commit()
        conn.close()

    @staticmethod
    def dump(name=None, movement=None):
        dump_path = f'{name or "boards"}.db'
        if os.path.exists(dump_path):
            os.remove(dump_path)
        conn = TourneyDB.connect(local=dump_path)
        cursor = conn.cursor()
        TourneyDB._create_tables(conn)
        all_players = Players.get_players('full_name,id_ru')
        conn2 = TourneyDB.connect()
        cur2 = conn2.cursor()
        cur2.execute("select number, partnership, penalty, rank, rank_ru from names")
        names = cur2.fetchall()
        for d in names:
            pair_names = d[1].split(' & ')
            ids = [0] * len(pair_names)
            for p in all_players:
                if p[0] in pair_names:
                    index = pair_names.index(p[0])
                    ids[index] = p[1]
            rows = f"({d[0]}, '{d[1]}', {d[2] or 0}, {d[3]}, {d[4]},{ids[0]}, {ids[1]})"
            insert = f"""INSERT INTO names (number, partnership, penalty, rank, rank_ru, id_ru1, id_ru2) VALUES {rows};"""
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
            # TODO: Add data from movement
            round_n = table_n = 0
            rows = f"({d[0]}, {d[1]}, {d[2]}, '{d[3]}', '{d[4]}', '{d[5]}', '{d[6]}', {d[7]}, {round_n or 0}, {table_n or 0})"

            insert = f"""INSERT INTO protocols (number, ns, ew, contract, declarer, lead, result, score, 
            round_number, table_number) VALUES {rows};"""
            cursor.execute(insert)
        cur2.execute("select key, value from config")
        for key, value in cur2.fetchall():
            rows = f"('{key}', '{value}')"
            insert = f"INSERT INTO config (key, value) VALUES {rows} ON CONFLICT (key) DO UPDATE set value=excluded.value;"
            cursor.execute(insert)
        cur2.execute("select tables, movement, is_mitchell, is_barometer, initial_board_sets from movements")
        for tables, movement, is_mitchell, is_barometer, board_sets in cur2.fetchall():
            rows = f"({tables}, '{movement}', {is_mitchell}, {is_barometer}, '{board_sets}')"
            insert = f"INSERT INTO movements (tables, movement, is_mitchell, is_barometer, initial_board_sets) VALUES {rows};"
            cursor.execute(insert)
        conn.commit()
        conn.close()
        conn2.close()
        return dump_path

    @staticmethod
    def load(filename):
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        conn2 = TourneyDB.connect(local=filename)
        cur2 = conn2.cursor()
        cur2.execute("select number, partnership, penalty, rank, rank_ru from names")
        names = cur2.fetchall()
        for d in names:
            rows = f"({d[0]}, '{d[1]}', {d[2] or 0}, {d[3]}, {d[4]})"
            insert = f"""INSERT INTO names (number, partnership, penalty, rank, rank_ru) VALUES {rows};"""
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
        conn.commit()
        conn.close()
        conn2.close()


if __name__ == "__main__":
    from constants import CONFIG
    from players import ALL_PLAYERS
    conn = TourneyDB.connect()
    cur = conn.cursor()
    CONFIG["tourney_coeff"] = 1
    cur.execute("select number, partnership from names where number < 100 order by number desc")
    for (n, names) in cur.fetchall():
        print(names)
        print(Players.lookup(names, ALL_PLAYERS))
#    TourneyDB.create_tables('postgres')


