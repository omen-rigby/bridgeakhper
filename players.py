import sqlite3


if __name__ == "__main__":
    current_dir = __file__.replace("generate.py", "")
    conn = sqlite3.connect(f"{current_dir}/players.db")
    cursor = conn.cursor()
    statement = """CREATE TABLE "players" (
        "first_name"	TEXT,
        "last_name"   	TEXT,
        "rank"	        TEXT,
        "gender"	    TEXT,
        "full_name" 	TEXT
    )"""
    cursor.execute(statement)
    conn.commit()
    conn.close()


