import os
import shutil
import re
import subprocess
import zipfile
import py7zr
import rarfile
from telegram.ext import CallbackContext
from telegram.update import Update
from inline_key import send, current_session
from tourney_db import TourneyDB
from constants import AM, CONFIG, hands
from board import Board


class FileHandlers:
    board_re = re.compile('Board "(\d+)"]')
    holding = ['[0-9AKQJT]*']
    hand = ['\.'.join(holding * 4)]
    deal = ' '.join(hand * 4)
    deal_re = re.compile(f'Deal "([NESW]):({deal})"]')

    @staticmethod
    def upload_boards(update: Update, context: CallbackContext):
        try:
            filename = update.message.document.get_file().download()
            if zipfile.is_zipfile(filename):
                with zipfile.ZipFile(filename, 'r') as zip_object:
                    path_list = zip_object.namelist()
                    pbn = [f for f in path_list if f.endswith('.pbn')][0]
                    contents = zip_object.read(pbn).decode('utf8', 'ignore')
                if not contents:
                    send(chat_id=update.effective_chat.id, text="Cannot read pbn from zip",
                         reply_buttons=[], context=context)
            elif rarfile.is_rarfile(filename):
                rar = rarfile.RarFile(filename)
                path_list = rar.namelist()
                pbn = [f for f in path_list if f.endswith('.pbn')][0]
                contents = rar.read(pbn).decode('utf-8', 'ignore')
                if not contents:
                    send(chat_id=update.effective_chat.id, text="Cannot read pbn from rar",
                         reply_buttons=[], context=context)
            elif py7zr.is_7zfile(filename):
                archive = py7zr.SevenZipFile(filename)
                names = archive.getnames()
                pbn = [f for f in names if f.endswith('.pbn')][0]
                tempdir = 'deals'
                if not os.path.exists(tempdir):
                    os.mkdir(tempdir)
                try:
                    subprocess.check_output(f'7z e {filename} -o{tempdir} {pbn}'.split())
                    contents = open(f'{tempdir}/{os.path.basename(pbn)}', 'rb').read().decode('utf8',
                                                                                              'ignore')
                finally:
                    shutil.rmtree(tempdir)
                if not contents:
                    send(chat_id=update.effective_chat.id, text="Cannot read pbn from 7z",
                         reply_buttons=[], context=context)
            elif filename.lower().endswith('.pbn'):
                contents = open(filename, 'rb').read().decode('utf8', 'ignore')
            else:
                send(chat_id=update.effective_chat.id, text="Input file type is neither pbn nor pbn.zip",
                     reply_buttons=[], context=context)
                os.remove(filename)
                return
            if not contents:
                send(chat_id=update.effective_chat.id, text="PBN seems empty, could not upload boards",
                     reply_buttons=[], context=context)
                return
            number = 0
            uploaded = 0
            board = None
            first = 100 * current_session(context)
            for line in contents.split('\n'):
                if board_line := FileHandlers.board_re.search(line):
                    number = int(board_line.group(1)) + first
                    board = Board(number=number)
                elif number and board.number:
                    if deal := FileHandlers.deal_re.search(line):
                        board.get_board_from_pbn(deal.group(2), hands.index(deal.group(1).lower()))
                        board.save()
                        uploaded += 1
                        number = 0
                        board = None
            send(chat_id=update.effective_chat.id, text=f"Uploaded {uploaded} boards",
                 reply_buttons=['/title', 'tourney_coeff', '/names'] if AM else ['/title', '/names'], context=context)
        except Exception as e:
            send(chat_id=update.effective_chat.id, text=f"Uploading boards failed with exception: {str(e)}",
                 reply_buttons=[], context=context)
            raise
        finally:
            os.remove(filename)

    @staticmethod
    def load_db(update: Update, context: CallbackContext):
        filename = update.message.document.get_file().download()
        try:
            TourneyDB.load(filename)
            send(update.effective_chat.id, "Uploaded db file to current session", None, context)
        except Exception as e:
            send(update.effective_chat.id, f"Failed to upload db file to current session: {e}", None,
                 context)
        finally:
            os.remove(filename)
            CONFIG["load_db"] = None


if __name__ == '__main__':
    pass