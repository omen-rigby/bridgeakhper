import subprocess
import os
import json
from copy import deepcopy

APPS = {
    "Ереван": "bridgeakhper",
    "Воронеж": "bridgeakhper-voronezh",
    "Курск": "bridgeakhper-kursk",
    "Ижевск": "bridgeakhper-izhevsk",
    "Ессентуки": "bridgeakhper-yessentuki",
    # "Новокузнецк": "bridgeakhper-novokuznetsk",
    "Иркутск": "bridgeakhper-irkutsk",
    "Новосибирск": "bridgeakhper-novosibirsk",
    #"at Sea": "bridgeakhper-at-sea",
    "Астана": "bridgeakhper-astana"
    # "null": "bridgeakhper-mdb-aggregator",

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
        new_json["city"] = city if city != "null" else None
        new_json["tournament_title"] = f"Клубный турнир - {city}"
        with open(config_path, 'w') as g:
            g.write(json.dumps(new_json, indent=2))
        # TODO: --local-only can't find docker
        # Remote docker may have flaky issue finding ddstable
        cmd = f'flyctl deploy -a {fly_app} --force-machines'
        if city == "null":
            cmd += " --dockerfile Dockerfile.bws"
        try:
            subprocess.check_output(cmd.split())
            # flows won't work on multiple machines because data is stored in bot context
            count = 1
            subprocess.check_output(f'fly scale count 1 -a {fly_app} -y'.split())
        except Exception as e:
            print(f"{city} deployment failed with exception {str(e)}")
    else:
        with open(config_path, 'w') as g:
            g.write(json.dumps(old_json, indent=2))
        with open(constants_path, 'w') as h:
            h.write(constants)
