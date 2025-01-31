import os
import subprocess
import tempfile
import logging
import pdfkit
from bs4 import BeautifulSoup
from pyvirtualdisplay import Display

try:
    PDFKIT_PRESENT = ' ' in subprocess.check_output("whereis wkhtmltopdf", shell=True).decode()
except:
    PDFKIT_PRESENT = False
if not PDFKIT_PRESENT:
    if os.name == "nt":
        CHROME_PATH = "C:\Program Files\Google\Chrome\Application/chrome"
        # TODO: registry lookup
    elif os.name == "posix":
        try:
            CHROME_PATH = subprocess.check_output("whereis google-chrome", shell=True).decode().split(" ")[1]
        except IndexError:
            CHROME_PATH = ""


def print_to_file(arg, pdf, name=None):
    if type(arg) == str and os.path.exists(arg):
        htm_path = arg
        htm_path = os.path.abspath(htm_path)
    elif type(arg) == str:
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".htm") as f:
            f.write(arg)
        htm_path = os.path.abspath(f.name)
    elif type(arg) == BeautifulSoup:
        with tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=".htm") as f:
            f.write(arg.prettify(encoding='UTF-8'))
        htm_path = os.path.abspath(f.name)
    if pdf:
        return print_to_pdf(htm_path, f'{name}.pdf')
    if name:
        new_path = os.path.join(os.path.dirname(htm_path), f'{name}.htm')
        os.rename(htm_path, new_path)
        return new_path
    return htm_path


def print_to_pdf(htm_path, pdf_path, landscape=False):
    remove = True
    if PDFKIT_PRESENT:
        with Display():
            pdfkit.from_file(htm_path, pdf_path, options={
                'encoding': 'utf-8',
                'orientation': 'landscape' if landscape else 'portrait',
                'page-size': 'A4',
                'margin-top': '0mm', 'margin-bottom': '0mm', 'margin-left': '0mm', 'margin-right': '0mm'
            })
            if remove:
                os.remove(htm_path)
    else:
        cmd = f'"{CHROME_PATH}" --headless --disable-gpu --no-sandbox --print-to-pdf="{pdf_path}" --no-margins "{htm_path}"'
        try:
            subprocess.check_output(cmd, shell=True)
            if remove:
                os.remove(htm_path)
        except:
            pdf_path = htm_path
    return pdf_path
