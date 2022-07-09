import os
import subprocess
import tempfile
import logging
from bs4 import BeautifulSoup
from constants import date
if os.name == "nt":
    CHROME_PATH = "C:\Program Files\Google\Chrome\Application/chrome"
    # TODO: registry lookup
elif 'DYNO' in os.environ:
    CHROME_PATH = "google-chrome"
elif os.name == "posix":
    CHROME_PATH = subprocess.check_output("whereis google-chrome", shell=True).decode().split(" ")[1]


def print_to_pdf(arg, pdf_path=None):
    remove = True
    if type(arg) == str:
        htm_path = arg
        pdf_path = pdf_path or os.path.abspath(htm_path.replace('_processed.htm', '.pdf'))
        htm_path = os.path.abspath(htm_path)
    elif type(arg) == BeautifulSoup:
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".htm", dir=date) as f:
            f.write(arg.prettify())
        print(f.name)
        htm_path = os.path.abspath(f.name)
        pdf_path = os.path.abspath(pdf_path or (arg.h1.string + ".pdf"))

    cmd = f'"{CHROME_PATH}" --headless --disable-gpu --print-to-pdf="{pdf_path}" --no-margins "{htm_path}"'
    try:
        subprocess.check_output(cmd, shell=True)
        if remove:
            os.remove(htm_path)
    except:
        pdf_path = htm_path
    return pdf_path
