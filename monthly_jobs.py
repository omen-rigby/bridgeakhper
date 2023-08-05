import pytz
from command_handlers import *


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
        synched = Players.synch()
        send(BITKIN_ID, f"Updated ranks:\n{synched}" if synched else "Monthly ranks: No ranks updated",
             reply_buttons=[], context=context)


if __name__ == "__main__":
    MonthlyJobs.masterpoints_report(None)