import psycopg2
import urllib.parse as up
import sqlite3
from constants import db_path

up.uses_netloc.append("postgres")


class TourneyDB:
    @staticmethod
    def connect():
        if db_path.startswith('postgres:'):
            url = up.urlparse(db_path)
            return psycopg2.connect(database=url.path[1:],
                                    user=url.username,
                                    password=url.password,
                                    host=url.hostname,
                                    port=url.port
                                    )
        else:
            return sqlite3.connect(db_path)

    @staticmethod
    def create_tables():
        conn = TourneyDB.connect()
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
        conn.close()

    @staticmethod
    def clear_tables():
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        for table in ('names', 'protocols', 'boards'):
            cursor.execute(f"delete from {table}")
        conn.commit()
        conn.close()


if __name__ == "__main__":
    TourneyDB.create_tables()

