import datetime
import logging
import pytz
from inline_key import *
from command_handlers import CommandHandlers
from file_handlers import FileHandlers
from monthly_jobs import MonthlyJobs
from match_handlers import MatchHandlers
from error_handler import error_handler

PORT = int(os.environ.get('PORT', 8080))
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
    # One city is enough for Russia
    if CONFIG.get('city') == "Пермь":
        updater.job_queue.run_monthly(MonthlyJobs.update_ranks, day=2, when=datetime.time(hour=18, minute=24,
                                                                                          tzinfo=pytz.UTC),
                                      job_kwargs={'misfire_grace_time': None})  # ensures job is run whenever it can be
    if AM:
        # RU masterpoints
        updater.job_queue.run_monthly(MonthlyJobs.update_ranks, day=2, when=datetime.time(hour=18, minute=24,
                                                                                          tzinfo=pytz.UTC),
                                      job_kwargs={'misfire_grace_time': None})
        updater.job_queue.run_daily(MonthlyJobs.masterpoints_report, time=datetime.time(hour=18, minute=24,
                                                                                    tzinfo=pytz.UTC),
                                    job_kwargs={'misfire_grace_time': None})
        # AM masterpoints
        updater.job_queue.run_daily(MonthlyJobs.update_ratings_am, time=datetime.time(hour=0, minute=0,
                                                                                      tzinfo=pytz.UTC),
                                    job_kwargs={'misfire_grace_time': None})
    # Common commands
    updater.dispatcher.add_handler(CommandHandler('donate', CommandHandlers.donate))
    updater.dispatcher.add_handler(CommandHandler('start', CommandHandlers.start))
    updater.dispatcher.add_handler(CommandHandler('help', CommandHandlers.help_command))
    updater.dispatcher.add_handler(CommandHandler('manual', CommandHandlers.manual))
    updater.dispatcher.add_handler(CommandHandler('session', CommandHandlers.start_session))
    updater.dispatcher.add_handler(CommandHandler('clear', CommandHandlers.clear_all))
    updater.dispatcher.add_handler(CommandHandler('multisession', CommandHandlers.start_multi_session))
    updater.dispatcher.add_handler(CommandHandler('switchsession', CommandHandlers.switch_session))
    updater.dispatcher.add_handler(CommandHandler('endmultisession', CommandHandlers.end_multi_session))
    updater.dispatcher.add_handler(CommandHandler('board', CommandHandlers.board))
    updater.dispatcher.add_handler(CommandHandler('names', CommandHandlers.names))
    updater.dispatcher.add_handler(CommandHandler('rounds', CommandHandlers.rounds))
    updater.dispatcher.add_handler(CommandHandler('players', CommandHandlers.players))
    updater.dispatcher.add_handler(CommandHandler('movecards', CommandHandlers.move_cards))
    updater.dispatcher.add_handler(CommandHandler('movecard', CommandHandlers.move_card))
    updater.dispatcher.add_handler(CommandHandler('tablecard', CommandHandlers.table_card))
    updater.dispatcher.add_handler(CommandHandler('tdlist', CommandHandlers.td_list))
    updater.dispatcher.add_handler(CommandHandler('loaddb', CommandHandlers.load_db))
    updater.dispatcher.add_handler(CommandHandler('rmhands', CommandHandlers.remove_board))
    updater.dispatcher.add_handler(CommandHandler('rmpair', CommandHandlers.remove_pair))
    updater.dispatcher.add_handler(CommandHandler('title', CommandHandlers.title))
    updater.dispatcher.add_handler(CommandHandler('tourneycoeff', CommandHandlers.tourney_coeff))
    updater.dispatcher.add_handler(CommandHandler('custommovement', CommandHandlers.custom_movement))
    updater.dispatcher.add_handler(CommandHandler('togglehands', CommandHandlers.toggle_hands))
    updater.dispatcher.add_handler(CommandHandler('mitchell', CommandHandlers.mitchell))
    updater.dispatcher.add_handler(CommandHandler('howell', CommandHandlers.howell))
    updater.dispatcher.add_handler(CommandHandler('barometer', CommandHandlers.barometer))
    # Match results (AM)
    updater.dispatcher.add_handler(CommandHandler('addmatch', MatchHandlers.add_match))
    updater.dispatcher.add_handler(CommandHandler('teamB', MatchHandlers.team_b))
    updater.dispatcher.add_handler(CommandHandler('matchscore', MatchHandlers.match_score))
    # RU masterpoints
    updater.dispatcher.add_handler(CommandHandler('monthlyreport', CommandHandlers.monthly_report))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex("^0\.2?5$"), CommandHandlers.tourney_coeff))
    updater.dispatcher.add_handler(CommandHandler('config', CommandHandlers.config))
    updater.dispatcher.add_handler(CommandHandler('config_update', CommandHandlers.config_update))
    # User input
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Clear"), CommandHandlers.clear_db))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Reuse names"), CommandHandlers.reuse_names))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Reuse$"), CommandHandlers.init))

    updater.dispatcher.add_handler(MessageHandler(Filters.regex("^-?\d+$"), CommandHandlers.number))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("OK"), CommandHandlers.ok))
    updater.dispatcher.add_handler(CommandHandler('restart', CommandHandlers.restart))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Cancel"), CommandHandlers.cancel))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex("^(Cross-)?(Swiss )?I?MPs$"), CommandHandlers.scoring))

    updater.dispatcher.add_handler(CallbackQueryHandler(inline_key))
    # Swiss
    updater.dispatcher.add_handler(CommandHandler('startround', CommandHandlers.start_round))
    updater.dispatcher.add_handler(CommandHandler('endround', CommandHandlers.end_round))
    updater.dispatcher.add_handler(CommandHandler('correctswiss', CommandHandlers.correct_swiss))
    updater.dispatcher.add_handler(CommandHandler('restartswiss', CommandHandlers.restart_swiss))
    # Results
    updater.dispatcher.add_handler(CommandHandler("result", result))
    updater.dispatcher.add_handler(CommandHandler("missing", CommandHandlers.missing))
    updater.dispatcher.add_handler(CommandHandler("viewboard", CommandHandlers.view_board))
    updater.dispatcher.add_handler(CommandHandler("addplayer", CommandHandlers.add_player))
    updater.dispatcher.add_handler(CommandHandler("updateplayer", CommandHandlers.update_player))
    updater.dispatcher.add_handler(CommandHandler("removeplayer", CommandHandlers.remove_player))
    updater.dispatcher.add_handler(CommandHandler("playerslist", CommandHandlers.list_players))
    updater.dispatcher.add_handler(CommandHandler("boards", CommandHandlers.get_boards_only))
    updater.dispatcher.add_handler(CommandHandler("end", CommandHandlers.end))
    updater.dispatcher.add_handler(CommandHandler("testend", CommandHandlers.testend))
    updater.dispatcher.add_handler(CommandHandler("store", CommandHandlers.store))
    updater.dispatcher.add_handler(CommandHandler("correct", CommandHandlers.correct))
    updater.dispatcher.add_handler(CommandHandler("addtd", CommandHandlers.add_td))
    updater.dispatcher.add_handler(CommandHandler('penalty', CommandHandlers.penalty))
    updater.dispatcher.add_handler(MessageHandler(Filters.document.zip, FileHandlers.upload_boards))
    updater.dispatcher.add_handler(MessageHandler(Filters.document.file_extension('rar'), FileHandlers.upload_boards))
    updater.dispatcher.add_handler(MessageHandler(Filters.document.file_extension('7z'), FileHandlers.upload_boards))
    updater.dispatcher.add_handler(MessageHandler(Filters.document.file_extension('pbn'), FileHandlers.upload_boards))
    # Debug
    updater.dispatcher.add_handler(MessageHandler(Filters.document.file_extension('db'), FileHandlers.load_db))
    # Excel
    updater.dispatcher.add_handler(CommandHandler('excel', CommandHandlers.excel))
    # Should go last
    updater.dispatcher.add_handler(MessageHandler(Filters.regex(".*"), CommandHandlers.freeform))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex(".*"), CommandHandlers.freeform))
    updater.dispatcher.add_error_handler(error_handler)

    if 'BOT_TOKEN' in os.environ:
        updater.start_webhook(listen="0.0.0.0",
                              port=int(PORT),
                              url_path=TOKEN,
                              webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
                              )
    else:
        updater.start_polling()
    # Jobs won't run unless this is fired
    updater.idle()
