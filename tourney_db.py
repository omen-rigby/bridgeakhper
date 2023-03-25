import psycopg2
import urllib.parse as up
import sqlite3
import os
import jaydebeapi
from constants import db_path, SUITS, SUITS_UNICODE
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

    @staticmethod
    def to_access():
        mdb_path = "templates/mdb.bws"
        ucanaccess_jars = [
            f'access_drivers/{path}' for path in ['ucanaccess-5.0.1.jar', 'lib/commons-lang3-3.8.1.jar',
                                                  'lib/commons-logging-1.2.jar', 'lib/hsqldb-2.5.0.jar',
                                                  'lib/jackcess-3.0.1.jar']]
        ms_conn = jaydebeapi.connect(
            "net.ucanaccess.jdbc.UcanaccessDriver",
            f"jdbc:ucanaccess://{mdb_path};newDatabaseVersion=V2010",
            ["", ""],
            ":".join(ucanaccess_jars)
        )
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        cursor.execute('select * from protocols')
        protocols = cursor.fetchall()
        players = max(max(p[1] for p in protocols), max(p[2] for p in protocols))
        ms_cursor = ms_conn.cursor()
        ms_cursor.execute('delete from ReceivedData')
        for i, p in enumerate(protocols):
            number, ns, ew, contract, declarer, lead, result, score = p[:8]
            decl_num = ew if declarer in 'EW' else ns
            contract = contract.upper().replace('XX', ' xx').replace('X', ' x')
            if contract[0].isdigit():
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
            rows = f"({i + 1}, 1, {table}, {round_n}, {number}, {ns + 900}, {ew + 900}, {decl_num + 900}, " \
                   f"'{declarer}', '{contract}', '{result}', '{lead}', '')"

            insert = f"INSERT INTO ReceivedData (ID, Section, Table, Round, Board, PairNS, PairEW, Declarer, [NS/EW]," \
                     f" Contract, Result, LeadCard, Remarks) VALUES {rows};"
            ms_cursor.execute(insert)
        ms_cursor.execute("select * from ReceivedData")
        ms_conn.commit()
        ms_conn.close()
        conn.close()
        return mdb_path


if __name__ == "__main__":
    TourneyDB.to_access()



