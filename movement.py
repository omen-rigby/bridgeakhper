import itertools
from constants import CONFIG
from tourney_db import TourneyDB
from players import Players, ALL_PLAYERS


class Movement:
    def __init__(self, boards, pairs):
        self.bye = (1 if CONFIG.get("no_first_pair") else pairs + 1) if pairs % 2 else None
        self.tables = (pairs + 1) // 2
        self.boards = boards
        self.movement, self.initial_board_sets = self.get_movement()
        self._names = []

    def __iter__(self):
        return self.movement.__iter__()

    def move_card(self, pair):
        if not self.initial_board_sets:
            return
        self._names = self.get_names()
        rounds = CONFIG.get('rounds', len(self.movement) // self.tables)
        data = [None] * rounds
        boards_per_round = self.boards // rounds
        if len(self.initial_board_sets) == self.tables:
            for i, r in enumerate(self.movement):
                if r[0] == pair or r[1] == pair:
                    table = i % self.tables
                    position = "NS" if r[0] == pair else "EW"
                    first_board = int((r[2] - 1) * boards_per_round + 1)
                    boards = f"{first_board}-{int(first_board + boards_per_round - 1)}"
                    opps_no = str(r[0] + r[1] - pair)
                    data[(r[2] - self.initial_board_sets[table]) % rounds] = [str(table + 1), position,
                                                                              self.names(opps_no), boards]
        else:
            sets = self.initial_board_sets
            tables_data = []
            sets_reordered = list(itertools.chain(*[sets[i::self.tables] for i in range(self.tables)]))
            for i, sett in enumerate(sets_reordered):
                tables_data.append([m for m in self.movement if m[2] == sett][sets_reordered[:i].count(sett)])
            for i in range(rounds):
                for j, t in enumerate(tables_data[i::rounds]):
                    if pair in t[0:2]:
                        position = "NS" if t[0] == pair else "EW"
                        first_board = int((t[2] - 1) * boards_per_round + 1)
                        boards = f"{first_board}-{int(first_board + boards_per_round - 1)}"
                        opps_no = str(t[0] + t[1] - pair)
                        data[i] = [str(j + 1), position, self.names(opps_no), boards]
        return "Round\tTable\tPosition\tOpp\tBoards\n" + '\n'.join('\t'.join([str(i + 1)] + (d or []))
                                                                   for i, d in enumerate(data))

    def names(self, number, short=True):
        return " & ".join(o[0].strip().split(' ')[-1] if short else o[0] for o in self._names[str(number)]) or number

    def table_card(self, table):
        if not self.initial_board_sets:
            return
        self._names = self.get_names()
        boards_per_round = self.boards // CONFIG.get('rounds', len(self.movement) / self.tables)
        data = []
        if len(self.initial_board_sets) == self.tables:
            for i, m in enumerate(self.movement[table - 1::self.tables]):
                current_set = m[2]
                first_board = (current_set - 1) * boards_per_round + 1
                boards = f"{int(first_board)}-{int(first_board + boards_per_round - 1)}"
                data.append(list(map(self.names, m[:-1])) + [boards])
            first_set = self.initial_board_sets[table - 1] - 1
            data = data[first_set:] + data[:first_set]
        else:
            # this is bullshit, but otherwise it's hard to combine move cards & remembering tournaments from input
            rounds = CONFIG.get('rounds', len(self.movement) // self.tables)
            sets = self.initial_board_sets
            tables_data = []
            sets_reordered = list(itertools.chain(*[sets[i::self.tables] for i in range(self.tables)]))
            for i, sett in enumerate(sets_reordered):
                tables_data.append([m for m in self.movement if m[2] == sett][sets_reordered[:i].count(sett)])
            for t in tables_data[rounds * (table - 1) : rounds * table]:
                first_board = (t[2] - 1) * boards_per_round + 1
                boards = f"{int(first_board)}-{int(first_board + boards_per_round - 1)}"
                data.append(list(map(lambda x: self.names(x), t[:-1])) + [boards])
        return "Round\tNS\tEW\tBoards\n" + '\n'.join('\t'.join([str(r + 1)] + d) for
                                                     r, d in enumerate(data))

    def get_movement(self):
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        is_mitchell = CONFIG.get("is_mitchell")
        cursor.execute(f"select movement, initial_board_sets from movements where tables={self.tables} and is_mitchell={is_mitchell}")
        movements = cursor.fetchall()
        conn.close()
        if movements:
            raw_data = [[[int(r.split('-')[0]), int(r.split('-')[1]), round_num + 1] for r in rawnd.split(',')]
                        for round_num, rawnd in enumerate(movements[0][0].split(';'))]
            initial_sets = list(map(int, movements[0][1].split(','))) if movements[0][1] else list(range(1, self.tables + 1))
            # list of [ns, ew, board_set (1...n_rounds)]
            return list(itertools.chain(*raw_data)), initial_sets

        else:
            return ""

    def get_names(self):
        conn = TourneyDB.connect()
        cur = conn.cursor()
        cur.execute("select number, partnership from names order by number")
        return_value = {str(res[0]): Players.lookup(res[1], ALL_PLAYERS) for res in cur.fetchall()}
        if self.bye:
            return_value[str(self.bye)] = [["BYE"]]
        conn.close()
        return return_value


if __name__ == "__main__":
    m = Movement(27, 9)
    print(m.move_card(3))
    print(m.table_card(2))
