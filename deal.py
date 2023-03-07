from tourney_db import TourneyDB
from ddstable import ddstable
from constants import *

bbo_url_template = "https://www.bridgebase.com/tools/handviewer.html?n={n}&e={e}&s={s}&w={w}&d={d}&v={v}&b={b}&a=ppp"
board_template = open("templates/board_template").read()
analysis_template = open("templates/analysis_template").read()


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

        self.get_html()

    def get_board_from_db(self, number):
        conn = TourneyDB.connect()
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
            return -self.sac_score(declarer, tricks - result) * multiplier / 2
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

    def _next_optimum(self, current_level, current_denomination, current_declarer, current_optimum):
        return_value = None
        current_optimum = -current_optimum
        denom_index = DENOMINATIONS.index(current_denomination) + 1
        decl_index = hands.index(current_declarer)
        for level in range(current_level, 8):
            for denomination in DENOMINATIONS[(level == current_level) * denom_index:]:
                for declarer in (hands[(decl_index + 1) % 4], hands[(decl_index + 3) % 4]):
                    result = self.data[f"{declarer.lower()}_par_{denomination[0].lower()}"]
                    if not current_level and result < level + 6:
                        continue
                    optimum_candidate = self.get_total_points(declarer, denomination, 6 + level, result,
                                                              multiplier='x' * (result < level + 6))
                    if optimum_candidate > current_optimum:
                        current_optimum = optimum_candidate
                        return_value = level, denomination + 'x' * (optimum_candidate < 0), declarer, optimum_candidate
        return return_value

    def get_minimax(self):
        total_points = {}
        dd = ddstable.get_ddstable(self.pbn.replace(b'10', b't')).items()
        for declarer, contracts in dd:
            declarer = declarer.lower()
            total_points[declarer] = {}
            for denomination, max_tricks in contracts.items():
                self.data[f"{declarer.lower()}_par_{denomination[0].lower()}"] = max_tricks
                result = self.get_total_points(declarer, denomination.lower()[0], max_tricks)
                total_points[declarer.lower()][denomination[0].lower()] = [
                    max_tricks, result
                ]
        declarer = hands[(hands.index(self.data["d"]) - 1) % 4]
        level = 0
        denomination = 'n'
        optimum = 0
        while True:
            result = self._next_optimum(level, denomination[0], declarer, optimum)
            if result is None:
                if not level:
                    result = self._next_optimum(level, denomination[0], self.data['d'], optimum)
                if result is None:
                    break

            level, denomination, declarer, optimum = result
        if not level:
            self.data.update({"level": "PASS", "denomination": "", "declarer": "", "score": 0, "result": ''})
        else:
            par = self.data[f"{declarer.lower()}_par_{denomination[0].lower()}"]
            if 'x' not in denomination:
                results = [(l, self.get_total_points(declarer, denomination, l + 6, par)) for l in range(level, par)]
                results.sort(key=lambda r: (-r[1], r[0]))
                level, optimum = results[0]
                result = f'+{par - level - 6}' if par > level + 6 else '='
            else:
                result = par - level - 6
            self.data.update({"level": str(level), "denomination": denomination, "declarer": declarer.upper(),
                              "score": str(int(optimum * (-1) ** (declarer in 'ew'))), "result": result,
                              'minimax_url': self.url_with_contract(level, denomination, declarer)})

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
