from command_handlers import *


class MonthlyJobs:
    @staticmethod
    def masterpoints_report(context: CallbackContext):
        send(chat_id=BITKIN_ID,
             text=Players.monthly_report(),
             reply_buttons=[], context=context)

    @staticmethod
    def update_ranks(context: CallbackContext):
        synched = Players.synch()
        send(BITKIN_ID, f"Updated ranks:\n{synched}" if synched else "Monthly ranks: No ranks updated",
             reply_buttons=[], context=context)
