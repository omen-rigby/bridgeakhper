import psycopg2
import urllib.parse as up
import sqlite3
import re
try:
    from util import levenshtein
    from constants import PLAYERS_DB
except ImportError:
    from .util import levenshtein
    from .constants import PLAYERS_DB

up.uses_netloc.append("postgres")


class Players:
    @staticmethod
    def connect():
        url = up.urlparse(PLAYERS_DB)
        return psycopg2.connect(database=url.path[1:],
                                user=url.username,
                                password=url.password,
                                host=url.hostname,
                                port=url.port
                                )

    @staticmethod
    def migrate():
        conn = Players.connect()
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
        conn.close()

    @staticmethod
    def get_players(columns="first_name,last_name,full_name,gender,rank,rank_ru"):
        if "postgres" in PLAYERS_DB:
            try:
                conn = Players.connect()
                cursor = conn.cursor()
                cursor.execute(f"select {columns} from players")
                players = cursor.fetchall()
                conn.close()
                return [list(map(lambda x: x.strip() if type(x) == str else x, p)) for p in players]
            except Exception:
                return []
        conn2 = sqlite3.connect(PLAYERS_DB)
        cursor2 = conn2.cursor()
        cursor2.execute(f"select {columns} from players")
        result = cursor2.fetchall()
        conn2.close()
        return result

    @staticmethod
    def add_new_player(first, last, gender, rank, rank_ru):
        conn = Players.connect()
        cursor = conn.cursor()
        full = f"{first} {last}"
        insert = f"""INSERT INTO players (first_name, last_name, rank, gender, full_name, rating, rank_ru) 
                     VALUES ('{first}', '{last}', {rank}, '{gender}', '{full}', 0, {rank_ru});"""
        cursor.execute(insert)
        conn.commit()
        conn.close()

    @staticmethod
    def update(last_name, rank=None, rank_ru=None):
        conn = Players.connect()
        cursor = conn.cursor()
        changes_dict = {"rank": rank, "rank_ru": rank_ru}
        changes = ",".join([f"{k}={v}" for k,v in changes_dict.items() if v is not None])
        cursor.execute(f"UPDATE players set {changes} WHERE last_name='{last_name}'")
        conn.commit()
        conn.close()

    @staticmethod
    def remove(last_name):
        conn = Players.connect()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM players WHERE last_name='{last_name}'")
        conn.commit()
        conn.close()

    @staticmethod
    def lookup(raw_pair, players):
        players = [p for p in players if any(p)]
        partners = re.split("[^\w\s]", raw_pair, 2)
        if len(partners) < 2:
            partners = raw_pair.split("  ")
            if len(partners) < 2:
                chunks = raw_pair.split(" ")
                partners = [" ".join(chunks[:2]), " ".join(chunks[2:])]
        partners = [p.strip().replace("ё", "е") for p in partners]
        candidates = []
        for partner in partners:
            candidate = [p for p in players if p[2] == partner]
            if candidate:
                candidates.append(candidate[0])
                continue
            # Full name partial match
            candidate = [p for p in players if levenshtein(partner, p[2]) <= 1]
            if candidate:
                candidates.append(candidate[0])
                continue
            # Last and first name partial match
            candidate = [p for p in players if levenshtein(partner.split(" ")[-1], p[1]) <= 1]
            if candidate:
                candidates.append(candidate[0])
                continue
            # If a player has only first name, find
            candidate = [p for p in players if levenshtein(partner, p[0]) <= 2]
            if candidate:
                candidates.append(candidate[0])
                continue
            # Otherwise, use name as given
            candidates.append(partner)
        if len(set(map(lambda p: p[3], candidates))) == 2:
            candidates.sort(key=lambda p: p[3])
        else:
            candidates.sort(key=lambda p: players.index(p))
        return [(c[2], c[4] or 0, c[5]) if type(c) != str else (c, 0, 1.6) for c in candidates]


if __name__ == "__main__":
    Players.add_new_player("Ваче", "Минасян", "M", 6, 1.6)
    print(Players.get_players())
