import itertools
import random
from copy import deepcopy
from tourney_db import TourneyDB
from constants import AM


class SwissMovement:
    def __init__(self, pairs: int):
        self.pairs = pairs
        self.adj = self.pairs + self.pairs % 2
        self.numbers_by_rank, self.names = self.get_names()
        self.has_played = self.restart()
        self.history = []
        self.round = 0
        self.totals = [0] * self.adj
        self.pairing = []
        self.nonpairable = []

    def get_names(self):
        """
        Names are 0...n-1 because of the recursion in _pair() method
        """
        conn = TourneyDB.connect()
        cur = conn.cursor()
        rank = "rank" if AM else "rank_ru"
        cur.execute(f"select number, partnership, {rank} from names order by {rank} desc")
        players = cur.fetchall()
        numbers_by_rank = [p[0] - 1 for p in players]
        names = {}
        for res in sorted(players, key=lambda x: x[0]):
            names[str(res[0] - 1)] = res[1]
        if self.adj > self.pairs:
            names[str(self.pairs)] = "BYE"
            numbers_by_rank.append(self.pairs)

        conn.close()
        return numbers_by_rank, names

    def __iter__(self):
        yield from self.history

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
        return_value = self._pair(sorted_pairs)

        return return_value

    def start_round(self):
        if not self.round:
            half = (self.pairs + 1) // 2
            self.pairing = [[self.numbers_by_rank[i], self.numbers_by_rank[i + half]] for i in range(half)]
        else:
            self.pair()
        self.round += 1
        for i, pairs in enumerate(self.pairing):
            self.history.append([pairs[0] + 1, pairs[1] + 1, self.round])
            less = min(pairs)
            greater = max(pairs)
            if 0 < i % 4 < 3:
                # (top, bottom) (bottom, top) (bottom, top) (top, bottom)
                # Can't see any reason for this, but cf. https://bridgemoscow.ru/tournaments/results/m22mem/m22memr1.htm
                self.pairing[i] = self.pairing[i][-1::-1]
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
    s = SwissMovement(8)
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
