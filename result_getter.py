from constants import *
from players import Players
from math import log10, ceil
from copy import deepcopy
from util import escape_suits
from print import *
from deal import Deal
from imps import imps
from statistics import mean
from tourney_db import TourneyDB
from constants import date

ALL_PLAYERS = Players.get_players()


class ResultGetter:
    _conn = None
    _deals = None

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
            self._conn = TourneyDB.connect()
        return self._conn

    @property
    def cursor(self):
        return self.conn.cursor()

    @property
    def max_mp(self):
        return self.pairs - 2 - self.pairs % 2

    @property
    def deals(self):
        if not self._deals:
            self._deals = [Deal(raw_hands=h) for h in self.hands]
        return self._deals

    def get_names(self):
        cur = self.cursor
        cur.execute("select * from names order by number")
        raw = cur.fetchall()
        try:
            players = Players.get_players()
            for raw_pair in raw:
                self.names.append(Players.lookup(raw_pair[1], players))
        except:
            for raw_pair in raw:
                self.names.append((raw_pair[1].split(" "), 0, 1.6))
        if not raw:
            self.names = [(f"{i}_1", f"{i}_2") for i in range(1, self.pairs + 1)]
        self._conn = self.conn.close()

    def get_hands(self):
        self.hands = []
        cur = self.cursor
        cur.execute(f"select distinct * from boards order by number")
        # board #0 can be erroneously submitted
        self.hands = [h for h in cur.fetchall() if h[0]]

    def set_scores_ximp(self, board, scores, adjusted_scores):
        for s in adjusted_scores:
            mp_ns = 0 if s[3] == 'A' else 3 * (-1) ** ('A-' == s[3]) * (len(scores) - 1)
            mp_ew = -mp_ns
            s[8] = mp_ns
            s[9] = mp_ew
            statement = f"update protocols set mp_ns={mp_ns}, mp_ew={mp_ew} where number={board} and ns={s[1]}"
            self.cursor.execute(statement)
        for s in scores:
            mp_ns = sum(imps(s[7] - other[7]) for other in scores)
            mp_ew = -mp_ns
            statement = f"update protocols set mp_ns={mp_ns}, mp_ew={mp_ew} where number={board} and ns={s[1]}"
            s[8] = mp_ns
            s[9] = mp_ew
            self.cursor.execute(statement)
        return scores

    def set_scores_imp(self, board, scores, adjusted_scores):
        for s in adjusted_scores:
            mp_ns = 0 if s[3] == 'A' else 3 * (-1) ** ('A-' == s[3])
            mp_ew = -mp_ns
            s[8] = mp_ns
            s[9] = mp_ew
            statement = f"update protocols set mp_ns={mp_ns}, mp_ew={mp_ew} where number={board} and ns={s[1]}"
            self.cursor.execute(statement)
        results_mean = mean(s[7] for s in scores)
        # datums ending in 5 are rounded towards the even number of tens
        # to make mean rounding error for a whole area tend to 0
        if results_mean % 20 == 5:
            datum = round(results_mean, -1) - 10
        else:
            datum = round(results_mean, -1)
        for s in scores:
            mp_ns = imps(s[7] - datum)
            mp_ew = -mp_ns
            statement = f"update protocols set mp_ns={mp_ns}, mp_ew={mp_ew} where number={board} and ns={s[1]}"
            s[8] = mp_ns
            s[9] = mp_ew
            self.cursor.execute(statement)
        return scores

    def set_scores_mp(self, board, scores, adjusted_scores):
        for s in adjusted_scores:
            mp_ns = round(self.max_mp / 100 * int(s[3].split("/")[0]), 1)
            mp_ew = self.max_mp - mp_ns
            s[8] = mp_ns
            s[9] = mp_ew
            statement = f"update protocols set mp_ns={mp_ns}, mp_ew={mp_ew} where number={board} and ns={s[1]}"
            self.cursor.execute(statement)
        scores.sort(key=lambda x: x[7])
        current = 0
        cluster_index = 0
        scores = [list(s) for s in scores]
        for s in scores:
            repeats = [s2[7] for s2 in scores].count(s[7])
            if adjusted_scores and CONFIG["neuberg"]:
                mp_ew = (self.max_mp - 2 * len(adjusted_scores) - current - (repeats - 1) + 1) \
                        * (len(scores) + len(adjusted_scores)) / len(scores) - 1
                mp_ns = self.max_mp - mp_ew
            else:
                mp_ns = current + (repeats - 1)
                mp_ew = self.max_mp - mp_ns
            if cluster_index == repeats - 1:
                current += 2 * repeats
                cluster_index = 0
            else:
                cluster_index += 1
            statement = f"update protocols set mp_ns={mp_ns}, mp_ew={mp_ew} where number={board} and ns={s[1]}"
            s[8] = mp_ns
            s[9] = mp_ew
            self.cursor.execute(statement)
        return scores

    def get_results(self):
        """
        For adjustments refer to
        http://db.eurobridge.org/repository/departments/directing/2001Course/LecureNotes/Score%20Adjustments1.pdf
        """
        cur = self.cursor
        self.travellers = []
        for board in range(1, self.boards + 1):
            cur.execute(f"select * from protocols where number={board}")
            filtered = {}
            for protocol in cur.fetchall():
                unique_id = protocol[1] * (self.pairs + 1) + protocol[2]
                filtered[f"{unique_id}"] = protocol
            if len(filtered) != self.pairs // 2:
                print(f"Missing results for board #{board}")
            sorted_results = [list(f) for f in filtered.values()]
            adjusted_scores = [s for s in sorted_results if s[7] == 1]
            scores = [s for s in sorted_results if s[7] != 1]
            scoring_method = {
                "MPs": self.set_scores_mp,
                "IMPs": self.set_scores_imp,
                "Cross-IMPs": self.set_scores_ximp
            }[CONFIG["scoring"]]
            scores = scoring_method(board, scores, adjusted_scores)
            # TODO: change 60/40 to session average
            self.travellers.append([[s[1], s[2], escape_suits(s[3] + s[6]), s[4], escape_suits(s[5]), s[7] if s[7] >= 0 else "",
                                    -s[7] if s[7] <= 0 else "", round(s[8], 2), round(s[9], 2)] for s in scores + adjusted_scores])
        self.conn.commit()

    def get_standings(self):
        max_mp = self.pairs - 2 - self.pairs % 2
        cur = self.cursor
        for pair in range(1, self.pairs + 1):
            cur.execute(f"select * from protocols where (ns={pair} or ew={pair}) and number > 0 order by number")
            # records are duplicated sometimes
            history = list(set(cur.fetchall()))
            result_in_mp = sum(record[-2] if pair == record[1] else record[-1] for record in history)
            self.totals.append([pair, result_in_mp])

            vul = {'-': "-", "n": "NS", "e": "EW", "b": "ALL"}
            self.personals.append([])
            for i in range(1, self.boards + 1):
                try:
                    board = [b for b in history if b[0] == i][0]
                except IndexError:
                    # ADDING NOT PLAYED
                    self.personals[-1].append([i, vul[VULNERABILITY[i % 16]], "-",
                                               "NOT PLAYED", "", "",
                                               0,
                                               0, 0, 0])
                    continue

                if pair == board[1]:
                    position = "NS"
                elif pair == board[2]:
                    position = "EW"

                self.personals[-1].append([board[0], vul[VULNERABILITY[board[0] % 16]], position,
                                          escape_suits(board[3] + board[6]), board[4], escape_suits(board[5]),
                                          board[7] * (-1) ** (pair != board[1]),
                                          board[8 + (pair != board[1])],
                                          round(board[8 + (pair != board[1])] * 100 / max_mp, 2),
                                          board[1 + (pair == board[1])]])
        self.totals.sort(key=lambda x: -x[1])
        self.get_masterpoints()

    def get_masterpoints(self):
        # AM
        # 52 is the number of cards in a board (sic!)
        total_rating = sum(sum(a[1] for a in p) / len(p) * 2 for p in self.names)
        n = self.pairs
        d = self.boards
        played_boards = max(len([p for p in personal if p[3] != "NOT PLAYED"]) for personal in self.personals)
        max_mp = self.max_mp * played_boards
        b0 = total_rating * played_boards / 52 * CONFIG["tourney_coeff"]
        mps = [b0]
        for i in range(2, n):
            mps.append(b0 / (1 + i/(n - i)) ** (i - 1))
        mps.append(0)
        cluster_index = 0
        for i in range(self.pairs):
            cluster_first = i - cluster_index
            if cluster_first + 1 > round(0.4 * self.pairs) or self.totals[i][1] < max_mp / 2:
                self.totals[i].append(0)
                continue
            cluster_length = len([a for a in self.totals if a[1] == self.totals[i][1]])
            cluster_total = sum(mps[j] for j, a in enumerate(self.totals) if a[1] == self.totals[i][1])\
                / cluster_length
            if i + 1 < len(self.totals) and self.totals[i + 1][1] == self.totals[i][1]:
                cluster_index += 1
            else:
                cluster_index = 0
            # Ask Artem for the reasoning behind this
            if cluster_first + cluster_length > round(0.4 * self.pairs):
                rounding_method = ceil
            elif i < 2:
                rounding_method = round
            else:
                rounding_method = int
            self.totals[i].append(rounding_method(cluster_total))
        # RU
        # this dragon poker rules are taken from https://www.bridgesport.ru/materials/sports-classification/
        ranks_ru = [sum(a[2] for a in p) / len(p) for p in self.names]
        team = "team" in CONFIG["scoring"].lower()
        n0 = n * (1 + team)  # number of pairs for team events also
        kp = 0.9 if team else 0.95
        typ = 2 - team
        q1 = list(sorted((0.2 - 0.12 * r if r < 0 else 0.2 / (1.6 ** r) for r in ranks_ru), key=lambda x: -x))
        q2 = [q * kp ** i for i, q in enumerate(q1)]
        last = 16 if type == 2 else 32
        kq = sum(q2[:last]) / 2 ** (typ - 1)
        kq1 = 1 if kq >= 1 else 1 - 0.7 * log10(kq)
        kqn = 0.6 * (kq + log10(n0) - 1.5) * kq1 if n0 >= 32 else 0.4 * kq * log10(n0) * kq1
        kd = 2.2 * log10(d) - 2
        t = n / 8 * max(0.5, 3 + kq - 0.5 * log10(n))
        r = 1.1 * (100 * kd * kqn) ** (1 / t)
        mps = [50 * kqn * kd / r ** i for i in range(self.pairs)]
        try:
            for i, t in enumerate(self.totals):
                cluster_length = len([a for a in self.totals if a[1] == self.totals[i][1]])
                tied_mps = [mps[j] for j, a in enumerate(self.totals) if a[1] == self.totals[i][1]]
                cluster_total = sum(tied_mps) / cluster_length
                t.append(1 if min(tied_mps) < 0.5 and max(map(round, tied_mps)) > 0 and cluster_total < 0.5 else round(cluster_total))
            # remove extra stuff from names
        except:
            for i, t in enumerate(self.totals):
                t.append(0)
        self.names = [[n[0] for n in p] for p in self.names]

    @staticmethod
    def _replace(string, dikt):
        minus = '−'
        for k, v in dikt.items():
            if "{" not in string:
                return string

            string = string.replace("${" + k + "}", " & ".join(v) if type(v) == list else str(v).replace("-", minus))
        return string

    def pdf_rankings(self):
        max_mp = self.max_mp * len([p for p in self.personals[0] if p[3] != "NOT PLAYED"])
        html = BeautifulSoup(open("templates/rankings_template.html"), features="lxml")
        template = html.find_all("tr")[1].extract()
        if CONFIG["scoring"] != 'MPs':
            html.find_all("th")[-1].extract()
            template.find_all("td")[-1].extract()
            scoring = CONFIG["scoring"]
            header_text = html.find(text=re.compile("MAX = \$\{max\}"))
            header_text.replace_with(header_text.replace("MAX = ${max}", f"Scoring: {scoring}"))
        for text in html.h1.find_all(text=re.compile('\$\{[^\}]+\}')):
            fixed_text = self._replace(text, {"tournament_title": CONFIG["tournament_title"],
                                              "date": date})
            text.replace_with(fixed_text)
        for text in html.h2.find_all(text=re.compile('\$\{[^\}]+\}')):
            fixed_text = self._replace(text, {"tables": self.pairs // 2, "boards": self.boards,
                                              "max": max_mp})
            text.replace_with(fixed_text)
        for i, rank in enumerate(self.totals):
            new_tr = deepcopy(template)
            cluster = [i for i, r in enumerate(self.totals) if r[1] == rank[1]]
            repl_dict = {
                "rank": i + 1 if len(cluster) == 1 else f"{cluster[0] + 1}-{cluster[-1] + 1}", "pair": rank[0],
                "names": self.names[int(rank[0]) - 1], "mp": round(rank[1], 2),
                "percent": round(100 * rank[1]/max_mp, 2),
                "masterpoints": rank[2] or "",
                "masterpoints_ru": rank[3] or ""
            }
            for text in new_tr.find_all(text=re.compile('\$\{[^\}]+\}')):
                new_text = self._replace(text.string, repl_dict)
                text.string.replace_with(new_text)

            html.tbody.append(new_tr)
        return print_to_pdf(html, "Ranks.pdf")

    def pdf_travellers(self, boards_only=False):
        file = open("templates/travellers_template.html").read()
        html = BeautifulSoup(file, features="lxml")
        html.table.tr.extract()
        html.table.tr.extract()
        for board_number in range(1, self.boards + 1):
            soup_copy = BeautifulSoup(file, features="lxml")
            new_tr = soup_copy.table.tr
            deal = self.deals[board_number - 1]
            if not boards_only:
                res = self.travellers[board_number - 1]
            repl_dict = {"d": deal.data["d"].upper(), "b": board_number,
                         "v": deal.data["v"],
                         }
            # Dealer and vul improvements
            for i, h in enumerate(hands):
                for j, s in enumerate(SUITS):
                    repl_dict[f"{h}{s}"] = deal.data[f"{h}{s}"].upper().replace("T", "10")
                for j,d in enumerate(DENOMINATIONS):
                    repl_dict[f"{h}_par_{d}"] = deal.data[f"{h}_par_{d}"]
            for key in ('level', 'denomination', 'declarer', 'score', 'minimax_url', 'result'):
                repl_dict[key] = deal.data[key]
            if repl_dict['denomination'] == "n":
                repl_dict['denomination'] = "NT"
            else:
                repl_dict['denomination'] = repl_dict['denomination'].upper()
            # VUL in boards
            table = new_tr.find('table')
            cols = [c for c in table.find_all('td') if type(c) != str and 'nonvul' in c.attrs.get('class', [])]
            for i, col in enumerate(cols):
                classes = col.attrs.get("class", [])
                if not classes:
                    continue
                if i % 3 and deal.data["v"] in ("EW", "ALL"):
                    classes.remove('nonvul')
                    classes.append("vul")
                if not i % 3 and deal.data["v"] in ("NS", "ALL"):
                    col["class"].remove('nonvul')
                    col["class"].append("vul")
            # TODO: this crazy stuff is sick and should somehow be replaced with real html aligning
            # yet as for now I have no idea how to implement it
            if board_number > 9:
                cols[0]["style"] = "padding-left: 8px;"
                cols[-1]["style"] = "padding-left: 8px;"
            else:
                number = [c for c in table.find_all('td') if type(c) != str and 'digits' in c.attrs.get('class', [])][0]
                number['style'] = "padding-left: 2px"
            dealer_tag = new_tr.find_all('font')["NWXES".index(repl_dict["d"])]
            dealer_tag['class'] = 'dealer'
            for text in new_tr.find_all(text=re.compile('\$\{[^\}]+\}')):
                new_text = self._replace(text.string, repl_dict)
                text.string.replace_with(new_text)
            new_tr.find("a", class_="minimax_url")["href"] = deal.data["minimax_url"]
            html.tbody.append(new_tr)
            new_tr = soup_copy.table.tr
            new_parent = soup_copy.table.table
            scoring_short = CONFIG["scoring"].rstrip("s").replace("Cross-", "X")
            for text in new_parent.tbody.find_all(text=re.compile('\$\{scoring_short\}')):
                text.replace_with(scoring_short)

            template = new_parent.find_all('tr')[1].extract()
            if boards_only:
                continue
            for r in res:
                protocol_table = deepcopy(template)
                repl_dict = {k: str(v).upper() for k, v in zip(
                    ("ns", "ew", "contract", "declarer", "lead", "ns+", "ns-", ), r)}
                repl_dict["mp_ns"] = round(r[7], 2)
                repl_dict["mp_ew"] = round(r[8], 2)
                repl_dict["ns_name"] = self.names[r[0] - 1]
                repl_dict["ew_name"] = self.names[r[1] - 1]
                bbo_url = deal.url_with_contract(r[2][0], r[2].split("=")[0].split("+")[0].split("-")[0][1:], r[3])
                for text in protocol_table.find_all(text=re.compile('\$\{[^\}]+\}')):
                    new_text = self._replace(text.string, repl_dict)
                    text.string.replace_with(new_text)
                protocol_table.a["href"] = bbo_url
                new_parent.tbody.append(protocol_table)
            html.tbody.append(new_tr)
        out_filename = 'Boards' if boards_only else 'Travellers'

        return print_to_pdf(html, f"{out_filename}.pdf")

    def pdf_scorecards(self):
        file = open("templates/scorecards_template.html").read()
        html = BeautifulSoup(file, features="lxml")
        html.div.extract()
        scoring_short = CONFIG["scoring"].rstrip("s").replace("Cross-", "X")
        boards_per_round = [p[-1] for p in self.personals[0]].count(self.personals[0][0][-1])

        num_of_rounds = self.boards // boards_per_round
        totals = self.totals
        max_mp = self.max_mp * len([p for p in self.personals[0] if p[3] != "NOT PLAYED"])

        for pair_number, results in enumerate(self.personals):
            new_div = BeautifulSoup(file, features='lxml').div
            pair_rank = [t for t in totals if t[0] == pair_number + 1][0]
            new_trs = new_div.table.find_all("tr")
            new_trs[0].th.string = self._replace(new_trs[0].th.string,
                                                 {"name": self.names[pair_number], "pair": pair_number + 1})
            # One per page
            if CONFIG["scoring"] != "MPs":
                new_trs[0].find("th")["colspan"] = 9
                new_trs[1].find("th")["colspan"] = 9
            for text in new_trs[1].find_all(text=re.compile('\$\{[^\}]+\}')):
                if CONFIG["scoring"] != "MPs":
                    fixed_text = text.replace("MaxMPs ${max_mp} Score ${percent_total}% ", "")
                else:
                    fixed_text = text
                fixed_text = self._replace(fixed_text, {"mp_total": round(pair_rank[1], 2), "max_mp": max_mp,
                                                        "percent_total": round(100 * pair_rank[1] / max_mp, 2),
                                                        "rank": totals.index(pair_rank) + 1,
                                                        "scoring_short": scoring_short})
                text.replace_with(fixed_text)
            for text in new_trs[2].find_all(text=re.compile('\$\{[^\}]+\}')):
                fixed_text = self._replace(text, {"scoring_short": scoring_short})
                text.replace_with(fixed_text)

            if CONFIG["scoring"] != "MPs":
                new_trs[2].find_all("th")[7].extract()
            new_trs[3].extract()

            for r in range(num_of_rounds):
                mp_for_round = sum(results[r * boards_per_round + b][7] for b in range(boards_per_round))
                for i in range(boards_per_round):
                    board_data = results[r * boards_per_round + i]
                    deal = self.deals[r * boards_per_round + i]
                    suspicious_result = False
                    if board_data[3].lower() not in ("pass", "not played") and '/' not in board_data[3]:
                        level = board_data[3][0]
                        denomination = board_data[3][1].lower()
                        declarer = board_data[4]
                        dummy = hands[(hands.index(declarer) + 2) % 4]
                        result = board_data[3][-2:].lstrip("sdhcnx")
                        tricks = int(level) + 6 if result == "=" else eval(f'{level}{result}') + 6
                        par = deal.data[f"{declarer}_par_{denomination}"]
                        if denomination != "n":
                            fit = len(deal.data.get(f"{declarer}{denomination}")) + \
                                len(deal.data.get(f"{dummy}{denomination}"))
                        else:
                            fit = 13
                        if (abs(tricks - par) > 3 and denomination == "n") or (abs(tricks - par) >= 3 and fit < 7):
                            suspicious_result = True
                    board_tr = BeautifulSoup(file, features='lxml').div.table.find_all("tr")[3]
                    if CONFIG["scoring"] != "MPs":
                        board_tr.find_all("td")[7].extract()

                    if suspicious_result:
                        board_tr.find_all("td")[3]["bgcolor"] = "#aa7777"
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
                        if board_data[3] == "NOT PLAYED":
                            opp_names = ""
                        else:
                            opp_names = self.names[board_data[-1] - 1]
                        fixed_text = self._replace(text,
                                                   {"board_number": board_data[0], "vul": board_data[1],
                                                    "dir": board_data[2], "contract": suits(board_data[3]),
                                                    "declarer": board_data[4].upper(), "lead": suits(board_data[5]),
                                                    "score": board_data[6], "mp": round(board_data[7], 2),
                                                    "percent": round(board_data[8], 2),
                                                    "mp_per_round": round(mp_for_round, 2),
                                                    "opp_names": opp_names})
                        text.replace_with(fixed_text)
                    new_div.tbody.append(board_tr)
            if not pair_number:
                new_div["style"] = ""
            html.append(new_div)

        return print_to_pdf(html, "Scorecards.pdf", landscape=True)

    def boards_only(self):
        self.get_hands()
        return self.pdf_travellers(boards_only=True)

    def process(self):
        paths = []
        self.get_results()
        self.get_names()
        self.get_hands()
        self.get_standings()
        paths.append(self.pdf_rankings())
        paths.append(self.pdf_travellers())
        paths.append(self.pdf_scorecards())
        self.conn.close()
        return paths


if __name__ == "__main__":
    ResultGetter(27, 9).process()
