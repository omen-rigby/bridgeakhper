import os
import re
import sys
import subprocess
import sqlite3
from deal import Deal
from tg_input import db_path
from print import *


def collect(folder):
    for root, _, files in os.walk(folder):
        yield from [f"{root}/{f}" for f in files]



global boards
boards = []


def get_board_html(url, template):

    url = url.lower()
    data = {q.split("=")[0]: q.split("=")[1].lower() for q in url.split("?")[1].split("&")}
    # parse hands to suits
    suit_data = {}
    for k, v in data.items():
        if k in "nsew":
            v = data[k]
            for suit in "cdhs":
                suit_data[f"{k}{suit}"] = (v.split(suit)[1].replace("t", "10") or '--') if suit in v else '--'
                v = v.split(suit)[0]
    data.update(suit_data)
    data["v"] = {"-": "-", "n": "NS", "e": "EW", "b": "ALL"}[data["v"]]
    # Dealer and vul improvements
    data["nscolor"] = "palegreen" if data["v"] in ("EW", "-") else "tomato"
    data["ewcolor"] = "palegreen" if data["v"] in ("NS", "-") else "tomato"

    # getting board
    board_html = template
    for var in data.keys():
        board_html = board_html.replace("${" + var + "}", data[var].upper())
    dealer = data["d"].upper()
    board_html = board_html.replace(f'>{dealer}<', f'style="text-decoration:underline;"><b>{dealer}</b><')
    # get minimax
    # TODO: add
    # ddstable.get_ddstable()
    return board_html


def get_boards(folder):
    # for url in open(f"{folder}/boards").read().split("\n"):
    #     if url:
    #         boards.append(Deal(url))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"Select * from boards")
    for i in range(len(cursor.fetchall())):
        boards.append(Deal(number=i + 1))
    conn.close()


def replace(file):
    old_string = file.read()
    old_string = old_string.replace('iso-8859-1', 'cp1251')
    if "Travellers" in file.name:
        old_string = re.sub('<TABLE\s+style="BORDER-TOP: 0px;',
                            '<TABLE style="page-break-inside: avoid;BORDER-TOP: 0px;', old_string)
        styles = """
@media print {
    @page { margin: 0mm 0mm 0mm 0mm; size: landscape; }
    @bottom-right-corner { ... /* empty footer */ } }
}
H1 {
FONT-SIZE: 20pt; FONT-FAMILY: Arial; FONT-WEIGHT: bold; COLOR: #000000; TEXT-ALIGN: center
}
H2 {
FONT-SIZE: 16pt; FONT-FAMILY: Arial; FONT-WEIGHT: bold; COLOR: #0000a0; TEXT-ALIGN: center
}
table.deal, table.deal td, .minimax {
border: none;
font-family: Verdana;
font-size: 13px;
}


table.deal th{
font-family: Verdana;
font-size: 13px;
border: 1px solid #0C479D;
border-collapse: separate;
background:#ddffdd;
border-radius: 4px;
}

.brd{
border: 1px solid #0C479D;
border-collapse: collapse;
}"""
        old_string = re.sub("<STYLE type=Text/css>.*</STYLE>",
                            f"<STYLE type=Text/css>{styles}</STYLE>", old_string, flags=re.DOTALL).replace("*", "")
        old_string = old_string\
            .replace("<HEAD>", "<HEAD>\n<script>function openUrl(url){window.open(url, '_blank').focus();</script>")
        tables = old_string.split('<TH width="100%" colSpan=13>Board')

        new_tables = [tables[0]]
        contract_re = re.compile(
            '<TD align=center>(\d+)</TD>\n(\s+)<TD align=center>(\d+)</TD>\n\s+<TD align=center>(\d)([SHDCN])([^<]+)</TD>'
            '\n\s+<TD align=center>(\w)</TD>',
            flags=re.MULTILINE)
        for i in range(1, len(tables)):
            table = tables[i]
            for match in contract_re.findall(table):
                ns, spaces, ew, level, denomination, stuff, declarer = (match[i] for i in range(7))
                link_repl = boards[i-1].url_with_contract(level, denomination, declarer)
                table = table.replace(
                    f'<TD align=center>{ns}</TD>\n{spaces}<TD align=center>{ew}</TD>\n{spaces}<TD align=center>'
                    f'{level}{denomination}{stuff}</TD>\n{spaces}<TD align=center>{declarer}</TD>',
                    f'<TD align=center>{ns}</TD>\n{spaces}<TD align=center>{ew}</TD>\n{spaces}<TD align=center>'
                    f'<a target="_blank" href="{link_repl}">{level}{denomination}{stuff}</a></TD>'
                    f'\n{spaces}<TD align=center>{declarer}</TD>',
                )
            new_tables.append(table)
        old_string = '<TH width="100%" colSpan=13>Board'.join(new_tables)
        board_previous = '<TD vAlign=top width="33.33%">'
        board_next = board_previous.replace("33.33", "75")
        new_separator = board_previous.replace('>', ' class="brd">').replace("33.33", "25")
        lines = old_string.split(board_previous)
        for i in range(1, len(lines)):
            deal = boards[i-1].board_html
            analysis = boards[i-1].analysis_html
            lines[i] = f"{deal}{analysis}</TD>{board_next}{lines[i]}"
        old_string = new_separator.join(lines)

    else:
        old_string = old_string.replace("<STYLE type=Text/css>", '''<STYLE type=Text/css>@media print {
    @page { margin: 0mm 0mm 0mm 0mm; size: landscape; }
    @bottom-right-corner { ... } }
}''')
    if "ScoreCards" in file.name:
        old_string = re.sub(",\d\d", "", old_string)
    if "Ranks" in file.name:
        old_string = old_string.replace(" [OVERALL]", "")\
            .replace('<META name=GENERATOR content="MSHTML 11.00.10570.1001">', '')

    old_string = old_string.replace('<H2>Session 1 Section A</H2>', '')
    old_string = re.sub('<H2>Neuberg.*</H2>', "", old_string)
    old_string = re.sub("<H2>.*printed.*</H2>", "", old_string)
    old_string = old_string.replace("/Round", "MPs per round").replace("*", "")
    return_value = old_string.replace('<TABLE style="FONT-SIZE: 10pt; FONT-FAMILY: Arial',
                                      '<TABLE style="FONT-SIZE: 10pt; FONT-FAMILY: Arial;page-break-after: always;')
    return return_value


if __name__ == "__main__":
    date = sys.argv[-1] if len(sys.argv) > 1 else "2022-05-08"
    get_boards(date)
    #sys.exit(0)
    for file in collect(date):
        if "processed" in file or ".htm" not in file:
            continue
        out_path = file.replace(".", "_processed.")
        with open(file, "r") as inp:
            with open(out_path, "w") as out:
                out_string = replace(inp)
                # if "Ranks" in file:
                #     print(out_string)
                out.write(out_string)

                print_to_pdf(out_path)
