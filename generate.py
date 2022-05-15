import sys
import time
import os
from constants import *

if __name__ == "__main__":
    date = sys.argv[-1] if len(sys.argv) > 1 else time.strftime("%Y-%m-%d")
    current_dir = __file__.replace("generate.py", "")
    new_dir = f"{current_dir}/{date}"
    if not os.path.exists(new_dir):
        os.mkdir(new_dir)
        link_template = "https://www.bridgebase.com/tools/handviewer.html?n=s&e=s&s=s&w=s&d={}&v={}&b={}&a=ppp"
        with open(f"{current_dir}/{date}/boards", 'w') as boards:
            content = [link_template.format("wnes"[i % 4], VULNERABILITY[i % 16], i) for i in range(1, 22)]
            boards.write("\n".join(content))

