"""Read tables from a mysqldump file into lists of dicts.

Usage: python3 dumpread.py backup.sql table [table ...]
Prints JSON {table: [row, ...]} to stdout.
"""
import json
import re
import sys

ESC = {"0": "\0", "n": "\n", "r": "\r", "t": "\t", "Z": "\x1a", "b": "\b"}


def parse_values(s):
    rows, i, n = [], 0, len(s)
    while i < n:
        if s[i] != "(":
            i += 1
            continue
        i += 1
        row, cur, inq, val_started = [], [], False, False
        while i < n:
            c = s[i]
            if inq:
                if c == "\\":
                    nxt = s[i + 1]
                    cur.append(ESC.get(nxt, nxt))
                    i += 2
                    continue
                if c == "'":
                    if i + 1 < n and s[i + 1] == "'":
                        cur.append("'")
                        i += 2
                        continue
                    inq = False
                    i += 1
                    continue
                cur.append(c)
                i += 1
                continue
            if c == "'":
                inq, val_started = True, True
                i += 1
                continue
            if c in ",)":
                v = "".join(cur)
                if not val_started:
                    v = v.strip()
                    v = None if v == "NULL" else (int(v) if re.fullmatch(r"-?\d+", v) else v)
                row.append(v)
                cur, val_started = [], False
                i += 1
                if c == ")":
                    break
                continue
            cur.append(c)
            i += 1
        rows.append(row)
    return rows


def main():
    text = open(sys.argv[1], encoding="utf8", errors="replace").read()
    out = {}
    for table in sys.argv[2:]:
        cm = re.search(r"CREATE TABLE `%s` \((.*?)\n\)" % re.escape(table), text, re.S)
        cols = re.findall(r"^\s+`([^`]+)`", cm.group(1), re.M) if cm else []
        rows = []
        for m in re.finditer(r"INSERT INTO `%s` VALUES (.*?);\n" % re.escape(table), text, re.S):
            rows += [dict(zip(cols, r)) for r in parse_values(m.group(1))]
        out[table] = rows
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
