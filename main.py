import os
import http
from subprocess import check_output
from flask import Flask, request
from werkzeug.wrappers import Response

from tg_input import *
app = Flask(__name__)


updater = Updater(token=os.environ["TOKEN"])
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('session', start_session))
dispatcher.add_handler(CommandHandler('board', board))
dispatcher.add_handler(CommandHandler('names', names))

# User input
dispatcher.add_handler(MessageHandler(Filters.regex("^\d+$"), number))
dispatcher.add_handler(MessageHandler(Filters.text("OK"), ok))
dispatcher.add_handler(MessageHandler(Filters.text("Save"), save))
dispatcher.add_handler(MessageHandler(Filters.text("Restart"), restart))
dispatcher.add_handler(MessageHandler(Filters.text("Cancel"), cancel))
dispatcher.add_handler(MessageHandler(Filters.regex(".*MPs"), scoring))
dispatcher.add_handler(MessageHandler(Filters.regex("\w+ \w+ [FfMm] \d\d?(\.7)? \-?\d(\.5)?"), add_player))
dispatcher.add_handler(MessageHandler(Filters.regex("\w+ \d\d?(\.7)? \-?\d(\.5)?"), update_player))
dispatcher.add_handler(MessageHandler(Filters.regex(" .* "), names_text))
dispatcher.add_handler(MessageHandler(Filters.regex("\w+-\w+"), names_text))
dispatcher.add_handler(CallbackQueryHandler(inline_key))
# Results
dispatcher.add_handler(CommandHandler("result", result))
dispatcher.add_handler(CommandHandler("missing", missing))
dispatcher.add_handler(CommandHandler("viewboard", view_board))
dispatcher.add_handler(CommandHandler("addplayer", add_player))
dispatcher.add_handler(CommandHandler("updateplayer", update_player))
dispatcher.add_handler(CommandHandler("boards", get_boards_only))
dispatcher.add_handler(CommandHandler("end", end))
if 'DYNO' in os.environ:
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN,
                          webhook_url=f"https://bridgeakhper.herokuapp.com/{TOKEN}"
                          )
elif 'gcloud' in os.environ:
    updater.start_webhook(check_output("gcloud run services describe bot --format 'value(status.url)' --project ${PROJECT_ID}"))
else:
    updater.start_polling()


@app.post("/")
def index() -> Response:
    dispatcher.process_update(
        Update.de_json(request.get_json(force=True), updater))
    return "", http.HTTPStatus.NO_CONTENT
