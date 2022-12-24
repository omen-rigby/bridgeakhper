from flask import Flask, render_template

VULNERABILITY = ["e",
                 "-", "n", "e", "b",
                 "n", "e", "b", "-",
                 "e", "b", "-", "n",
                 "b", "-", "n"]
app = Flask(__name__)
from ..players import Players
from ..util import Dict2Class

@app.route('/result/<tournament_id>/ranks')
def ranks(tournament_id):
    conn = Players.connect()
    cursor = conn.cursor()
    cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
    data = cursor.fetchone()
    cursor.execute(f'select * from names where tournament_id={tournament_id} order by rank')
    totals = cursor.fetchall()
    totals_dict = [Dict2Class({"rank": total[3], "number": total[1], "names": total[2], "mp": total[4],
                               "percent": total[5], "masterpoints": total[6] or '', "masterpoints_ru": total[7] or ''})
                   for total in totals]
    return render_template('rankings_template_web.html', scoring= data[4], max=data[3], tables=data[2] // 2,
                           date=data[0], boards=data[1], tournament_title=data[-1], totals=totals_dict,
                           tournament_id=tournament_id)


@app.route('/result/<tournament_id>/scorecards/<pair_number>')
def scorecard(tournament_id, pair_number):
    conn = Players.connect()
    cursor = conn.cursor()
    cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
    data = cursor.fetchone()
    cursor.execute(f'select number, partnership, rank, mps, percent from names where tournament_id={tournament_id}')
    names = cursor.fetchall()
    pair_results = [n for n in names if n[0] == pair_number][0]
    cursor.execute(f'select * from protocols where tournament_id={tournament_id} and number={pair_number} order by number')
    personals = cursor.fetchall()

    scoring_short = data[4].rstrip("s").replace("Cross-", "X")
    pairs = [Dict2Class({"name": pair_results[1], "number": pair_number,
                            "mp_total": pair_results[3], "max_mp": data[3],
                            "percent_total": pair_results[4],
                            "rank": pair_results[2], "boards": []})]

    boards_per_round = [p[-1] for p in personals].count(self.personals[0][0][-1])
    for i in range(1, data[1] + 1):
        p = [pers for pers in personals if pers[2] == pair_number or pers[3] == pair_number]
        if not p:
            # not played
            continue
        p = p[0]
        position = "NS" if p[2] == pair_number else 'EW' if p[3] else ''
        index = 8 + (position == 'NS')
        mp = p[index] or 0
        mp_for_round = sum(results[r * boards_per_round + b][index] for b in range(boards_per_round))

        pairs[0].boards.append(Dict2Class({"number": p[1], "vul": VULNERABILITY[p[1]],
                                        "dir": position, "contract": p[4],
                                        "declarer": p[5], "lead": p[6],
                                        "score": p[7] if p[7] != -1 else '', "mp": mp,
                                        "percent": round(board_data[8], 2),
                                        "mp_per_round": round(mp_for_round, 2),
                                        "opp_names": opp_names}))

    return render_template('scorecards_template_web.html', scoring_short=scoring_short,
            boards_per_round=boards_per_round, pairs=pairs)


