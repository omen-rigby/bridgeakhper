import os
import psycopg2
import urllib.parse as up
import sqlite3
from constants import PLAYERS_DB

up.uses_netloc.append("postgres")


def migrate():
    url = up.urlparse(PLAYERS_DB)
    conn = psycopg2.connect(database=url.path[1:],
                            user=url.username,
                            password=url.password,
                            host=url.hostname,
                            port=url.port
                            )
    cursor = conn.cursor()
    statement = """CREATE TABLE "players" (
            "first_name"    CHAR(20),
            "last_name"    CHAR(20),
            "rank"  REAL,
            "gender"	CHAR,
            "full_name" CHAR(40),
            "rating"    SMALLINT,
            "rank_ru"	REAL  default 1.6
        )"""
    cursor.execute(statement)
    old_con = sqlite3.connect("players.db")
    old_cur = old_con.cursor()
    old_cur.execute("select * from players")
    old_data = old_cur.fetchall()
    old_con.close()

    for d in old_data:
        rows = f"('{d[0]}', '{d[1]}', {d[2] or 0}, '{d[3]}', '{d[4]}', {d[5]}, {d[6]})"
        insert = f"""INSERT INTO players (first_name, last_name, rank, gender, full_name, rating, rank_ru) VALUES {rows};"""
        cursor.execute(insert)
    conn.commit()


def get_players(columns="first_name,last_name,full_name,gender,rank,rank_ru"):
    if "DYNO" in os.environ:
        try:
            url = up.urlparse(PLAYERS_DB)
            conn = psycopg2.connect(database=url.path[1:],
                                    user=url.username,
                                    password=url.password,
                                    host=url.hostname,
                                    port=url.port
                                    )
            cursor = conn.cursor()
            cursor.execute(f"select {columns} from players")
            players = cursor.fetchall()
            conn.close()
            return [map(lambda x: x.strip() if type(x) == str else x, p) for p in players]
        except Exception:
            return []
    conn2 = sqlite3.connect(PLAYERS_DB)
    cursor2 = conn2.cursor()
    cursor2.execute(f"select {columns} from players")
    result = cursor2.fetchall()
    conn2.close()
    return result


if __name__ == "__main__":
    get_players()
