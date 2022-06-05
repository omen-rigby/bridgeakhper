import sqlite3
from constants import *
from bs4 import Comment
from copy import deepcopy
from util import levenshtein
from print import *
from deal import Deal

date = os.path.abspath(db_path).replace("\\", "/").split("/")[-2]
def escape_suits(string):
    for bad, good in zip(SUITS_UNICODE, SUITS):
        string = string.replace(bad, good)
    return string

class ResultGetter:
    _conn = None

    def __init__(self, boards, pairs):
        self.boards = boards
        self.pairs = pairs
        self.travellers = []
        self.totals = []
        self.personals = []
        self.names = []

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(db_path)
        return self._conn

    @property
    def cursor(self):
        return self.conn.cursor()

    @property
    def max_mp(self):
        return self.pairs - 2 + self.pairs % 2

    @staticmethod
    def lookup(raw_pair, players):
        players = [p for p in players if any(p)]
        partners = re.split("[^\w\s]", raw_pair, 1)
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
            candidate = [p for p in players if levenshtein(partner, p[2]) <= 2]
            if candidate:
                candidates.append(candidate[0])
                continue
            # First and last name partial match
            candidate = [p for p in players if levenshtein(partner.split(" ")[-1], p[1]) <= 2]
            if candidate:
                candidates.append(candidate[0])
                continue
            candidate = [p for p in players if levenshtein(partner.split(" ")[0], p[0]) <= 2]
            if candidate:
                candidates.append(candidate[0])
                continue
            candidates.append(partner)
        if len(set(map(lambda p: p[3], candidates))) == 2:
            candidates.sort(key=lambda p: p[3])
        else:
            candidates.sort(key=lambda p: players.index(p))
        return [c[2] for c in candidates]

    def get_names(self):
        cur = self.cursor
        cur.execute("select * from names order by number")
        raw = cur.fetchall()
        conn2 = sqlite3.connect("players.db")
        cursor2 = conn2.cursor()
        cursor2.execute("select first_name,last_name,full_name,gender from players")
        players = cursor2.fetchall()
        for raw_pair in raw:
            self.names.append(self.lookup(raw_pair[1], players))
        conn2.close()
        self._conn = self.conn.close()

    def get_hands(self):
        self.hands = []
        cur = self.cursor
        cur.execute(f"select * from boards")
        self.hands = cur.fetchall()

    def get_results(self):
        max_mp = self.max_mp
        cur = self.cursor
        self.travellers = []
        for board in range(1, self.boards + 1):
            cur.execute(f"select * from protocols where number={board}")
            filtered = {}
            for protocol in cur.fetchall():
                filtered[f"{protocol[0]}{protocol[1]}"] = protocol
            print(filtered)
            if len(filtered) != self.pairs // 2:
                print(f"Missing results for board #{board}")
            sorted_results = list(filtered.values())
            sorted_results.sort(key=lambda x: x[7])
            scores = [s[7] for s in sorted_results]
            current = 0
            cluster_index = 0
            for s in sorted_results:
                repeats = scores.count(s[7])
                mp_ns = current + (repeats - 1)
                if cluster_index == repeats - 1:
                    current += 2 * repeats
                else:
                    cluster_index += 1
                mp_ew = max_mp - mp_ns
                statement = f"update protocols set mp_ns={mp_ns}, mp_ew={mp_ew} where number={board} and ns={s[1]}"
                cur.execute(statement)
            self.travellers.append([[s[1], s[2], escape_suits(s[3] + s[6]), s[4], escape_suits(s[5]), s[7] if s[7] >= 0 else "",
                                    -s[7] if s[7] <= 0 else "", s[8], s[9]] for s in sorted_results])
        self.conn.commit()

    def get_standings(self):
        max_mp = self.pairs - 2
        cur = self.cursor
        for pair in range(1, self.pairs + 1):
            cur.execute(f"select * from protocols where ns={pair} or ew={pair} order by number")
            history = cur.fetchall()
            self.totals.append(
                (pair, sum(record[-2] if pair == record[0] else record[-1] for record in history))
            )
            vul = {'-': "-", "n": "NS", "e": "EW", "b": "ALL"}
            self.personals.append([[board[0], vul[VULNERABILITY[board[0]]], "NS" if pair == board[1] else "EW",
                                    escape_suits(board[3] + board[6]), board[4], escape_suits(board[5]),
                                    board[7] * (-1) ** (pair == board[1]),
                                    board[8 + (pair != board[1])], round(board[8 + (pair != board[1])] * 100 / max_mp),
                                    board[1 + (pair == board[1])]]
                             for board in history])
        self.totals.sort(key=lambda x: -x[1])

    @staticmethod
    def _replace(string, dikt):
        for k, v in dikt.items():
            if "{" not in string:
                return string
            string = string.replace("${" + k + "}", " & ".join(v) if type(v) == list else str(v))

        return string

    def pdf_rankings(self):
        html = BeautifulSoup(open("rankings_template.html"), features="lxml")
        template = html.find_all("tr")[1].extract()
        for text in html.h1.find_all(text=re.compile('\$\{[^\}]+\}')):
            fixed_text = self._replace(text, {"tournament_title": "Koghbatsi Sunday",
                                              "date": date})
            text.replace_with(fixed_text)
        for text in html.h2.find_all(text=re.compile('\$\{[^\}]+\}')):
            fixed_text = self._replace(text, {"tables": self.pairs // 2, "boards": self.boards,
                                              "max": self.max_mp * self.boards})
            text.replace_with(fixed_text)
        for i, rank in enumerate(self.totals):
            new_tr = deepcopy(template)
            repl_dict = {"rank": i + 1, "pair": rank[0], "names": self.names[int(rank[0]) - 1],
                         "mp": rank[1], "percent": round(100 * rank[1]/self.boards/self.max_mp)
                         }
            for text in new_tr.find_all(text=re.compile('\$\{[^\}]+\}')):
                new_text = self._replace(text.string, repl_dict)
                text.string.replace_with(new_text)

            html.tbody.append(new_tr)
        print_to_pdf(html, f"{date}/Ranks.pdf")

    def pdf_travellers(self):
        file = open("travellers_template.html").read()
        html = BeautifulSoup(file, features="lxml")
        html.table.tr.extract()
        html.table.tr.extract()
        for board_number in range(1, self.boards + 1):
            soup_copy = BeautifulSoup(file, features="lxml")
            new_tr = soup_copy.table.tr
            for c in new_tr.find_all(text=lambda t: isinstance(t, Comment)):
                c.extract()
            hand = self.hands[board_number - 1]
            res = self.travellers[board_number - 1]
            deal = Deal(raw_hands=hand)
            repl_dict = {"d": deal.data["d"].upper(), "b": board_number,
                         "v": deal.data["v"],
                         }
            # Dealer and vul improvements
            for i, h in enumerate(hands):
                for j, s in enumerate(SUITS):
                    repl_dict[f"{h}{s}"] = deal.data[f"{h}{s}"].upper().replace("T", "10")
                for j,d in enumerate(DENOMINATIONS):
                    repl_dict[f"{h}_par_{d}"] = deal.data[f"{h}_par_{d}"]

            # TODO: add minimax
            # repl_dict["minimax"] = deal.
            # repl_dict["minimax_url"] = deal.
            tables = new_tr.find_all("table")
            # VUL in boards
            colors_dict = {"nscolor": "palegreen" if deal.data["v"] in ("EW", "-") else "tomato",
                           "ewcolor": "palegreen" if deal.data["v"] in ("NS", "-") else "tomato"}
            for td in tables[0].find_all("td"):
                if "color}" in td.get("bgcolor", ""):
                    td["bgcolor"] = colors_dict[td["bgcolor"].split("{")[1].strip("}")]
            dealer_tag = [f for f in tables[0].find_all('font') if f.string == repl_dict["d"]][0]
            dealer_tag['style'] = 'text-decoration:underline;'
            for table in tables:
                for text in table.find_all(text=re.compile('\$\{[^\}]+\}')):
                    new_text = self._replace(text.string, repl_dict)
                    text.string.replace_with(new_text)
            html.tbody.append(new_tr)
            new_tr = soup_copy.table.tr
            new_parent = soup_copy.table.table
            template = new_parent.find_all('tr')[1].extract()
            for r in res:
                protocol_table = deepcopy(template)
                repl_dict = {k: str(v).upper() for k, v in zip(
                    ("ns", "ew", "contract", "declarer", "lead", "ns+", "ns-", "mp_ns", "mp_ew"), r)}
                repl_dict["ns_name"] = self.names[r[0] - 1]
                repl_dict["ew_name"] = self.names[r[1] - 1]
                bbo_url = deal.url_with_contract(r[2][0], r[2][1:], r[3])
                for text in protocol_table.find_all(text=re.compile('\$\{[^\}]+\}')):
                    new_text = self._replace(text.string, repl_dict)
                    text.string.replace_with(new_text)
                protocol_table.a["href"] = bbo_url
                new_parent.tbody.append(protocol_table)
            html.tbody.append(new_tr)
        print_to_pdf(html, f"{date}/Travellers.pdf")

    def pdf_scorecards(self):
        file = open("scorecards_template.html").read()
        html = BeautifulSoup(file, features="lxml")
        for tr in html.find_all("tr"):
            tr.extract()

        boards_per_round = [p[-1] for p in self.personals[0]].count(self.personals[0][0][-1])

        num_of_rounds = self.boards // boards_per_round
        totals = self.totals
        for pair_number, results in enumerate(self.personals):
            pair_rank = [t for t in totals if t[0] == pair_number + 1][0]
            new_trs = BeautifulSoup(file, features="lxml").table.find_all("tr")
            new_trs[0].th.string = self._replace(new_trs[0].th.string,
                                                 {"name": self.names[pair_number], "pair": pair_number + 1})
            html.tbody.append(new_trs[0])
            for text in new_trs[1].find_all(text=re.compile('\$\{[^\}]+\}')):
                fixed_text = self._replace(text, {"mp_total": pair_rank[1], "max_mp": self.max_mp * self.boards,
                                                  "percent_total": round(100 * pair_rank[1] / self.max_mp / self.boards),
                                                  "rank": totals.index(pair_rank) + 1})
                text.replace_with(fixed_text)
            html.tbody.append(new_trs[1])
            html.tbody.append(new_trs[2])

            for r in range(num_of_rounds):
                new_trs[3].extract()
                mp_for_round = sum(results[r * boards_per_round + b][7] for b in range(boards_per_round))
                for i in range(boards_per_round):
                    board_data = results[r * boards_per_round + i]

                    board_tr = BeautifulSoup(file, features="lxml").table.find_all("tr")[3]
                    if i:
                        for last_col in board_tr.find_all("td")[-1:-3:-1]:
                            last_col.extract()
                    else:
                        for td in board_tr.find_all("td"):
                            if "boards_per_round}" in td.get("rowspan", ""):
                                td["rowspan"] = boards_per_round
                    def suits(string):

                        for s in ["spade", "heart", "diamond", "club"]:
                            if s in string:
                                string = string.replace(s[0], f'<img src="../{s}.gif"/>')
                                break
                        string = string.replace("n", "NT")
                        return string.upper()
                    for text in board_tr.find_all(text=re.compile('\$\{[^\}]+\}')):
                        fixed_text = self._replace(text,
                                                   {"board_number": board_data[0], "vul": board_data[1],
                                                    "dir": board_data[2], "contract": suits(board_data[3]),
                                                    "declarer": board_data[4].upper(), "lead": suits(board_data[5]),
                                                    "score": board_data[6], "mp": board_data[7],
                                                    "percent": board_data[8],
                                                    "mp_per_round": mp_for_round,
                                                    "opp_names": self.names[board_data[-1] - 1]})
                        text.replace_with(fixed_text)

                    html.tbody.append(board_tr)
        print_to_pdf(html, f"{date}/Scorecards.pdf")


if __name__ == "__main__":
    r = ResultGetter(10, 6)
    r.get_names()
    r.get_hands()
    r.get_results()
    r.get_standings()
    r.pdf_rankings()
    r.pdf_travellers()
    r.pdf_scorecards()
    r.conn.close()
