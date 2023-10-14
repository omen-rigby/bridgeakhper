import psycopg2
import urllib.parse as up
import sqlite3
import re
import time
import requests
from util import levenshtein
from constants import PLAYERS_DB, CONFIG
from lxml import etree

up.uses_netloc.append("postgres")
RU_DB = "https://db.bridgesport.ru/rate/fulllist/"


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
                city = CONFIG['city']
                cursor.execute(f"select {columns} from players where city='{city}' order by last_name")
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
        gender = "M" if gender.lower() in ("м", "муж", "m", "male") else "F"
        conn = Players.connect()
        cursor = conn.cursor()
        full = f"{first} {last}"
        res = requests.get(RU_DB)
        players = etree.fromstring(res.content)
        ru_id, message = Players.find_ru_id(first, last ,CONFIG["city"], players)
        insert = f"""INSERT INTO players (first_name, last_name, rank, gender, full_name, rating, rank_ru, city, id_ru) 
                     VALUES ('{first or ""}', '{last}', {rank}, '{gender}', '{full}', 0, {rank_ru}, '{CONFIG["city"]}',
                     {ru_id});"""
        cursor.execute(insert)
        conn.commit()
        conn.close()
        return message

    @staticmethod
    def update(last_name, rank=None, rank_ru=None, first_name=None):
        conn = Players.connect()
        cursor = conn.cursor()
        changes_dict = {"rank": rank, "rank_ru": rank_ru}
        changes = ",".join([f"{k}={v}" for k,v in changes_dict.items() if v is not None])
        cursor.execute(f"UPDATE players set {changes} WHERE last_name='{last_name}'"
                       + f"and first_name='{first_name}'" * (first_name is not None))
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
    def lookup(raw_pair, players, single=False):
        players = [p for p in players if any(p)]
        partners = re.split("[^\w\s]", raw_pair, 2)
        if len(partners) < 2 - single:
            partners = raw_pair.split("  ")
            if len(partners) < 2:
                chunks = raw_pair.split(" ")
                if len(chunks) == 2:
                    partners = chunks
                else:
                    partners = [" ".join(chunks[:2]), " ".join(chunks[2:])]
        partners = [p.strip().replace("ё", "е") for p in partners]
        candidates = []
        for partner in partners:
            name = partner.split(' ')[-1].replace('.', "")
            surname = partner.split(' ')[-1].replace('.', "")
            if len(surname) == 1 and not surname in (p[1] for p in players):
                initial = surname
                surname = partner.split(' ')[0]
                name = initial
                full_name = partner
            elif len(name) == 1 and not name in (p[1] for p in players):
                initial = name
                name = initial
                full_name = partner
            elif len(partner.split(' ')) == 2:
                name, surname = partner.split()
                initial = ""
                full_name = partner
            else:
                name = partner
                surname = partner
                initial = ""
                full_name = partner
            candidate = [p for p in players if p[2].lower() == full_name.lower() and p not in candidates]
            if candidate:
                candidates.append(candidate[0])
                continue
            # Full name partial match
            candidate = [p for p in players if levenshtein(full_name, p[2]) <= 1]
            candidate.sort(key=lambda p: levenshtein(partner, p[2]))
            if candidate:
                candidates.append(candidate[0])
                continue
            # Last and first name partial match
            candidate = [p for p in players if levenshtein(surname, p[1]) <= 1 and p not in candidates]
            candidate.sort(key=lambda p: levenshtein(partner.split(" ")[-1], p[1]))
            if candidate:
                if initial and len(candidates) > 1:
                    candidates.append([c for c in candidates if c[0][0] == initial])
                else:
                    candidates.append(candidate[0])
                continue
            # If a player has only first name, find
            if name == partner:
                candidate = [p for p in players if levenshtein(name, p[0]) <= 2 and p not in candidates]
                candidate.sort(key=lambda p: levenshtein(partner, p[0]))
                if candidate:
                    candidates.append(candidate[0])
                    continue
            # Otherwise, use name as given
            candidates.append(partner)
        if all(type(c) == tuple for c in candidates):
            if len(set(map(lambda p: p[3], candidates))) == 2:
                candidates.sort(key=lambda p: p[3])
            else:
                candidates.sort(key=lambda p: players.index(p))
        return [(c[2], c[4] or 0, c[5] if c[5] is not None else 5) if type(c) != str else (c, 0, 1.6) for c in candidates]

    @staticmethod
    def synch():
        res = requests.get(RU_DB)
        players = etree.fromstring(res.content)
        conn = Players.connect()
        cursor = conn.cursor()
        cursor.execute("select id_ru,rank_ru,full_name from players")
        digest = []
        for player_id, rank, full_name in cursor.fetchall():
            if not player_id:
                continue
            db_rank = players.find(f'.//player[@id="{player_id}"]').find('razr').text
            if float(db_rank) != rank:
                digest.append(f"{full_name} {rank} -> {db_rank}")
                cursor.execute(f"update players set rank_ru={db_rank} where id_ru={player_id}")
        conn.commit()
        conn.close()
        return "\n".join(digest)

    @staticmethod
    def find_ru_id(first, last, city, players):
        candidates = [p for p in players.findall(f'.//player') if p.find('.firstname').text == first.strip() and
                      p.find('.lastname').text == last.strip()]
        if not candidates:
            return 0, f"No people found in RU DB for criteria {first.strip()} {last.strip()}"
        if len(candidates) > 1:
            candidates = [c for c in candidates if c.find('city').text == city]
            if not candidates:
                return 0, f"No people found in RU DB for criteria {first.strip()} {last.strip()} {city}"
            if len(candidates) > 1:
                return 0, f"More than one person found for criteria {first.strip()} {last.strip()} {city}\n" + \
                    '\n'.join(f'https://www.bridgesport.ru/players-and-ratings/search-player/{c.get("id")}'
                                for c in candidates)
        ru_id = candidates[0].get('id')
        return ru_id, f'{first.strip()} {last.strip()} id is set to {ru_id}'

    @staticmethod
    def find_ru_ids():
        res = requests.get(RU_DB)
        players = etree.fromstring(res.content)
        conn = Players.connect()
        cursor = conn.cursor()
        cursor.execute("select first_name,last_name,city from players where id_ru is NULL")
        digest = []
        for first, last, city in cursor.fetchall():
            ru_id, message = Players.find_ru_id(first, last, city, players)
            digest.append(message)
            if ru_id:
                cursor.execute(f"update players set id_ru={ru_id} where first_name='{first}' and last_name='{last}'"
                               f" and city='{city}'")
        conn.commit()
        conn.close()
        return '\n'.join(digest)

    @staticmethod
    def synch_city(city):
        res = requests.get(RU_DB)
        players = etree.fromstring(res.content)
        city_players = [p for p in players.findall(f'.//player') if p.find('.city').text == city]
        conn = Players.connect()
        cursor = conn.cursor()
        for c in city_players:
            player_id = c.get('id')
            first = c.find('.firstname').text
            last = c.find('.lastname').text
            patronymic = c.find('.fathername').text
            rank = c.find('.razr').text
            if patronymic:
                gender = 'F' if patronymic.endswith('а') else 'M'
            else:
                # TODO: improve gender detection
                # This condition gives false females which is not really bad since all this data is used for sorting
                # player names within a partnership
                gender = 'F'
            cursor.execute(
                f"""insert into players (id_ru, first_name, last_name, full_name, rank_ru, "rank", gender, city) 
                    VALUES({player_id}, '{first}', '{last}', '{first} {last}', {rank}, 0, '{gender}', '{city}')""")
        conn.commit()
        conn.close()

    @staticmethod
    def monthly_report():
        current = time.localtime()
        month = current[1] if current[2] > 21 else (current[1] - 2) % 12 + 1
        year = current[0]
        conn = Players.connect()
        cursor = conn.cursor()
        cursor.execute('select full_name,id_ru from players where id_ru > 0')
        ru_players = {p[0].strip(): p[1] for p in cursor.fetchall()}
        cursor.execute(f'select tournament_id from tournaments where EXTRACT(MONTH FROM "date")={month} '
                       f'and EXTRACT(year FROM "date")={year}')
        tourneys = cursor.fetchall()
        mps = {}
        for tourney in tourneys:
            cursor.execute(f'select partnership, masterpoints_ru from names where tournament_id={tourney[0]} '
                           f'and masterpoints_ru > 0')
            pairs = cursor.fetchall()
            for pair in pairs:
                for name in pair[0].split(' & '):
                    if name in ru_players.keys():
                        mps[name] = mps.get(name, 0) + pair[1]
        return "ID\tName\tMPs\n" + "\n".join(f"{ru_players[k]}\t{k}\t{v}" for k,v in mps.items())


global ALL_PLAYERS
ALL_PLAYERS = Players.get_players() if PLAYERS_DB else []


if __name__ == "__main__":
    #print(Players.find_ru_ids())
    Players.synch_city("Воронеж")
