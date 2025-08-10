global DIRECTORS
from tourney_db import TourneyDB
from constants import CONFIG, DIRECTORS, AM


def fix_type(s):
    if s.isdigit():
        return int(s)
    try:
        return float(s)
    except ValueError:
        pass
    if s.lower() in ('true', 'false'):
        return s == 'true'
    return s


def init_config():
    if CONFIG.get("city"):
        conn = TourneyDB.connect()
        cur = conn.cursor()
        cur.execute("select key,value from config")
        db_config = {c[0]: c[1] for c in cur.fetchall()}
        conn.close()
        for k, v in db_config.items():
            if k == "directors":
                DIRECTORS.update(db_config["directors"].split(','))
            elif ':' in k:
                CONFIG[k.split(':')[0]][k.split(':')[1]] = fix_type(v)
            else:
                CONFIG[k] = fix_type(v)
    global AM
    AM = CONFIG["city"] in ("Ереван",)

init_config()
