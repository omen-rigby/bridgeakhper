import psycopg2
import urllib.parse as up
import sqlite3
import os
from constants import db_path
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
                                        "mp_ew" {float_type}
                                    );"""
        cursor.execute(statement)
        if flavor == 'postgres':
            constraint = 'ALTER TABLE public.protocols ADD CONSTRAINT protocols_un UNIQUE ("number",ns,ew);'
            cursor.execute(constraint)
        statement = f"""CREATE TABLE "names" (
                                        "number"	{int_type}  PRIMARY KEY,
                                        "partnership"	TEXT,
                                        "penalty"   {float_type} DEFAULT 0,
                                        "rank"  {float_type},
                                        "rank_ru"  {float_type}
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
                                        "initial_board_sets"  TEXT
                                    );"""
        cursor.execute(statement)
        if flavor == 'postgres':
            constraints = """ALTER TABLE ONLY protocols ADD CONSTRAINT protocols_un UNIQUE (number, ns, ew);"""
            cursor.execute(constraints)
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
    def dump(name=None):
        dump_path = f'{name or "boards"}.db'
        if os.path.exists(dump_path):
            os.remove(dump_path)
        conn = TourneyDB.connect(local=dump_path)
        cursor = conn.cursor()
        TourneyDB._create_tables(conn)
        conn2 = TourneyDB.connect()
        cur2 = conn2.cursor()
        cur2.execute("select number, partnership, penalty, rank, rank_ru from names")
        names = cur2.fetchall()
        for d in names:
            rows = f"({d[0]}, '{d[1]}', {d[2]}, {d[3]}, {d[4]})"
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
    def load(filename):
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        conn2 = TourneyDB.connect(local=filename)
        cur2 = conn2.cursor()
        cur2.execute("select number, partnership, penalty, rank, rank_ru from names")
        names = cur2.fetchall()
        for d in names:
            rows = f"({d[0]}, '{d[1]}', {d[2]}, {d[3]}, {d[4]})"
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
    pass
    # TourneyDB.create_tables('postgres')


