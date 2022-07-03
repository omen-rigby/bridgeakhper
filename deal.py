import sqlite3
from ddstable import ddstable
from constants import *

bbo_url_template = "https://www.bridgebase.com/tools/handviewer.html?n={n}&e={e}&s={s}&w={w}&d={d}&v={v}&b={b}&a=ppp"
board_template = open("board_template").read()
analysis_template = open("analysis_template").read()


class Deal:
    def __init__(self, url=None, number=0, raw_hands=None, no_data=False):
        self.data = {}
        if url:
            self.url = url.lower()
            for q in self.url.split("?")[1].split("&"):
                self.data[q.split("=")[0]] = q.split("=")[1]
            self.parse_hands_to_suits()
        elif number and not no_data:
            try:
                self.get_board_from_db(number)
            except:
                pass
        elif raw_hands:
            for i, h in enumerate(hands):
                self.data[h] = ""
                for j, s in enumerate(SUITS):
                    self.data[f"{h}{s}"] = raw_hands[4 * i + j + 1]
                    self.data[h] += s + raw_hands[4 * i + j + 1]
            self.data["b"] = raw_hands[0]
            self.data["d"] = "wnes"[raw_hands[0] % 4]
            self.data["v"] = VULNERABILITY[raw_hands[0] % 16]
            self.url = bbo_url_template.format(n=self.data["n"], s=self.data["s"], e=self.data["e"], w=self.data["w"],
                                               v=self.data["v"], d=self.data["d"], b=self.data["b"])
            print(self.url)
        self.get_html()

    def get_board_from_db(self, number):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"Select * from boards where number={number}")
        board = cursor.fetchone()
        conn.close()
        fields = ["ns", "nh", "nd", "nc", "es", "eh", "ed", "ec", "ss", "sh", "sd", "sc", "ws", "wh", "wd", "wc"]
        for i, field in enumerate(fields):
            self.data[field] = board[i + 1]
        for seat in "nesw":
            self.data[seat] = ""
            for suit in "shdc":
                self.data[seat] += suit + self.data[f"{seat}{suit}"]
        self.data["b"] = number
        self.data["d"] = "wnes"[number % 4]
        self.data["v"] = VULNERABILITY[number % 16]
        self.url = bbo_url_template.format(n=self.data["n"], s=self.data["s"], e=self.data["e"], w=self.data["w"],
                                           v=self.data["v"], d=self.data["d"], b=self.data["b"])

    def parse_hands_to_suits(self):
        for k in "nsew":
            v = self.data[k]
            for suit in "cdhs":
                self.data[f"{k}{suit}"] = v.split(suit)[1]
                v = v.split(suit)[0]

    @property
    def pbn(self):
        pbn = "N:"
        hands = [".".join(self.data[f"{position}{suit}"] for suit in "shdc") for position in "nesw"]
        return (pbn + " ".join(hands)).encode()

    def is_vul(self, declarer):
        return declarer.lower() in self.data["v"].lower() or self.data["v"] == 'ALL'

    def url_with_contract(self, level, denomination, declarer):
        dealer = self.data["d"].upper()
        pre_passes = "p" * (("NESW".index(declarer.upper()) - "NESW".index(dealer.upper())) % 4)
        return self.url.replace("ppp", f'{pre_passes}{level}{denomination}ppp')

    def get_total_points(self, declarer, denomination, tricks, result=None, multiplier=""):
        """
        Gets total points
        :param declarer: nsew
        :param denomination: cdhsn
        :param tricks: 7..13
        :param result: 7..13
        :param multiplier: "" or "x" or "xx"
        :return: total points
        """
        multiplier = 2 ** multiplier.count("x")
        vul = self.is_vul(declarer)
        if result is None:
            result = tricks
        level = tricks - 6
        if result < tricks:
            if not multiplier:
                return (50 + 50 * vul) * (result - tricks)
            return self.sac_score(declarer, result - tricks) * 2 ** (multiplier - 1)
        trick_value = 20 if denomination in "cd" else 30
        base_cost = level * trick_value + 10 * (denomination == "n")
        bonus = 50 * multiplier
        if base_cost * multiplier >= 100:
            bonus += [250, 450][vul]
            if level == 6:
                bonus += [500, 750][vul]
            elif level == 7:
                bonus += [1000, 1500][vul]
        overtrick_value = [50, 100] * vul * multiplier if multiplier > 1 else trick_value
        return bonus + base_cost + overtrick_value * (result - tricks)

    def sac_score(self, declarer, undertricks):
        if undertricks == 1:
            return 200 if self.is_vul(declarer) else 100
        elif undertricks == 2:
            return 500 if self.is_vul(declarer) else 300
        else:
            return -400 + 300 * (undertricks + self.is_vul(declarer))

    def get_cheapest_sacrifice(self, winner_score, winner_tricks, winner_denomination, loser):
        cheapest_sacrifice = winner_score
        for declarer in loser:
            for denomination in "cdhsn":
                sac_on_next_level = "cdhsn".index(denomination) <= "cdhsn".index(winner_denomination)
                if not sac_on_next_level and winner_denomination == denomination:
                    continue
                undertricks = winner_tricks - self.data[
                    f"{declarer}_par_{denomination}"] + sac_on_next_level
                sac_score = self.sac_score(declarer, undertricks)
                if sac_score < cheapest_sacrifice:
                    cheapest_sac_denomination = denomination
                    cheapest_sacrifice = sac_score
                    sac_declarer = declarer
                    break
        if cheapest_sacrifice < winner_score:
            return {"level": winner_tricks + sac_on_next_level - 6,
                    "denomination": f"{cheapest_sac_denomination}x",
                    "declarer": sac_declarer,
                    "score": (-1) ** (sac_declarer in "ew") * cheapest_sacrifice,
                    "minimax_url": self.url_with_contract(winner_tricks + sac_on_next_level - 6,
                                                          f"{cheapest_sac_denomination}x",
                                                          sac_declarer),
                    "result": "-{}".format(
                        winner_tricks - self.data[f"{sac_declarer}_par_{cheapest_sac_denomination}"] + sac_on_next_level)
                    }
        return {}

    def get_winner(self, total_points):
        ns_score = ew_score = 0
        winning_contracts = []
        for declarer, data in total_points.items():
            for den, (tricks, score, sac) in data.items():
                if declarer in "ns" and score >= ns_score:
                    ns_score = score
                    ns_den = den.lower()[0]
                    ns_tricks = tricks
                    if score > ns_score:
                        winning_contracts = []
                    else:
                        winning_contracts.append((tricks, den, sac))
                elif declarer in "ew" and score >= ew_score:
                    ew_score = score
                    ew_den = den.lower()[0]
                    ew_tricks = tricks
                    if score > ns_score:
                        winning_contracts = []
                    else:
                        winning_contracts.append((tricks, den, sac))
        if ns_tricks > ew_tricks:
            winner = "ns"
        elif ns_tricks < ew_tricks:
            winner = "ew"
        elif "cdhsn".index(ns_den) >= "cdhsn".index(ew_den):
            winner = "ns"
        else:
            winner = "ew"
        loser = "nsew".replace(winner, "")
        if winner == "ns":
            winner_score = ns_score
            winner_denomination = ns_den
            winner_tricks = ns_tricks
        else:
            winner_score = ew_score
            winner_denomination = ew_den
            winner_tricks = ew_tricks
        if all(r[2] for r in winning_contracts):
            best_sacrifice = list(sorted(winning_contracts, key=lambda x: x[0]))[0][2]
            self.data.update(best_sacrifice)
            return
        elif all(r[2] is None for r in winning_contracts):
            lowest_contracts = [self.look_down(winner, loser, c[0], winner_score) for c in winning_contracts]
            minimax = list(sorted(lowest_contracts, key=lambda x: x[0]))[0]

        for tricks in range(13, 6, -1):
            for den in "nshdc":
                declarers = [d for d in "nsew" if self.data[f"{d}_par_{den[0]}"] == tricks]
                if declarers:
                    declarer = declarers[0]
                    winner_score = total_points[declarer][den][1]
                    winner_denomination = den
                    winner_tricks = tricks
                    winner = "ns" if declarer in "ns" else "ew"
                    return winner, winner_denomination, winner_tricks, winner_score
        return "ns", "", 0, 0

    def look_down(self, winner, loser, winner_tricks, winner_score):
        for less_tricks in range(7, winner_tricks + 1):
            for decl in winner:
                for denomination in "cdhsn":
                    tricks_taken = self.data[f"{decl.lower()}_par_{denomination[0].lower()}"]
                    if tricks_taken > winner_tricks:
                        continue

                    points = self.get_total_points(decl, denomination, less_tricks,
                                                   self.data[f"{decl.lower()}_par_{denomination[0].lower()}"])
                    if points >= winner_score \
                            and not self.get_cheapest_sacrifice(points, less_tricks, denomination, loser):
                        winner_tricks = self.data[f"{decl.lower()}_par_{denomination[0].lower()}"]
                        return {
                            "level": less_tricks - 6,
                            "denomination": denomination,
                            "declarer": decl,
                            "score": (-1) ** (decl in "ew") * points,
                            "minimax_url": self.url_with_contract(less_tricks - 6, denomination, decl),
                            "result": "=" if less_tricks == winner_tricks
                                      else "+{}".format(winner_tricks - less_tricks)
                        }

    def get_minimax(self):
        total_points = {}
        dd = ddstable.get_ddstable(self.pbn).items()
        for declarer, contracts in dd:
            declarer = declarer.lower()
            total_points[declarer] = {}
            for denomination, max_tricks in contracts.items():
                self.data[f"{declarer.lower()}_par_{denomination[0].lower()}"] = max_tricks
                result = self.get_total_points(declarer, denomination.lower()[0], max_tricks)
                #sac = self.get_cheapest_sacrifice(result, max_tricks, denomination.lower()[0],
                #                                  "ew" if declarer in "ns" else "ns")

                total_points[declarer.lower()][denomination[0].lower()] = [
                    max_tricks, result#, sac

                ]
        # TODO: remove
        return
        winner, winner_denomination, winner_tricks, winner_score = self.get_winner(total_points)
        if winner_score == 0:
            self.data["level"] = "PASS"
            self.data["denomination"] = ""
            self.data["declarer"] = "N"
            self.data["score"] = 0
            return

        # for declarer, data in total_points.items():
        #     for den, (tricks, score) in data.items():
        #         # >= determines maximum level at which contract could be made
        #         if self.data["b"] == "8":
        #
        #             print(declarer, den, tricks, score, ew_score)
        #         if declarer in "ns" and score >= ns_score:
        #             ns_score = score
        #             ns_den = den.lower()[0]
        #             ns_tricks = tricks
        #         elif declarer in "ew" and score >= ew_score:
        #             ew_score = score
        #             ew_den = den.lower()[0]
        #             ew_tricks = tricks
        # if self.data["b"] == "8":
        #     print(ns_tricks, ew_tricks)
        # if ns_score + ew_score == 0:
        #     self.data["level"] = "PASS"
        #     self.data["denomination"] = ""
        #     self.data["declarer"] = "N"
        #     self.data["score"] = 0
        #     return
        # if ns_tricks > ew_tricks:
        #     winner = "ns"
        # elif ns_tricks < ew_tricks:
        #     winner = "ew"
        # elif "cdhsn".index(ns_den) >= "cdhsn".index(ew_den):
        #     winner = "ns"
        # else:
        #     winner = "ew"
        loser = "nsew".replace(winner, "")
        # if winner == "ns":
        #     winner_score = ns_score
        #     winner_denomination = ns_den
        #     winner_tricks = ns_tricks
        # else:
        #     winner_score = ew_score
        #     winner_denomination = ew_den
        #     winner_tricks = ew_tricks
        sac = self.get_cheapest_sacrifice(winner_score, winner_tricks, winner_denomination, loser)
        if sac:
            self.data.update(sac)
            return
        for less_tricks in range(7, winner_tricks + 1):
            for decl in winner:
                for denomination in "cdhsn":
                    tricks_taken = self.data[f"{decl.lower()}_par_{denomination[0].lower()}"]
                    if tricks_taken > winner_tricks:
                        continue

                    points = self.get_total_points(decl, denomination, less_tricks,
                                                   self.data[f"{decl.lower()}_par_{denomination[0].lower()}"])
                    if points >= winner_score \
                            and not self.get_cheapest_sacrifice(points, less_tricks, denomination, loser):
                        winner_tricks = self.data[f"{decl.lower()}_par_{denomination[0].lower()}"]
                        self.data.update({
                            "level": less_tricks - 6,
                            "denomination": denomination,
                            "declarer": decl,
                            "score": (-1) ** (decl in "ew") * points,
                            "minimax_url": self.url_with_contract(less_tricks - 6, denomination, decl),
                            "result": "=" if less_tricks == winner_tricks
                                      else "+{}".format(winner_tricks - less_tricks)
                        })
                        return
        else:
            raise Exception("Can't find minimax")

    def get_html(self):
        # Vul to bridgemate style
        self.data["v"] = {"-": "-", "n": "NS", "e": "EW", "b": "ALL"}[self.data["v"]]
        # colors
        self.data["nscolor"] = "palegreen" if self.data["v"] in ("EW", "-") else "tomato"
        self.data["ewcolor"] = "palegreen" if self.data["v"] in ("NS", "-") else "tomato"
        self.get_minimax()
        for k in "nsew":
            for suit in "cdhs":
                self.data[f"{k}{suit}"] = self.data[f"{k}{suit}"].replace("t", "10")
        board_html = board_template
        analysis_html = analysis_template
        for var in self.data.keys():
            if "_par_" in var or var == "minimax_url":
                var_formatted = str(self.data[var])
            else:
                var_formatted = str(self.data[var]) if type(self.data[var]) == int \
                    else self.data[var].upper().replace("X", "x") or '--'
            board_html = board_html.replace("${" + var + "}", var_formatted)
            analysis_html = analysis_html.replace("${" + var + "}", var_formatted)
        dealer = self.data["d"].upper()
        self.board_html = board_html.replace(f'>{dealer}<', f'style="text-decoration:underline;"><b>{dealer}</b><')
        self.analysis_html = analysis_html
        return board_html, analysis_html
