from pathlib import Path
from loader import load_local_file

DIR_PATH = r"C:\HUR\Document"

folder = Path(DIR_PATH)

count = 5

for file in folder.rglob("*.md"):
    print(file)
    print(load_local_file(file))

    if count >= 0:
        count -= 1
        continue
    break