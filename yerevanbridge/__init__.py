from flask import Flask, render_template

VULNERABILITY = ["e",
                 "-", "n", "e", "b",
                 "n", "e", "b", "-",
                 "e", "b", "-", "n",
                 "b", "-", "n"]
SUITS = "shdc"
hands = "nesw"
DENOMINATIONS = "cdhsn"

app = Flask(__name__)
from ..players import Players
from ..util import Dict2Class

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/tournaments')
def tournaments():
    conn = Players.connect()
    cursor = conn.cursor()
    cursor.execute(f'select tournament_id,date,scoring,players  from tournaments order by date desc')
    data = cursor.fetchall()

    conn.close()
    return render_template('tournaments.html', tournaments=[Dict2Class(
        {'id': d[0], 'date': d[1], 'scoring': d[2], 'players': d[3]}) for d in data])


@app.route('/rating')
def rating():
    conn = Players.connect()
    cursor = conn.cursor()
    cursor.execute(f'select full_name,rating,rank,rank_ru  from players order by rating desc')
    data = cursor.fetchall()

    conn.close()
    return render_template('rating.html', players=[Dict2Class(
        {'name': d[0], 'rating': d[1], 'rank': d[2], 'rank_ru': "" if d[3] == 1.6 else d[3]}) for d in data])



@app.route('/result/<tournament_id>/ranks')
def ranks(tournament_id):
    conn = Players.connect()
    cursor = conn.cursor()
    cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
    data = cursor.fetchone()
    cursor.execute(f"select * from names where tournament_id={tournament_id} order by regexp_replace(rank, '−.*', '', 'g')::int")
    totals = cursor.fetchall()
    totals_dict = [Dict2Class({"rank": total[3], "number": total[1], "names": total[2], "mp": total[4],
                               "percent": total[5], "masterpoints": total[6] or '', "masterpoints_ru": total[7] or ''})
                   for total in totals]
    conn.close()
    return render_template('rankings_template_web.html', scoring= data[4], max=data[3], tables=data[2] // 2,
                           date=data[0], boards=data[1], tournament_title=data[6], totals=totals_dict,
                           tournament_id=tournament_id)


@app.route('/result/<tournament_id>/scorecard/<pair_number>')
def scorecard(tournament_id, pair_number):
    tournament_id = int(tournament_id)
    pair_number = int(pair_number)
    conn = Players.connect()
    cursor = conn.cursor()
    cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
    data = cursor.fetchone()
    cursor.execute(f'select number, partnership, rank, mps, percent from names where tournament_id={tournament_id}')
    names = cursor.fetchall()
    pair_results = [n for n in names if n[0] == pair_number][0]
    cursor.execute(f'select * from protocols where tournament_id={tournament_id} and (ew={pair_number} or ns={pair_number}) order by number')
    personals = cursor.fetchall()
    max_mp = (data[2] // 2 - 1) * 2
    scoring_short = data[4].rstrip("s").replace("Cross-", "X")
    pairs = [Dict2Class({"name": pair_results[1], "number": pair_number, "scoring": data[4],
                            "mp_total": pair_results[3],
                            "percent_total": pair_results[4],
                            "rank": pair_results[2], "boards": []})]

    boards_per_round = data[1] // data[-1]
    vul = {'-': "−", "n": "NS", "e": "EW", "b": "ALL"}
    for i in range(1, data[1] + 1):
        p = [pers for pers in personals if pers[1] == i]
        if not p:
            # not played
            pairs[0].boards.append(Dict2Class({"number": i, "vul": vul[VULNERABILITY[i % 16]],
                                               "dir": "", "contract": "NOT PLAYED",
                                               "declarer": "", "lead": "",
                                               "score": '', "mp": 0,
                                               "percent": 0,
                                               "mp_per_round": 0,
                                               "opp_names": "BYE"}))
            continue
        p = p[0]
        position = "NS" if p[2] == pair_number else 'EW'
        index = 8 + (position == 'EW')
        opps = p[2 + (position != 'EW')]
        opp_names = [n for n in names if n[0] == opps][0][1]
        mp = p[index] or 0
        current_round = (i - 1) // boards_per_round

        mp_for_round = sum(res[index] for res in personals
                           if current_round * boards_per_round < res[1] <= (current_round + 1) * boards_per_round)

        pairs[0].boards.append(Dict2Class({"number": i, "vul": vul[VULNERABILITY[i % 16]],
                                           "dir": position, "contract": p[4],
                                           "declarer": p[5], "lead": p[6],
                                           "score": p[7] if p[7] != 1 else '', "mp": mp,
                                           "percent": round(mp/max_mp, 2),
                                           "mp_per_round": round(mp_for_round, 2),
                                           "opp_names": opp_names}))
    conn.close()
    return render_template('scorecards_template_web.html', scoring_short=scoring_short, max_mp=data[3],
                           boards_per_round=boards_per_round, pairs=pairs, tournament_id=tournament_id)


@app.route('/result/<tournament_id>/board/<board_number>')
def board(tournament_id, board_number):
    tournament_id = int(tournament_id)
    board_number = int(board_number)
    conn = Players.connect()
    cursor = conn.cursor()
    cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
    data = cursor.fetchone()
    cursor.execute(f'select number, partnership from names where tournament_id={tournament_id}')
    names = cursor.fetchall()
    cursor.execute(f'select * from protocols where tournament_id={tournament_id} and number={board_number} order by mp_ns desc')
    personals = cursor.fetchall()

    cursor.execute(f'select * from boards where tournament_id={tournament_id} and number={board_number}')
    board_data = cursor.fetchone()
    scoring_short = data[4].rstrip("s").replace("Cross-", "X")
    vul = {'-': "−", "n": "NS", "e": "EW", "b": "ALL"}

    repl_dict = {"d": hands[board_number % 4].upper(), "b": board_number, "v": vul[VULNERABILITY[board_number % 16]],
                 "minimax_contract": board_data[38], "minimax_outcome": board_data[39], "minimax_url": board_data[40]}
    for i, h in enumerate(hands):
        for j, s in enumerate(SUITS):
            print(i  * 4 + j)
            repl_dict[f"{h}{s}"] = board_data[2 + i * 4 + j].upper().replace("T", "10")
        for j, d in enumerate(reversed(DENOMINATIONS)):
            repl_dict[f"{h}_par_{d}"] = board_data[18+i*5+j]
    dealer_low = repl_dict["d"].lower()
    repl_dict["ns_vul"] = (repl_dict["v"] in ("EW", "−")) * "non" + "vul"
    repl_dict["ew_vul"] = (repl_dict["v"] in ("NS", "−")) * "non" + "vul"
    repl_dict[f"{dealer_low}_dealer"] = "dealer"
    repl_dict["tables"] = []

    current_board = Dict2Class(repl_dict)
    for p in personals:
        repl_dict = {"ns": p[2], "ew": p[3], "contract": p[4], "declarer": p[5], "lead": p[6],
                     "nsplus": p[7] if p[7] > 1 else "", "nsminus": -p[7] if p[7] < 0 else "", "mp_ns": round(p[8], 2),
                     "mp_ew": round(p[9], 2), "ns_name": [n[1] for n in names if n[0] == p[2]][0],
                     "ew_name": [n[1] for n in names if n[0] == p[3]][0], "bbo_url": p[10]}
        current_board.tables.append(Dict2Class(repl_dict))

    conn.close()
    return render_template('travellers_template_web.html', scoring_short=scoring_short, board=current_board,
                           tournament_id=tournament_id, maxboard=data[1])


