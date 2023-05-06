global DIRECTORS
from tourney_db import TourneyDB
from constants import CONFIG, DIRECTORS


def init_config():
    conn = TourneyDB.connect()
    cur = conn.cursor()
    cur.execute("select key,value from config")
    db_config = {c[0]: c[1] for c in cur.fetchall()}
    conn.close()
    if CONFIG.get("city"):
        for k, v in db_config.items():
            if k == "directors":
                DIRECTORS.update(db_config["directors"].split(','))
            elif ':' in k:
                CONFIG[k.split(':')[0]][k.split(':')[1]] = int(v) if v.isdigit() else v
            else:
                CONFIG[k] = int(v) if v.isdigit() else v


init_config()
