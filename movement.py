import itertools
import json

from exceptions import MovementError
from constants import CONFIG
from tourney_db import TourneyDB
from jinja2 import Template
from print import *
from util import Dict2Class
from decimal import Decimal, ROUND_HALF_UP

class Movement:
    """
    This doesn't generate movements (unless Mitchell), only processed ones stored in movements db table.
    Actual movements can be taken from https://tedmuller.us/Bridge/Director/Movements.htm
    """
    def __init__(self, boards, pairs, session_index=0, rounds=0):
        self.pairs = pairs
        self.tables = (pairs + 1) // 2
        self.boards = boards
        self.session_index = session_index
        # "3/4" howell
        self.rounds = rounds
        # TODO: investigate
        # CONFIG.get('rounds', boards // (boards // (2 * self.tables - 1) + 1) \
        #     if boards % (2 * self.tables - 1) else 2 * self.tables - 1)
        self.mitchell = False
        self.skip_mitchell = False
        self.bye = self.get_bye()
        self.movement, self.initial_board_sets = self.get_movement()
        self._names = {}

    def __iter__(self):
        return self.movement.__iter__()

    def get_bye(self):
        if self.pairs % 2 == 0:
            return None
        elif self.mitchell:
            return self.tables
        elif CONFIG.get("no_first_pair", False):
            return 1
        elif CONFIG.get('pair_zero', False):
            return 0
        else:
            return self.pairs + 1

    def create_mitchell(self):
        if self.tables > 4 and ((self.tables % 2 and not self.boards % self.tables) or
                                (self.tables % 2 == 0 and not self.boards % (self.tables - 1))):
            self.mitchell = True
            self.skip_mitchell = not self.tables % 2
            self.rounds = self.tables - 1 if self.skip_mitchell else self.tables
            arrow_switch = 2 / 3 * self.rounds
            self.bye = self.tables if self.pairs % 2 else 0
            movement = []
            for set_index in range(self.tables):
                skipped = False
                for table_index in range(self.tables):
                    if self.skip_mitchell and not skipped and (len(movement) % self.tables - set_index) % self.tables == 1:
                        movement.append([0, 0, 0])
                        skipped = True
                        continue
                    skip_decrement = bool((set_index - table_index) % self.tables >= 4)
                    opp = (2 * table_index - set_index - skip_decrement) % self.tables + self.tables + 1
                    if (set_index - table_index) % self.tables > arrow_switch:
                        movement.append([opp, table_index + 1, set_index + 1])
                    else:
                        movement.append([table_index + 1, opp, set_index + 1])

            return movement, list(range(1, self.tables + 1))
            # 1 - 8, 10 - 2, 12 - 3, 4 - 14, 5 - 9, 6 - 11, 7 - 13;
            # 1 - 14, 2 - 9, 11 - 3, 13 - 4, 5 - 8, 6 - 10, 7 - 12;
            # 1 - 13, 2 - 8, 3 - 10, 12 - 4, 14 - 5, 6 - 9, 7 - 11;
            # 1 - 12, 2 - 14, 3 - 9, 4 - 11, 13 - 5, 8 - 6, 7 - 10;
            # 1 - 11, 2 - 13, 3 - 8, 4 - 10, 5 - 12, 14 - 6, 9 - 7;
            # 10 - 1, 2 - 12, 3 - 14, 4 - 9, 5 - 11, 6 - 13, 8 - 7;
            # 9 - 1, 11 - 2, 3 - 13, 4 - 8, 5 - 10, 6 - 12, 7 - 14

    def get_movement(self):
        """Movement is stored as following:
        movement field:
        semicolon separates the board set data, each of which is a list of pairs of numbers which play this set,
        they are sorted by table number (!) not by round number
        board_sets is comma-separated list of board sets.
        If board sets change sequentially at each table, numbers for the 1st round are stored sorted by table number again.
        Otherwise, all rounds are stored
        """
        conn = TourneyDB.connect()
        cursor = conn.cursor()
        is_mitchell = CONFIG.get("is_mitchell")
        is_barometer = CONFIG.get("is_barometer", False) or ((CONFIG.get("force_barometer", False) and self.pairs < 6))
        possible_rounds = [self.rounds] if self.rounds else [r for r in range(2, self.boards + 1) if self.boards % r == 0]
        if self.tables == 2:
            possible_rounds.append(6)
        possible_movements = set()
        rounds_with_movements = set()
        for r in possible_rounds:
            maxrounds = self.tables * 2 - 1 if self.tables > 2 else self.tables * 4 - 2
            statement = f"select movement, initial_board_sets, rounds from (select movement, initial_board_sets, least(" \
                        f"array_length(string_to_array(movement, ';'), 1), "\
                        f"array_length(string_to_array(movement, '-'), 1) / tables) as rounds" \
                        f" from movements where tables={self.tables} " \
                        f"and is_mitchell={is_mitchell} and is_barometer={is_barometer}) as results where "\
                        f"least(rounds, {maxrounds}) = {r}"
            cursor.execute(statement)
            movement = cursor.fetchall()
            if movement:
                # https://www.jeff-goldsmith.com/moves/howell3.html double round-robin for 3 tables
                rounds_adjusted = [m[2] for m in movement]
                rounds_with_movements.update(rounds_adjusted)
                possible_movements.update(movement)
                self.rounds = rounds_adjusted[0]

        conn.close()
        if len(possible_movements) == 1:
            movement = possible_movements.pop()
            decrement = self.bye == 0
            raw_data = [[[int(r.split('-')[0]) - decrement, int(r.split('-')[1]) - decrement, round_num + 1]
                         for r in rawnd.split(',')]
                        for round_num, rawnd in enumerate(movement[0].split(';'))]
            if is_barometer:
                initial_sets = list(n // self.rounds + 1 for n in range(1, self.tables + 1))
            else:
                initial_sets = list(map(int, movement[1].split(','))) if movement[1] else list(range(1, self.tables + 1))
            # list of [ns, ew, board_set (1...n_rounds)]

            return list(itertools.chain(*raw_data)), initial_sets
        elif not possible_movements:
            if mitchell := self.create_mitchell():
                return mitchell
            raise MovementError('No suitable movement')
        else:
            rounds = ",".join(map(str, sorted(rounds_with_movements)))
            raise MovementError(f'Found multiple movements. Set the number of rounds first: {rounds}')

    def move_card(self, pair):
        if not self.initial_board_sets:
            return
        self._names = self.get_names()
        rounds = self.rounds
        data = [None] * self.rounds
        boards_per_round = self.boards / self.rounds
        if len(self.initial_board_sets) == self.tables:
            for i, r in enumerate(self.movement):
                if r[0] == pair or r[1] == pair:
                    table = i % self.tables
                    position = "NS" if r[0] == pair else "EW"
                    first_board = Decimal((r[2] - 1) * boards_per_round + 1).to_integral_value(rounding=ROUND_HALF_UP)
                    last_board = Decimal(r[2] * boards_per_round).to_integral_value(rounding=ROUND_HALF_UP)
                    boards = f"{first_board}-{last_board}" if first_board != last_board else f"{first_board}"
                    opps_no = str(r[0] + r[1] - pair)
                    # This is likely wrong for skip mitchellx
                    round_index = (r[2] - self.initial_board_sets[table]) % (rounds + self.skip_mitchell)
                    data[round_index] = [str(table + 1), position, self.names(opps_no), boards]
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
                        first_board = Decimal((t[2] - 1) * boards_per_round + 1).to_integral_value(rounding=ROUND_HALF_UP)
                        last_board = Decimal(t[2] * boards_per_round).to_integral_value(rounding=ROUND_HALF_UP)
                        boards = f"{first_board}-{last_board}" if first_board != last_board else f"{first_board}"
                        opps_no = str(t[0] + t[1] - pair)
                        data[i] = [str(j + 1), position, self.names(opps_no), boards]
        if None in data:
            data.remove(None)
        return "<pre>Round\tTable\tPosition\tOpp\tBoards\n" + '\n'.join('\t'.join([str(i + 1)] + (d or []))
                                                                   for i, d in enumerate(data)) + '</pre>'

    def names(self, number, short=False):
        if str(number) in self._names.keys():
            if short:
                return " & ".join(o[0].strip().split(' ')[-1] for o in self._names[str(number)].split(' & '))
            return self._names[str(number)]
        return str(number)

    def table_card(self, table):
        if not self.initial_board_sets:
            return
        self._names = self.get_names()
        boards_per_round = self.boards // self.rounds
        data = []
        if len(self.initial_board_sets) == self.tables:
            for i, m in enumerate(self.movement[table - 1::self.tables]):
                current_set = m[2]
                first_board = Decimal((current_set - 1) * boards_per_round + 1).to_integral_value(rounding=ROUND_HALF_UP)
                last_board = Decimal(current_set * boards_per_round).to_integral_value(rounding=ROUND_HALF_UP)
                boards = f"{first_board}-{last_board}" if first_board != last_board else f"{first_board}"
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
                first_board = Decimal((t[2] - 1) * boards_per_round + 1).to_integral_value(rounding=ROUND_HALF_UP)
                last_board = Decimal(t[2] * boards_per_round).to_integral_value(rounding=ROUND_HALF_UP)
                boards = f"{first_board}-{last_board}" if first_board != last_board else f"{first_board}"
                data.append(list(map(lambda x: self.names(x), t[:-1])) + [boards])
        return "<pre>Round\tNS\tEW\tBoards\n" + '\n'.join('\t'.join([str(r + 1)] + d) for
                                                     r, d in enumerate(data)) + '</pre>'

    def get_names(self):
        first = 100 * self.session_index
        conn = TourneyDB.connect()
        cur = conn.cursor()
        cur.execute(f"select number, partnership from names where {first} < number and number < {first + 100} order by number")
        all_players = cur.fetchall()
        return_value = {str(res[0]): f"#{res[0]} {res[1]}" for res in all_players}
        if self.bye:
            return_value[str(self.bye)] = "BYE"
        conn.close()
        return return_value

    def pdf(self):
        rounds = self.rounds
        self._names = self.get_names()
        movement_dict = {'tables': self.tables, 'boards': self.boards,
                         'type': 'Mitchell' if CONFIG.get("is_mitchell") or self.mitchell else 'Howell',
                         'pairs': [Dict2Class({'number': i, 'names': self.names(i),
                                               'rounds': [None] * rounds}) for i in range(1, self.tables * 2 + 1)],
                         'tablecards': [Dict2Class({'number': i, 'instruction_ns': None,
                                                    'instruction_ew': None,
                                                    'rounds': [None] * rounds}) for i in range(1, self.tables + 1)],
                         'roundcards': [Dict2Class({'number': i + 1, 'tables': [None] * self.tables})
                                   for i in range(rounds)]
                         }
        boards_per_round = self.boards / rounds
        if len(self.initial_board_sets) == self.tables:
            # assumes that board sets change +1, otherwise whole movement is written in initial_board_sets column
            for i, r in enumerate(self.movement):
                for pair in r[:1]:
                    table = i % self.tables
                    table_data = [t for t in movement_dict['tablecards'] if t.number == table + 1][0].rounds
                    try:
                        pair_data = [p for p in movement_dict['pairs'] if p.number == pair][0].rounds
                    except IndexError:
                        continue
                    position = "NS" if r[0] == pair else "EW"
                    skip_mitchell_decrement = (self.skip_mitchell and
                                               (r[2] - self.initial_board_sets[table]) % rounds >= self.tables // 2)
                    board_set = r[2]
                    if board_set == 0:  # skip mitchell
                        board_set = self.tables
                    first_board = Decimal((board_set - 1) * boards_per_round + 1).to_integral_value(rounding=ROUND_HALF_UP)
                    last_board = Decimal(board_set * boards_per_round).to_integral_value(rounding=ROUND_HALF_UP)
                    boards = f"{first_board}-{last_board}" if first_board != last_board else f"{first_board}"
                    opps_no = str(r[0] + r[1] - pair)
                    round_index = (board_set - self.initial_board_sets[table]) % (rounds + self.skip_mitchell)
                    if table_data[round_index] is None:
                        table_data[round_index] = Dict2Class({'number': round_index + 1, 'ns': pair, 'ew': opps_no,
                                                              'boardset': board_set})
                    try:
                        opps_data = [p for p in movement_dict['pairs'] if str(p.number) == opps_no][0].rounds
                    except IndexError:  # BYE
                        continue

                    pair_data[round_index] = Dict2Class({
                        'number': round_index + 1, 'table': str(table + 1), 'position': position,
                        'opps': self.names(opps_no).replace(' ', '&nbsp;'), 'boards': boards})
                    opps_data[round_index] = Dict2Class({
                        'number': round_index + 1, 'table': str(table + 1), 'position': "NSEW".replace(position, ""),
                        'opps': self.names(pair).replace(' ', '&nbsp;'), 'boards': boards})
            if self.bye:
                movement_dict['pairs'].pop(self.bye - 1)
            elif self.bye == 0:
                movement_dict['pairs'].pop()
        else:
            sets = self.initial_board_sets
            tables_data = []
            sets_reordered = list(itertools.chain(*[sets[i::self.tables] for i in range(self.tables)]))
            for i, sett in enumerate(sets_reordered):
                current = [m for m in self.movement if m[2] == sett]
                tables_data.append(current[sets_reordered[:i].count(sett)])
            for i in range(rounds):
                for j, t in enumerate(tables_data[i::rounds]):
                    for pair in t[0:2]:
                        if pair == 0:
                            continue
                        data = [p for p in movement_dict['pairs'] if p.number == pair][0].rounds
                        position = "NS" if t[0] == pair else "EW"
                        first_board = Decimal((t[2] - 1) * boards_per_round + 1).to_integral_value(rounding=ROUND_HALF_UP)
                        last_board = Decimal(t[2] * boards_per_round).to_integral_value(rounding=ROUND_HALF_UP)
                        boards = f"{first_board}-{last_board}" if first_board != last_board else f"{first_board}"
                        opps_no = str(t[0] + t[1] - pair)
                        data[i] = Dict2Class(
                            {'number': i + 1, 'table': str(j + 1), 'position': position,
                             'opps': self.names(opps_no).replace(' ', '&nbsp;'),  'boards': boards})

        for p in movement_dict['pairs']:
            for round_index, pair_round_data in enumerate(p.rounds):
                if pair_round_data is None:
                    continue
                table_index = int(pair_round_data.table) - 1
                if len(movement_dict['roundcards'][round_index].tables) <= table_index:  # skip_mitchell
                    continue
                movement_dict['roundcards'][round_index].tables[table_index] = {
                    'number': table_index + 1,
                    'ns': p.names if pair_round_data.position == 'NS' else pair_round_data.opps,
                    'ew': p.names if pair_round_data.position == 'EW' else pair_round_data.opps,
                    'boards': pair_round_data.boards}
        html_string = Template(open("templates/movement_template.html").read()).render(**movement_dict)
        return print_to_file(html_string, CONFIG.get('output_format', 'pdf') == 'pdf', "Movement")

    def table_cards(self):
        rounds = self.rounds
        self._names = self.get_names()
        movement_dict = {'tables': self.tables, 'boards': self.boards,
                         'type': 'Mitchell' if CONFIG.get("is_mitchell") else 'Howell',
                         'pairs': [Dict2Class({'number': i, 'names': self.names(i),
                                               'rounds': [None] * rounds}) for i in range(1, self.tables * 2 + 1)],
                         'tablecards': [Dict2Class({'number': i, 'instruction_ns': None,
                                                    'instruction_ew': None,
                                                    'rounds': [None] * rounds}) for i in range(1, self.tables + 1)]}
        boards_per_round = self.boards / rounds
        if len(self.initial_board_sets) == self.tables:
            # assumes that board sets change +1, otherwise whole movement is written in initial_board_sets column
            for i, r in enumerate(self.movement):
                for pair in r[:1]:
                    table = i % self.tables
                    table_data = [t for t in movement_dict['tablecards'] if t.number == table + 1][0].rounds
                    try:
                        pair_data = [p for p in movement_dict['pairs'] if p.number == pair][0].rounds
                    except:  # skip mitchell
                        continue
                    position = "NS" if r[0] == pair else "EW"
                    first_board = int((r[2] - 1) * boards_per_round + 1)
                    last_board = int(first_board + boards_per_round - 1)
                    boards = f"{first_board}-{last_board}" if first_board != last_board else f"{first_board}"
                    opps_no = str(r[0] + r[1] - pair)
                    round_index = (r[2] - self.initial_board_sets[table]) % rounds
                    if table_data[round_index] is None:
                        table_data[round_index] = Dict2Class({'number': round_index + 1, 'ns': pair, 'ew': opps_no,
                                                              'boardset': r[2]})
                    try:
                        opps_data = [p for p in movement_dict['pairs'] if str(p.number) == opps_no][0].rounds
                    except IndexError:  # skip mitchell
                        continue

                    pair_data[round_index] = Dict2Class({
                        'number': round_index + 1, 'table': str(table + 1), 'position': position,
                        'opps': self.names(opps_no).replace(' ', '&nbsp;'), 'boards': boards})
                    opps_data[round_index] = Dict2Class({
                        'number': round_index + 1, 'table': str(table + 1), 'position': "NSEW".replace(position, ""),
                        'opps': self.names(pair).replace(' ', '&nbsp;'), 'boards': boards})
        else:
            sets = self.initial_board_sets
            tables_data = []
            sets_reordered = list(itertools.chain(*[sets[i::self.tables] for i in range(self.tables)]))
            for i, sett in enumerate(sets_reordered):
                tables_data.append([m for m in self.movement if m[2] == sett][sets_reordered[:i].count(sett)])
            for table_number in range(1, self.tables + 1):
                rounds = [t for t in movement_dict['tablecards'] if t.number == table_number][0].rounds
                for round_index, round_data in enumerate(
                        tables_data[self.rounds * (table_number - 1) : self.rounds * table_number]):
                    first_board = Decimal((round_data[2] - 1) * boards_per_round + 1).to_integral_value(rounding=ROUND_HALF_UP)
                    last_board = Decimal(round_data[2] * boards_per_round ).to_integral_value(rounding=ROUND_HALF_UP)
                    boards = f"{first_board}-{last_board}" if first_board != last_board else f"{first_board}"
                    rounds[round_index] = Dict2Class({'number': round_index + 1, 'ns': round_data[0],
                                                      'ew': round_data[1], 'boards': boards})
        # TODO: remove
        # movement_dict['tablecards'] = movement_dict['tablecards']
        html_string = Template(open("templates/table_cards.html").read()).render(**movement_dict)
        return print_to_file(html_string, CONFIG.get('output_format', 'pdf') == 'pdf', "Table_cards")


if __name__ == "__main__":
    from config import init_config
    init_config()
    CONFIG["force_barometer"] = False
    #CONFIG["no_first_pair"] = True
    m = Movement(21, 15)
    print(m.bye)
    # for t in range(m.tables):
    #     print(m.movement[t * m.tables:t*m.tables + m.tables])
    # print(m.move_card(9))
    # print(m.move_card(2))
    # print(m.move_card(3))
    # print(m.move_card(4))
    # print(m.move_card(15))
    # print(m.pdf())
    # print(m.table_cards())
