import sys
import time
import os
import sqlite3


if __name__ == "__main__":
    date = sys.argv[-1] if len(sys.argv) > 1 else time.strftime("%Y-%m-%d")
    current_dir = __file__.replace("generate.py", "")
    new_dir = f"{current_dir}/{date}"
    if not os.path.exists(new_dir):
        os.mkdir(new_dir)
        conn = sqlite3.connect(f"{current_dir}/{date}/boards.db")
        cursor = conn.cursor()
        statement = """CREATE TABLE "boards" (
        	"number"	INTEGER,
        	"ns"	TEXT,
        	"nh"	TEXT,
        	"nd"	TEXT,
        	"nc"	TEXT,
        	"es"	TEXT,
        	"eh"	TEXT,
        	"ed"	TEXT,
        	"ec"	TEXT,
        	"ss"	TEXT,
        	"sh"	TEXT,
        	"sd"	TEXT,
        	"sc"	TEXT,
        	"ws"	TEXT,
        	"wh"	TEXT,
        	"wd"	TEXT,
        	"wc"	TEXT
        )"""
        cursor.execute(statement)
        statement = """CREATE TABLE "protocols" (
                	"number"	INTEGER,
                	"ns"	INTEGER,
                	"ew"	INTEGER,
                	"contract"	TEXT,
                	"declarer"	TEXT,
                	"lead"	TEXT,
                	"result"  TEXT,
                	"score"	INTEGER,
                	"mp_ns" INTEGER,
                	"mp_ew" INTEGER
                )"""
        cursor.execute(statement)
        statement = """CREATE TABLE "names" (
                	"number"	INTEGER,
                	"partnership"	TEXT
                )"""
        cursor.execute(statement)
        conn.commit()
        conn.close()


