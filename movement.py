import itertools
import json

from exceptions import MovementError
from constants import CONFIG
from tourney_db import TourneyDB
from jinja2 import Template
from print import *
from util import Dict2Class
from decimal import Decimal, ROUND_HALF_UP


# orange book Bridge Movements p. 240 (pdf)
BAROMETER_HOWELL_START_NS = {
    2: (), 3: (), 4: (4,), 5: (4,), 6: (3,), 7: (3, 5, 6, 7), 8: (5, 7, 8), 9: (3, 4, 8), 10: (3, 4, 9),
    11: (3, 4, 9, 11), 12: (6, 8, 11, 12), 13: (4, 5, 7, 9, 10, 11, 12, 13),  14: (3, 4, 5, 6, 7, 11, 12, 14),
    15: (5, 6, 7, 9, 10, 11, 13, 14), 16: (4, 7, 12, 13, 14, 16), 17:(4, 9, 10, 13, 15, 16, 17),
    18: (3, 5, 8, 9, 11, 12, 13, 14, 15), 19: (3, 4, 6, 8, 15, 16), 20: (5, 9, 11, 14, 17, 18, 19),
    21: (3, 5, 8, 9, 11, 12, 18), 22: (3, 4, 6, 8, 9, 13, 19, 20, 21),
    23: (3, 4, 5, 8, 11, 13, 14, 15, 17, 18, 19, 20), 24: (6, 11, 12, 14, 16, 20, 21, 23, 24),
    25: (4, 11, 12, 13, 18, 21, 22, 24), 26: (3, 4, 5, 8, 10, 13, 14, 16, 20),
    27: (5, 6, 7, 8, 9, 10, 12, 13, 15, 18, 19, 22, 23, 24, 26),
    28: (4, 5, 6, 7, 9, 13, 15, 18, 23, 25, 26), 29: (3, 4, 6, 7, 8, 11, 12, 17, 18, 19, 20, 21, 23, 25, 27, 28),
    30: (3, 7, 9, 11, 12, 14, 15, 19, 24, 25),
    31: (3, 7, 8, 9, 10, 11, 12, 15, 17, 18, 21, 22, 23, 25, 26, 27, 28, 30, 31),
    32: (3, 5, 6, 7, 13, 15, 17, 18, 21, 24, 29),
    33: (3, 4, 5, 6, 8, 9, 10, 12, 13, 15, 16, 20, 21, 23, 25, 26, 27, 29),
    34: (3, 4, 6, 8, 9, 12, 13, 14, 19, 21, 28, 29, 31, 32, 33),
    35: (3, 6, 8, 9, 10, 13, 14, 19, 20, 21, 23, 28, 35), 36: (8, 12, 14, 15, 18, 22, 23, 24, 27, 29, 32, 34, 35, 36),
    37: (3, 4, 6, 10, 12, 13, 14, 15, 18, 20, 23, 27, 28, 34),
    38: (3, 4, 5, 6, 7, 11, 16, 17, 21, 24, 26, 28, 29, 30, 32, 35, 36, 37, 38),
    39: (6, 7, 8, 9, 11, 12, 14, 18, 21, 23, 25, 26, 27, 28, 29, 31, 32, 33, 36, 37, 39),
    40: (4, 7, 8, 13, 15, 16, 18, 25, 28, 29, 30, 31, 34, 35, 36, 38, 40),
    41: (4, 5, 8, 11, 13, 17, 22, 24, 27, 28, 32, 34, 35, 36, 37, 38),
    42: (3, 6, 7, 9, 14, 15, 16, 19, 20, 21, 23, 25, 33, 35, 36, 40),
    43: (5, 8, 9, 14, 15, 16, 19, 27, 28, 30, 32, 34, 36, 37, 39, 40, 41, 42),
    44: (3, 4, 6, 10, 11, 12, 16, 20, 22, 29, 30, 31, 33, 34, 36, 37, 41, 42, 44),
    45: (10, 12, 14, 16, 19, 22, 23, 26, 27, 31, 32, 34, 36, 37, 42, 43, 44, 45),
    46: (6, 8, 9, 11, 12, 13, 14, 16, 18, 21, 22, 27, 31, 33, 38, 39, 41, 42, 45, 46),
    47: (5, 7, 9, 11, 12, 15, 16, 19, 20, 21 , 22, 25, 28, 30, 33, 34, 35, 36, 37, 38, 39, 40, 42, 44, 45, 46, 47),
    48: (4, 6, 8, 9, 10, 11, 14, 15, 17, 18, 20, 28, 30, 32, 33, 36, 43, 44, 45)
                             }

class Movement:
    """
    This doesn't generate movements (unless Mitchell or Barometer Howell).
    Typically, it processes movements stored in movements db table.
    Actual movements can be taken from https://tedmuller.us/Bridge/Director/Movements.htm or the orange book:
    https://books.google.com.cy/books/about/Bridge_Movements.html
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
        self.barometer = (CONFIG.get("is_barometer", False)
                          or (CONFIG.get("force_barometer", False) and self.pairs < 6))

        self.bye = self.get_bye()
        self.bump = False
        self.boards_per_round = 0
        self.movement, self.initial_board_sets = self.get_movement()
        # TODO: refactor schedule generation and use it to append table/round number to tourney result
        # self.schedule = self.get_schedule()
        self._names = {}

    def __iter__(self):
        return self.movement.__iter__()

    def get_schedule(self):
        pass
        # TODO: implement

    def get_bye(self):
        if self.pairs % 2 == 0:
            return None
        elif self.mitchell:
            return self.tables
        elif self.barometer and self.pairs > 5:
            return 1
        elif CONFIG.get("no_first_pair", False):
            return 1
        elif CONFIG.get('pair_zero', False):
            return 0
        else:
            return self.pairs + 1

    def create_mitchell(self):
        """Generates mitchell and bump mitchell movements
        Bump mitchell (modified):
        odd pair has bye in round 1, then bumps one of the NS to bye
        """
        if self.tables <= 4:
            return

        regular_odd_mitchell = self.pairs % 2 == 0 and self.tables % 2 == 1 and self.boards % self.tables == 0
        regular_skip_mitchell = self.pairs % 2 == 0 and self.tables % 2 == 0 and self.boards % self.tables == 0
        bump_odd_mitchell = self.pairs % 2 == 1 and self.tables % 2 == 0 and self.boards % (self.tables - 1) == 0
        # TODO: add bump movement for skip mitchell
        bump_skip_mitchell = False#self.pairs % 2 == 1 and self.tables % 2 == 1 and self.boards % (self.tables - 2) == 0
        if bump_skip_mitchell or bump_skip_mitchell and self.tables < 6:
            return

        if regular_odd_mitchell or regular_skip_mitchell or bump_odd_mitchell or bump_skip_mitchell:
            self.mitchell = True
            self.bye = self.tables if self.pairs % 2 else 0
            self.bump = bump_skip_mitchell or bump_odd_mitchell
            if self.bump:
                self.tables -= 1
            self.skip_mitchell = bump_skip_mitchell or regular_skip_mitchell
            self.rounds = self.tables - 1 if self.skip_mitchell else self.tables
            self.boards_per_round = self.boards // self.tables

            arrow_switch = 2 / 3 * self.rounds
            odd_pair = self.tables * 2 + 2
            movement = []

            for set_index in range(self.tables):
                skipped = False
                for table_index in range(self.tables):
                    if self.skip_mitchell and not skipped and (len(movement) % self.tables - set_index) % self.tables == self.tables // 2:
                        movement.append([0, 0, 0])
                        skipped = True
                        continue
                    opp = ((2 * table_index - set_index) % self.tables
                           + self.tables + 1 + self.bump)
                    round_index = (set_index - table_index) % self.tables

                    if self.bump:
                        # TODO: these constants should be set dynamically;
                        # 2 and 3 work for odd tables, here
                        # shift = coefficient2 - coefficient1 + 1 represents how many
                        # tables up/down the odd pair goes each round.
                        # Obviously workaround_coefficient2/coefficient1 != +-1
                        # otherwise it plays the same boards/opps all the way.
                        # More, GCD(coefficient1, tables) = GCD(coefficient1, tables) = GCD(shift, tables) = 1
                        coefficient1 = 2
                        coefficient2 = 3
                        if (coefficient1 * set_index - coefficient2 * table_index) % self.tables == 0:
                            ns_pair = odd_pair
                        else:
                            ns_pair = table_index + 1
                    else:
                        ns_pair = table_index + 1
                    if self.skip_mitchell:
                        set_corrected = (set_index - (round_index > self.tables // 2)) % self.tables
                    else:
                        set_corrected = set_index
                    if round_index > arrow_switch:
                        movement.append([opp, ns_pair, set_corrected + 1])
                    else:
                        movement.append([ns_pair, opp, set_corrected + 1])
            return movement, list(range(1, self.tables + 1))
            # ODD
            # 1 - 8, 10 - 2, 12 - 3, 4 - 14, 5 - 9, 6 - 11, 7 - 13;
            # 1 - 14, 2 - 9, 11 - 3, 13 - 4, 5 - 8, 6 - 10, 7 - 12;
            # 1 - 13, 2 - 8, 3 - 10, 12 - 4, 14 - 5, 6 - 9, 7 - 11;
            # 1 - 12, 2 - 14, 3 - 9, 4 - 11, 13 - 5, 8 - 6, 7 - 10;
            # 1 - 11, 2 - 13, 3 - 8, 4 - 10, 5 - 12, 14 - 6, 9 - 7;
            # 10 - 1, 2 - 12, 3 - 14, 4 - 9, 5 - 11, 6 - 13, 8 - 7;
            # 9 - 1, 11 - 2, 3 - 13, 4 - 8, 5 - 10, 6 - 12, 7 - 14
            # EVEN
            # [[1, 7, 1], [9, 2, 1], [11, 3, 1], [0, 0, 0], [5, 9, 1], [6, 11, 1]]
            # [[1, 12, 2], [2, 8, 2], [10, 3, 2], [12, 4, 2], [0, 0, 0], [6, 10, 2]]
            # [[1, 11, 3], [2, 7, 3], [3, 9, 3], [11, 4, 3], [7, 5, 3], [0, 0, 0]]
            # [[0, 0, 0], [2, 12, 4], [3, 8, 4], [4, 10, 4], [12, 5, 4], [8, 6, 4]]
            # [[9, 1, 5], [0, 0, 0], [3, 7, 5], [4, 9, 5], [5, 11, 5], [7, 6, 5]]
            # [[8, 1, 6], [10, 2, 6], [0, 0, 0], [4, 8, 6], [5, 10, 6], [6, 12, 6]]

    def create_barometer_howell(self):
        for r in range(2, self.boards // 2 + 1):
            if self.boards % r == 0:
                rounds = self.boards // r
                if rounds > self.pairs:
                    continue
                self.rounds = rounds
                break
        movement = [(self.tables * 2, 1, 1)] + [
            (table, self.tables * 2 + 1 - table, 1) if table in BAROMETER_HOWELL_START_NS[self.tables]
            else (self.tables * 2 + 1 - table, table, 1) for table in range(2, self.tables + 1)]
        for set_index in range(1, self.rounds):
            last_round_start = self.tables * (set_index - 1)
            # last pair is static
            movement.append((self.tables * 2, movement[last_round_start + 1][0], set_index + 1))
            # Ns move up, ew move down
            for table_index in range(1, self.tables - 1):
                movement.append((
                    movement[last_round_start + table_index + 1][0],
                    movement[last_round_start + table_index - 1][1], set_index + 1))
            # last table changes direction
            movement.append((
                    movement[last_round_start + self.tables - 1][1],
                    movement[last_round_start + self.tables - 2][1], set_index + 1))
        initial_sets = list(n // self.rounds + 1 for n in range(1, self.tables + 1))
        return movement, initial_sets

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
        is_barometer = self.barometer
        if is_barometer and self.tables > 3:
            return self.create_barometer_howell()
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
                self.boards_per_round = self.boards // self.rounds

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
            # TODO: self.mitchell should be detected for any numbering
            self.mitchell = all(all(i + 1 in b[:2] for i, b in enumerate(board_data)) for board_data in raw_data)
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
                bumped = self.bump and self.pairs + 1 in r[:2] and i % self.tables == pair - 1
                if pair in r[:2] or bumped:
                    table = i % self.tables
                    position = "NS" if r[0] == pair else "EW"
                    first_board = Decimal((r[2] - 1) * boards_per_round + 1).to_integral_value(rounding=ROUND_HALF_UP)
                    last_board = Decimal(r[2] * boards_per_round).to_integral_value(rounding=ROUND_HALF_UP)
                    boards = f"{first_board}-{last_board}" if first_board != last_board else f"{first_board}"
                    opps_no = str(r[0] + r[1] - pair)
                    modulo = self.tables if self.mitchell else rounds
                    round_index = (r[2] - self.initial_board_sets[table]) % modulo
                    if bumped:
                        data[round_index] = [str(table + 1), position, self.names(self.bye), boards]
                    else:
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
        boards_per_round = self.boards_per_round
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
                                               'rounds': [None] * rounds})
                                   for i in range(1, self.tables * 2 + 1 + 2 * self.bump)],
                         'tablecards': [Dict2Class({'number': i, 'instruction_ns': None,
                                                    'instruction_ew': None,
                                                    'rounds': [None] * rounds}) for i in range(1, self.tables + 1)],
                         'roundcards': [Dict2Class({'number': i + 1, 'tables': [None] * self.tables})
                                   for i in range(rounds)]
                         }
        boards_per_round = self.boards_per_round
        if len(self.initial_board_sets) == self.tables:
            # assumes that board sets change +1, otherwise whole movement is written in initial_board_sets column
            for i, r in enumerate(self.movement):
                pair = r[0]
                table = i % self.tables
                table_data = [t for t in movement_dict['tablecards'] if t.number == table + 1][0].rounds
                try:
                    pair_data = [p for p in movement_dict['pairs'] if p.number == pair][0].rounds
                except IndexError:
                    continue
                position = "NS" if r[0] == pair else "EW"
                board_set = r[2]
                if board_set == 0:  # skip mitchell
                    board_set = self.tables
                first_board = Decimal((board_set - 1) * boards_per_round + 1).to_integral_value(rounding=ROUND_HALF_UP)
                last_board = Decimal(board_set * boards_per_round).to_integral_value(rounding=ROUND_HALF_UP)
                boards = f"{first_board}-{last_board}" if first_board != last_board else f"{first_board}"
                opps_no = str(r[0] + r[1] - pair)
                modulo = self.tables if self.mitchell else rounds
                round_index = (board_set - self.initial_board_sets[table]) % modulo
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
        return print_to_file(html_string, "Movement")

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
        boards_per_round = self.boards_per_round
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
        return print_to_file(html_string, "Table_cards")


if __name__ == "__main__":
    from config import init_config
    init_config()
    CONFIG["force_barometer"] = False
    CONFIG["is_barometer"] = False
    m = Movement(21, 8)
    board_sets = m.boards // m.boards_per_round
    print(m.initial_board_sets, m.rounds)
    for t in range(board_sets):
        print(m.movement[t * m.tables:t*m.tables + m.tables])
    print(m.pdf())
    print(m.move_card(1))
    # print(m.pdf())
    # print(m.table_cards())
