from flask import Flask, render_template



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


@app.route('/result/<tournament_id>/scorecards/<pair_id>')
def scorecard(tournament_id, pair_id):
    conn = Players.connect()
    cursor = conn.cursor()
    cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
    data = cursor.fetchone()
    cursor.execute(f'select * from names where tournament_id={tournament_id} order by rank')
    names = cursor.fetchall()
    cursor.execute(f'select * from protocols where tournament_id={tournament_id} order by rank')
    protocols = cursor.fetchall()
    protocols_dict = [Dict2Class({"rank": total[3], "number": total[1], "names": total[2], "mp": total[4],
                               "percent": total[5], "masterpoints": total[6] or '', "masterpoints_ru": total[7] or ''})
                   for total in protocols]
    return render_template('scorecards_template_web.html', scoring= data[4], max=data[3], tables=data[2] // 2,
                           date=data[0], boards=data[1], tournament_title=data[-1], totals=protocols_dict,
                           tournament_id=tournament_id)


