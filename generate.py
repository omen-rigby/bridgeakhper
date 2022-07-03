import sys
import os
import sqlite3
from constants import db_path, date


def generate():
    date_folder = sys.argv[-1] if len(sys.argv) > 1 else date
    current_dir = __file__.replace("generate.py", "")
    new_dir = f"{current_dir}/{date_folder}"
    if not os.path.exists(new_dir):
        os.mkdir(new_dir)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        statement = """CREATE TABLE "boards" (
            	"number"	INTEGER  PRIMARY KEY,
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
                    	"number"	INTEGER  PRIMARY KEY,
                    	"partnership"	TEXT
                    )"""
        cursor.execute(statement)
        conn.commit()
        conn.close()


if __name__ == "__main__":
    generate()


