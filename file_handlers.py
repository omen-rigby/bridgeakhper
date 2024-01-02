import zipfile
from command_handlers import *
from sim_handlers import SimHandlers
import rarfile


class FileHandlers:
    board_re = re.compile('\[Board "(\d+)"\]')
    holding = ['[0-9AKQJT]*']
    hand = ['\.'.join(holding * 4)]
    deal = ' '.join(hand * 4)
    deal_re = re.compile(f'\[Deal "([NESW]):({deal})"\]')

    @staticmethod
    @command_eligibility
    def upload_boards(update: Update, context: CallbackContext):
        filename = update.message.document.get_file().download()
        if zipfile.is_zipfile(filename):
            with zipfile.ZipFile(filename, 'r') as zip_object:
                path_list = zip_object.namelist()
                pbn = [f for f in path_list if f.endswith('.pbn')][0]
                contents = zip_object.read(pbn).decode()
        elif rarfile.is_rarfile(filename):
            rar = rarfile.RarFile(filename)
            path_list = rar.namelist()
            pbn = [f for f in path_list if f.endswith('.pbn')][0]
            contents = rar.read(pbn).decode()
        elif filename.lower().endswith('.pbn'):
            contents = open(filename).read()
        else:
            send(chat_id=update.effective_chat.id, text="Input file type is neither pbn nor pbn.zip",
                 reply_buttons=[], context=context)
            os.remove(filename)
            return
        number = 0
        for line in contents.split('\n'):
            board_line = FileHandlers.board_re.match(line)
            if board_line:
                number = board_line.group(1)
                board = Board(number=number)
            elif number and board.number:
                deal = FileHandlers.deal_re.match(line)
                if deal:
                    board.get_board_from_pbn(deal.group(2), hands.index(deal.group(1).lower()))
                    board.save()
        send(chat_id=update.effective_chat.id, text=f"Uploaded {number} boards",
             reply_buttons=[], context=context)
        os.remove(filename)

    @staticmethod
    def load_db(update: Update, context: CallbackContext):
        if CONFIG['city']:
            filename = update.message.document.get_file().download()
            try:
                TourneyDB.load(filename)
                send(update.effective_chat.id, "Uploaded db file to current session", None, context)
            except Exception as e:
                send(update.effective_chat.id, f"Failed to upload db file to current session: {e}", None, context)
            finally:
                os.remove(filename)
                CONFIG["load_db"] = None
        else:
            SimHandlers.upload_sqlite(update, context)


if __name__ == '__main__':
    number = 0
    contents = open('/home/ibitkin/Downloads/2404.pbn').read()
    for line in contents.split('\n'):
        board_line = FileHandlers.board_re.match(line)
        if board_line:
            number = board_line.group(1)
            board = Board(number=int(number))
        elif number and int(board.number) > 0:
            deal = FileHandlers.deal_re.match(line)
            if deal:
                board.get_board_from_pbn(deal.group(2), hands.index(deal.group(1).lower()))
                board.save()
