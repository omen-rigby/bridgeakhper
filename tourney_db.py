import psycopg2
import urllib.parse as up
import sqlite3
import os
import jaydebeapi
from constants import db_path, SUITS, SUITS_UNICODE
from players import Players
up.uses_netloc.append("postgres")

mdb_path = "templates/yer_20230312pimp1.mdb"
# TODO: replace for cloud setup
ucanaccess_jars = [
    "/home/ibitkin/Downloads/UCanAccess-5.0.1.bin/ucanaccess-5.0.1.jar",
    "/home/ibitkin/Downloads/UCanAccess-5.0.1.bin/lib/commons-lang3-3.8.1.jar",
    "/home/ibitkin/Downloads/UCanAccess-5.0.1.bin/lib/commons-logging-1.2.jar",
    "/home/ibitkin/Downloads/UCanAccess-5.0.1.bin/lib/hsqldb-2.5.0.jar",
    "/home/ibitkin/Downloads/UCanAccess-5.0.1.bin/lib/jackcess-3.0.1.jar",
]
classpath = ":".join(ucanaccess_jars)

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
    def _create_tables(conn):
        cursor = conn.cursor()
        statement = """CREATE TABLE "boards" (
                                "number"	INTEGER  PRIMARY KEY,
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
        statement = """CREATE TABLE "protocols" (
                                        "number"	INTEGER,
                                        "ns"	INTEGER,
                                        "ew"	INTEGER,
                                        "contract"	TEXT,
                                        "declarer"	TEXT,
                                        "lead"	TEXT,
                                        "result"  TEXT,
                                        "score"	INTEGER,
                                        "mp_ns" INTEGER,
                                        "mp_ew" INTEGER
                                    )"""
        cursor.execute(statement)
        statement = """CREATE TABLE "names" (
                                        "number"	INTEGER  PRIMARY KEY,
                                        "partnership"	TEXT
                                    )"""
        cursor.execute(statement)
        conn.commit()

    @staticmethod
    def create_tables():
        conn = TourneyDB.connect()
        TourneyDB._create_tables(conn)
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

    @staticmethod
    def to_access():
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        cursor.execute('select * from protocols')
        protocols = cursor.fetchall()
        players = max(max(p[1] for p in protocols), max(p[2] for p in protocols))
        ms_conn = jaydebeapi.connect(
            "net.ucanaccess.jdbc.UcanaccessDriver",
            f"jdbc:ucanaccess://{mdb_path};newDatabaseVersion=V2010",
            ["", ""],
            classpath
        )

        ms_cursor = ms_conn.cursor()
        ms_cursor.execute('select * from Data')
        ms_cursor.execute('delete from Data')
        for i, p in enumerate(protocols):
            number, ns, ew, contract, declarer, lead, result, score = p[:8]
            decl_num = ew if declarer in 'EW' else ns
            contract = contract.replace('XX', ' xx').replace('X', ' x')
            for new, old in zip(SUITS, SUITS_UNICODE):
                lead = lead.replace(old, new)
                contract = contract.replace(old, new)
            # The two numbers below have no meaning yet look consistent
            table = (ns - 1) // 2 + 1
            round_n = (ns + ew - 1) % (players - 1) + 1
            rows = f"({i + 1}, 1, {table}, {round_n}, {number}, {ns}, {ew}, {decl_num}, '{declarer}', '{contract}'," \
                   f"'{result}', '{lead}', {score}, 10000)"

            insert = f"INSERT INTO Data (ID, Section, Table, Round, Board, PairNS, PairEW, Declarer, [NS/EW], Contract, " \
                     f"Result, LeadCard, ScoreNS, ScoreEW) VALUES {rows};"
            ms_cursor.execute(insert)
        ms_conn.commit()
        ms_conn.close()
        conn.close()



if __name__ == "__main__":
    TourneyDB.to_access()



