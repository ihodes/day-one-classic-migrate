from datetime import datetime 
import os
import re
import time
import timezonefinder as tz
import pytz

tf = tz.TimezoneFinder()
utc = pytz.timezone('UTC')

from subprocess import Popen, PIPE, STDOUT

DATETIME_FMT = "%Y-%m-%d %H:%M"
BAD_DATE_CUTOFF = datetime.strptime('2016-03-19', '%Y-%m-%d')

PHOTO_RE = "!\[.*?\]\((.*?)\)"
DATE_RE = "# .*?<(.*) [a-zA-Z]{3,9} (.*)>"
LATLONG_RE = '\*@\((-?[0-9.]+),[ ]?(-?[0-9.]+)(:.*)?\)'

def photo_path_from_line(line):
    m = re.match(PHOTO_RE, line)
    if m:
        print(m.groups()[0])
        return m.groups()[0]
    else:
        raise ValueError("Can't parse photo from '{}'".format(line))

def latlong_from_line(line, date):
    """
    !!!!!!
    We need the date, as entries prior to 2016-03-19 have them flipped, 
    due to how they were exported. Hacky.
    """
    m = re.match(LATLONG_RE, line)
    if m:
        r = m.groups()
        d = datetime.strptime(date, DATETIME_FMT)
        if d > BAD_DATE_CUTOFF:
            return [r[0],r[1]]
        else:
            # need to flip it...
            return [r[1],r[0]]
    else:
        print("Trouble parsing latlong from: {}".format(line))
        return None
        # raise ValueError("Can't parse latlong from '{}'".format(line))

def date_from_line(line):
    m = re.match(DATE_RE, line)
    if m:
        r = m.groups()
        date = r[0]
        time = r[1]
        d = datetime.strptime("{} {}".format(date, time), DATETIME_FMT)
        return date + " " + time
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
                if entry.get('text') or entry.get('date'):
                    entries.append(entry)
                entry = {"text": []}
                entry['date'] = date_from_line(line)
            elif line.startswith('# Quarterly Review ') \
                or line.startswith('# [Review]') \
                or line.startswith('# [REVIEW]'):
                if entry.get('text') or entry.get('date'):
                    entries.append(entry)
                entry = {"text": []}
                entry['date'] = date_from_line(line)
                entry['tag'] = 'Review'
            elif line.startswith('!['):
                entry['photo'] = photo_path_from_line(line)
                if not entry['photo'].startswith('./photos/'):
                    entry['photo'] = "./photos/" + entry['photo']
            elif line.startswith('*@('):
                ll = latlong_from_line(line, entry['date'])
                if ll:
                    entry['latlong'] = ll
                    lat = float(entry["latlong"][0])
                    lng = float(entry["latlong"][1])
                    try:
                        entry['timezone'] = tf.timezone_at(lat=lat, lng=lng)
                    except ValueError as e: 
                        None
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
    cmd = ["dayone2", "new", "--journal={}".format(journal)]
    if entry.get("photo"):
        cmd = cmd + ["--photos", os.path.join(photo_base, entry["photo"])]
    if entry.get("latlong"):
        cmd = cmd + ["--coordinate"] + entry["latlong"]
    if entry.get('timezone'):
        timezone = entry['timezone']
        cmd = cmd + ["--time-zone={}".format(timezone)]
        d = datetime.strptime(entry['date'], DATETIME_FMT)
        t = pytz.timezone(timezone)
        offset = t.utcoffset(d)
        # d = d - offset
        date = d.strftime(DATETIME_FMT)
        cmd = cmd + ["--date='{}'".format(date)]
    else:
        cmd = cmd + ["--date='{}'".format(entry["date"])]
    if entry.get('tag'):
        # Won't work with tags with a space in them, which Day1 does accept
        # or with multiple tags in an entry
        cmd = cmd + ["--tags={}".format(entry['tag'])]
    p = Popen(cmd, shell=False, stdin=PIPE, stderr=STDOUT)
    p.communicate(input=bytes(''.join(entry["text"]), 'utf-8'))
    # Looks like some race condition in the CLI app, this helps...
    time.sleep(0.5)
    p.stdin.close()
    time.sleep(0.5)

def write_entries_to_day_one(entries, photo_base="", journal="TEST_IMPORT"):
    for entry in entries:
        write_entry_to_day_one(entry, photo_base, journal)
