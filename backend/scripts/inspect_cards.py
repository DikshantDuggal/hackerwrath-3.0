import os
import glob

for f in sorted(glob.glob("D:/edgerunner_datasets/cards/*_README.md")):
    name = os.path.basename(f)
    print(f"\n==================== {name} ====================")
    with open(f, "r", encoding="utf-8") as fp:
        lines = fp.readlines()
        print("".join(lines[:40]))
