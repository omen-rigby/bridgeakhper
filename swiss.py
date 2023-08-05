import itertools
import random
from copy import deepcopy
from tourney_db import TourneyDB
from players import Players, ALL_PLAYERS


class SwissMovement:
    def __init__(self, pairs: int):
        self.pairs = pairs
        self.adj = self.pairs + self.pairs % 2
        self.names = self.get_names()
        self.has_played = self.restart()
        self.round = 0
        self.totals = [0] * self.adj
        self.pairing = []
        self.nonpairable = []

    def get_names(self):
        conn = TourneyDB.connect()
        cur = conn.cursor()
        cur.execute("select number, partnership from names order by number")
        return_value = {}
        for i, res in enumerate(cur.fetchall()):
            players = [p[0].split(' ')[-1] for p in Players.lookup(res[1], ALL_PLAYERS)]
            return_value[str(i)] = " & ".join(players)
        if self.adj > self.pairs:
            return_value[str(self.pairs)] = "BYE"
        conn.close()
        return return_value

    def __iter__(self):
        for p in self.pairing:
            yield p[0] + 1, p[1] + 1, self.round

    def restart(self):
        """
        returns a list of boolean values sorted as below:
        1 vs 2, 1 vs 3, ... 1 vs n
        2 vs 3, ..., 2 vs n
        ...
        n-1 vs n
        True means the two pairs have played against each other
        """
        self.has_played = [False] * (self.adj * (self.adj - 1) // 2)
        return self.has_played

    def played(self, pair1, pair2):
        if pair2 < pair1:
            pair2, pair1 = pair1, pair2
        return self.has_played[int((self.adj - 1 - (pair1 - 1) / 2) * pair1 + pair2 - pair1 - 1)]

    def _pair(self, sorted_pairs, first_index=0):
        if not first_index:
            self.pairing = []
        if first_index == self.adj - 1:
            self.nonpairable = []
            return self.pairing

        first = sorted_pairs[first_index]
        if first in itertools.chain(*self.pairing):
            return self._pair(sorted_pairs, first_index=first_index + 1)
        second = [p for p in sorted_pairs[first_index + 1:] if not self.played(first, p)
                  and p not in itertools.chain(*self.pairing) and str(self.pairing + [[first, p]]) not in map(str, self.nonpairable)]
        if second:
            self.pairing.append([first, second[0]])
            return self._pair(sorted_pairs, first_index=first_index + 1)
        else:
            self.nonpairable.append(deepcopy(self.pairing))
            self.pairing.pop()
            return self._pair(sorted_pairs, first_index=sorted_pairs.index(self.pairing[-1][0]))

    def pair(self):
        sorted_totals = list(reversed(sorted(self.totals)))
        sorted_pairs = [None] * self.adj
        for i in range(self.adj):
            index = sorted_totals.index(self.totals[i])
            sorted_pairs[[j for j in range(index, self.adj) if sorted_pairs[j] is None][0]] = i
        return self._pair(sorted_pairs)

    def start_round(self):
        if not self.round:
            half = (self.pairs + 1) // 2
            self.pairing = [[i, i + half] for i in range(half)]
        else:
            self.pair()
        self.round += 1
        for pairs in self.pairing:
            less = min(pairs)
            greater = max(pairs)
            self.has_played[int((self.adj - 1 - (less - 1) / 2) * less + greater - less - 1)] = True
        printable_pairs = []
        for pair in self.pairing:
            printable_pairs.append(self.names[str(pair[0])] + ' VS ' + self.names[str(pair[1])])
        if self.adj > self.pairs and "BYE" not in printable_pairs[-1]:
            bye_index = [i for i,p in enumerate(printable_pairs) if 'BYE' in p][0]
            printable_pairs.append(printable_pairs.pop(bye_index))
        return f'Round #{self.round}\n{"Table":<8}\tNS vs EW\n' + \
            '\n'.join(f'{i + 1:<10}\t{p}' for i, p in enumerate(printable_pairs))


if __name__ == "__main__":
    s = SwissMovement(9)
    for i in range(6):
        s.start_round()
        new_totals = [0] * s.adj
        for p in s.pairing:
            if s.adj > s.pairs and s.pairs in p:
                new_totals[sum(p) - s.pairs] = 12
            else:
                new_totals[p[0]] = random.randint(0, 20)
                new_totals[p[1]] = 20 - new_totals[p[0]]
        s.totals = [t + n for n, t in zip(new_totals, s.totals)]
