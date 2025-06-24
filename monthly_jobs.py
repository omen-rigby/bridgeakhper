import pytz
from command_handlers import *

# RANK_EDGE_VALUES = {0: 0, 100: 0.7, 300: 2.5, 150: '2.5*', 300: '4*', 600: 4, 1000: 6, 2000: 10, 3000: 14}
FAST_RANK_EDGE_VALUES = {40: 0.7, 100: 1.5, 150: 2.5, 300: 4}


class MonthlyJobs:
    @staticmethod
    def masterpoints_report(context: CallbackContext):
        today = datetime.datetime.now(pytz.UTC)
        if today.weekday() == 6 and (today + datetime.timedelta(days=7)).month != today.month:
            send(chat_id=BITKIN_ID,
                 text=Players.monthly_report(),
                 reply_buttons=[], context=context)

    @staticmethod
    def update_ranks(context: CallbackContext):
        Players.find_ru_ids()
        synched = Players.synch()
        global ALL_PLAYERS
        ALL_PLAYERS = Players.get_players()
        send(BITKIN_ID, f"Updated ranks:\n{synched}" if synched else "Monthly ranks: No ranks updated",
             reply_buttons=[], context=context)

    @staticmethod
    def update_ratings_am(context: CallbackContext=None):
        if not AM:
            return
        conn = Players.connect()
        cursor = conn.cursor()
        cursor.execute('select TRIM(full_name), rating, last_year, rank, is_rank_temporary, is_rank_reduced from players')
        players = cursor.fetchall()
        cursor.execute("""select partnership, masterpoints from names left join tournaments 
                          on names.tournament_id = tournaments.tournament_id
                          where "date" = current_date - 1 and masterpoints > 0""")
        recent_tournaments = cursor.fetchall()
        dict_update = {}
        for (pair, masterpoints) in recent_tournaments:
            for player in pair.split(' & '):
                if player in dict_update:
                    dict_update[player] += masterpoints
                else:
                    dict_update[player] = masterpoints
        for player, masterpoints_to_add in dict_update.items():
            try:
                player_record = [p for p in players if p[0].strip() == player.strip()][0]
            except IndexError:
                if context:
                    context.bot.send_message(BITKIN_ID, f"No player found in DB for {player}")
                continue
            rating = player_record[1] + masterpoints_to_add
            year = player_record[2] + masterpoints_to_add
            cursor.execute(f"update players set rating={rating}, last_year={year} where TRIM(full_name)='{player}'")
            if context:
                context.bot.send_message(BITKIN_ID, f"{player} total {player_record[1]} + {masterpoints_to_add}, "
                                                f"year {player_record[2]} + {masterpoints_to_add}")
        # Update ranks
        # TODO: implement
        # for player in players:
        #     expected = RANK_EDGE_VALUES[max(k for k in RANK_EDGE_VALUES.keys() if player[1] >= k)]
        #     is_rank_temporary = False
        #     if isinstance(expected, str) and '*' in expected:
        #         expected = float(expected.strip('*'))
        #         is_rank_temporary = True
        #     if player[-2] < expected:
        #         cursor.execute(
        #             f"update players set rank={expected}, is_rank_temporary={is_rank_temporary} "
        #             f"where TRIM(full_name)='{player[0]}'")
        conn.commit()
        conn.close()


if __name__ == "__main__":
    print(MonthlyJobs.update_ratings_am())