import os
import re

from subprocess import Popen, PIPE, STDOUT

PHOTO_RE = "!\[.*?\]\((.*?)\)"
DATE_RE = "# <(.*) [a-zA-Z]{3,9} (.*)>"
LATLONG_RE = '\*@\((-?[0-9.]+),[ ]?(-?[0-9.]+)(:.*)?\)'

def photo_path_from_line(line):
    m = re.match(PHOTO_RE, line)
    if m:
        return m.groups()[0]
    else:
        raise ValueError("Can't parse photo from '{}'".format(line))

def latlong_from_line(line):
    m = re.match(LATLONG_RE, line)
    if m:
        r = m.groups()
        return [r[1],r[0]]
    else:
        #raise ValueError("Can't parse latlong from '{}'".format(line))
        return None

def date_from_line(line):
    m = re.match(DATE_RE, line)
    if m:
        r = m.groups()
        return r[0] + " " + r[1]
    else:
        raise ValueError("Can't parse date from '{}'".format(line))

def read_journal_file(path):
    """Read the markdown formatted journal file in and parse it into a
    Python datastructure
    """
    with open(path, 'r') as file:
        entry = {"text": []}
        entries = []
        for line in file.readlines():
            if line.startswith('# <2'):
                entries.append(entry)
                entry = {"text": []}
                entry['date'] = date_from_line(line)
            elif line.startswith('![]('):
                entry['photo'] = photo_path_from_line(line)
            elif line.startswith('*@('):
                entry['latlong'] = latlong_from_line(line)
            else:
                entry['text'].append(line)
        entries.append(entry)
    return entries

def read_journal(dir):
    entries = []
    for path in os.listdir(dir):
        if path.endswith(".md"):
            entries = entries + read_journal_file(path)
    return entries

def write_entry_to_day_one(entry, photo_base, journal):
    if not entry.get("date"):
        return None
    cmd = ["dayone2", "new", "--journal={}".format(journal),\
           "--date='{}'".format(entry["date"])]
    if entry.get("photo"):
        cmd = cmd + ["--photos", os.path.join(photo_base, entry["photo"])]
    if entry.get("latlong"):
        cmd = cmd + ["--coordinate"] + entry["latlong"]
    p = Popen(cmd, shell=False, stdin=PIPE, stderr=STDOUT)
    p.communicate(input=bytes(''.join(entry["text"]), 'utf-8'))
    p.stdin.close()

def write_entries_to_day_one(entries, photo_base="", journal="TEST_IMPORT"):
    for entry in entries:
        write_entry_to_day_one(entry, photo_base, journal)
