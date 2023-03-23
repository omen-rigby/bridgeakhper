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
                                        "partnership"	TEXT
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
        conn.commit()
        conn.close()
        conn2.close()
        return dump_path


if __name__ == "__main__":
    TourneyDB.create_tables(flavor='postgres')
    # from result_getter import ALL_PLAYERS
    #
    # conn = Players.connect()
    # cursor = conn.cursor()
    # cursor.execute("select * from names where tournament_id=1")
    # for d in cursor.fetchall():
    #     number = d[1]
    #     partnership = Players.lookup(d[2], ALL_PLAYERS)
    #     names = " & ".join([p[0] for p in partnership])
    #     rank = sum(p[1] for p in partnership) / len(partnership) * 2
    #     rank_ru = sum(p[2] for p in partnership) / len(partnership)
    #     cursor.execute(f"update names set partnership='{names}',rank={rank},rank_ru={rank_ru} where number={number}")
    # conn.commit()
    # conn.close()


