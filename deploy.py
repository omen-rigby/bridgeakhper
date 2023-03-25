import subprocess
import os
import json
from copy import deepcopy

APPS = {"Ереван": "bridgeakhper",
        "Воронеж": "bridgeakhper-voronezh",
        "Курск": "bridgeakhper-kursk"
        }

config_path = os.path.abspath(__file__).replace(os.path.basename(__file__), "config.json")
constants_path = os.path.abspath(__file__).replace(os.path.basename(__file__), "constants.py")
constants = open(constants_path).read()
new_constants = deepcopy(constants)
old_db_path = constants.split('db_path = ')[1].split('\n')[0]
old_players_path = constants.split('PLAYERS_DB = ')[1].split('\n')[0]
new_constants = new_constants.replace(old_db_path, "os.environ.get('CURRENT_TOURNEY')")
new_constants = new_constants.replace(old_players_path, "os.environ.get('PLAYERS_DB')")
with open(constants_path, 'w') as g:
    g.write(new_constants)
with open(config_path) as f:
    old_json = json.loads(f.read())
    new_json = deepcopy(old_json)
    for city, fly_app in APPS.items():
        new_json["city"] = city
        new_json["tournament_title"] = f"Клубный турнир - {city}"
        with open(config_path, 'w') as g:
            g.write(json.dumps(new_json, indent=2))
        subprocess.check_output(f'flyctl deploy -a {fly_app}'.split())
    else:
        with open(config_path, 'w') as g:
            g.write(json.dumps(old_json, indent=2))
        with open(constants_path, 'w') as h:
            h.write(constants)
