import logging
from inline_key import *
from command_handlers import CommandHandlers
from file_handlers import FileHandlers


PORT = int(os.environ.get('PORT', 5000))
if 'BOT_TOKEN' in os.environ:
    TOKEN = os.environ["BOT_TOKEN"]
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
else:
    TOKEN = CONFIG["token"]
URL = f"https://api.telegram.org/bot{TOKEN}"
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)


if __name__ == '__main__':
    updater = Updater(token=TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', CommandHandlers.start))
    updater.dispatcher.add_handler(CommandHandler('help', CommandHandlers.help_command))
    updater.dispatcher.add_handler(CommandHandler('session', CommandHandlers.start_session))
    updater.dispatcher.add_handler(CommandHandler('board', CommandHandlers.board))
    updater.dispatcher.add_handler(CommandHandler('names', CommandHandlers.names))
    updater.dispatcher.add_handler(CommandHandler('tdlist', CommandHandlers.td_list))
    updater.dispatcher.add_handler(CommandHandler('loaddb', CommandHandlers.load_db))
    updater.dispatcher.add_handler(CommandHandler('rmboard', CommandHandlers.remove_board))
    updater.dispatcher.add_handler(CommandHandler('title', CommandHandlers.title))
    updater.dispatcher.add_handler(CommandHandler('tourneycoeff', CommandHandlers.tourney_coeff))
    updater.dispatcher.add_handler(CommandHandler('custommovement', CommandHandlers.custom_movement))
    updater.dispatcher.add_handler(CommandHandler('monthlyreport', CommandHandlers.monthly_report))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex("^0\.2?5$"), CommandHandlers.tourney_coeff))

    # User input
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Clear"), CommandHandlers.clear_db))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Reuse"), CommandHandlers.init))

    updater.dispatcher.add_handler(MessageHandler(Filters.regex("^\d+$"), CommandHandlers.number))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("OK"), CommandHandlers.ok))
    updater.dispatcher.add_handler(CommandHandler('restart', CommandHandlers.restart))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Cancel"), CommandHandlers.cancel))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex("^(Cross-)?I?MPs$"), CommandHandlers.scoring))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex("\w+ \w+ [FfMm] \d\d?(\.7)? \-?\d(\.5)?"),
                                                  CommandHandlers.add_player))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex("\w+ \d\d?(\.7)? \-?\d(\.5)?"),
                                                  CommandHandlers.update_player))

    updater.dispatcher.add_handler(CallbackQueryHandler(inline_key))
    # Results
    updater.dispatcher.add_handler(CommandHandler("result", result))
    updater.dispatcher.add_handler(CommandHandler("missing", CommandHandlers.missing))
    updater.dispatcher.add_handler(CommandHandler("viewboard", CommandHandlers.view_board))
    updater.dispatcher.add_handler(CommandHandler("addplayer", CommandHandlers.add_player))
    updater.dispatcher.add_handler(CommandHandler("updateplayer", CommandHandlers.update_player))
    updater.dispatcher.add_handler(CommandHandler("boards", CommandHandlers.get_boards_only))
    updater.dispatcher.add_handler(CommandHandler("end", CommandHandlers.end))
    updater.dispatcher.add_handler(CommandHandler("store", CommandHandlers.store))
    updater.dispatcher.add_handler(CommandHandler("correct", CommandHandlers.correct))
    updater.dispatcher.add_handler(CommandHandler("bridgematedb", CommandHandlers.bridgematedb))
    updater.dispatcher.add_handler(MessageHandler(Filters.document, FileHandlers.upload_boards))
    # Should go last
    updater.dispatcher.add_handler(MessageHandler(Filters.regex(".*"), CommandHandlers.freeform))

    if 'BOT_TOKEN' in os.environ:
        updater.start_webhook(listen="0.0.0.0",
                              port=int(PORT),
                              url_path=TOKEN,
                              webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
                              )
    else:
        updater.start_polling()

    updater.idle()
