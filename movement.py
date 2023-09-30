import itertools
from constants import CONFIG
from tourney_db import TourneyDB
from players import Players, ALL_PLAYERS
from jinja2 import Template
from print import *
from util import Dict2Class


class Movement:
    """
    This doesn't generate movements, only processed ones stored in movements db table.
    Actual movements can be taken from https://tedmuller.us/Bridge/Director/Movements.htm
    """
    def __init__(self, boards, pairs, session_index=0):
        self.pairs = pairs
        self.bye = (1 if CONFIG.get("no_first_pair") else pairs + 1) if pairs % 2 else None
        self.tables = (pairs + 1) // 2
        self.boards = boards
        self.session_index = session_index
        # "3/4" howell
        self.rounds = boards // (boards // (2 * self.tables - 1) + 1) \
            if boards % (2 * self.tables - 1) else 2 * self.tables - 1
        self.movement, self.initial_board_sets = self.get_movement()
        self._names = {}

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
        if str(number) in self._names.keys():
            return " & ".join(o[0].strip().split(' ')[-1] if short else o[0] for o in self._names[str(number)])
        return str(number)

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
        statement = f"select movement, initial_board_sets from movements where tables={self.tables} " \
                    f"and is_mitchell={is_mitchell} and " \
                    f"MOD(array_length(string_to_array(movement, ';'), 1),{self.rounds})=0"
        cursor.execute(statement)
        movement = cursor.fetchone()
        conn.close()
        if movement:
            raw_data = [[[int(r.split('-')[0]), int(r.split('-')[1]), round_num + 1] for r in rawnd.split(',')]
                        for round_num, rawnd in enumerate(movement[0].split(';'))]
            initial_sets = list(map(int, movement[1].split(','))) if movement[1] else list(range(1, self.tables + 1))
            # list of [ns, ew, board_set (1...n_rounds)]
            return list(itertools.chain(*raw_data)), initial_sets

        else:
            return ""

    def get_names(self):
        first = 100 * self.session_index
        conn = TourneyDB.connect()
        cur = conn.cursor()
        cur.execute(f"select number, partnership from names where {first} < number and number < {first + 100} order by number")
        all_players = cur.fetchall()
        return_value = {str(res[0]): Players.lookup(res[1], ALL_PLAYERS) for res in all_players}
        if self.bye:
            return_value[str(self.bye)] = [["BYE"]]
        conn.close()
        return return_value

    def pdf(self):
        rounds = CONFIG.get('rounds', len(self.movement) // self.tables)
        self._names = self.get_names()
        movement_dict = {'tables': self.tables, 'boards': self.boards, 'type': 'Howell', 'pairs': [Dict2Class({
            'number': i, 'names': self.names(i),
            'rounds': [None] * rounds}) for i in range(1, self.tables * 2 + 1)]}
        boards_per_round = self.boards // rounds
        if len(self.initial_board_sets) == self.tables:
            # assumes that board sets change +1, otherwise whole movement is written in initial_board_sets column
            for i, r in enumerate(self.movement):
                for pair in r[:1]:
                    table = i % self.tables
                    data = [p for p in movement_dict['pairs'] if p.number == pair][0].rounds
                    position = "NS" if r[0] == pair else "EW"
                    first_board = int((r[2] - 1) * boards_per_round + 1)
                    boards = f"{first_board}-{int(first_board + boards_per_round - 1)}"
                    opps_no = str(r[0] + r[1] - pair)
                    round_index = (r[2] - self.initial_board_sets[table]) % rounds
                    opps_data = [p for p in movement_dict['pairs'] if str(p.number) == opps_no][0].rounds
                    data[round_index] = Dict2Class({
                        'number': round_index + 1, 'table': str(table + 1), 'position': position,
                        'opps': self.names(opps_no).replace(' ', '&nbsp;'), 'boards': boards})
                    opps_data[round_index] = Dict2Class({
                        'number': round_index + 1, 'table': str(table + 1), 'position': "NSEW".replace(position, ""),
                        'opps': self.names(pair).replace(' ', '&nbsp;'), 'boards': boards})
            if self.bye:
                movement_dict['pairs'].pop(self.bye - 1)
        else:
            sets = self.initial_board_sets
            tables_data = []
            sets_reordered = list(itertools.chain(*[sets[i::self.tables] for i in range(self.tables)]))
            for i, sett in enumerate(sets_reordered):
                tables_data.append([m for m in self.movement if m[2] == sett][sets_reordered[:i].count(sett)])
            for i in range(rounds):
                for j, t in enumerate(tables_data[i::rounds]):
                    for pair in t[0:2]:
                        data = [p for p in movement_dict['pairs'] if p.number == pair][0].rounds
                        position = "NS" if t[0] == pair else "EW"
                        first_board = int((t[2] - 1) * boards_per_round + 1)
                        boards = f"{first_board}-{int(first_board + boards_per_round - 1)}"
                        opps_no = str(t[0] + t[1] - pair)

                        data[i] = Dict2Class(
                            {'number': i + 1, 'table': str(j + 1), 'position': position,
                             'opps': self.names(opps_no).replace(' ', '&nbsp;'),  'boards': boards})
        html_string = Template(open("templates/movement_template.html").read()).render(**movement_dict)
        return print_to_pdf(html_string, "Movement.pdf")


if __name__ == "__main__":
    m = Movement(18, 4)
    print(m.pdf())
    #print(m.table_card(2))
