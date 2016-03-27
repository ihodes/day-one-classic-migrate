import xml.etree.ElementTree as et
import collections
import os
import re
import datetime, time


TEMPLATE = u"""# {date}{location}{photo}
{entry}\n\n\n"""
REVIEW_TEMPLATE = u"""# [Review] {date}{location}{photo}
{entry}\n\n\n"""

def parse_date(datestring):
    """Returns a datetime object from the given DayOne-formatted date string."""
    return datetime.datetime.strptime(datestring, '%Y-%m-%dT%H:%M:%SZ')

def dict_from_xml_tree(xml):
    previous_was_key = False
    previous_key = None
    keyvals = {}
    for item in xml:
        if item.tag == 'key':
            previous_was_key = True
            previous_key = item.text
        elif item.tag == 'dict':
            if previous_was_key:
                keyvals[previous_key] = dict_from_xml_tree(list(item.iter())[1:])
                previous_was_key = False
        elif item.tag == 'array':
            if previous_was_key:
                items = list(item.iter())[1:]
                keyvals[previous_key] = [i.text for i in items]
                previous_was_key = False
        else:
            if previous_was_key:
                keyvals[previous_key] = item.text
                previous_was_key = False
    return keyvals

def journal_entry_from_day_one_file(path, day_one_photos, photos_path):
    """Return a dict representing a DayOne journal entry from the given path.

    day_one_photos is a list of photo filenames; it's used to see if the entry
    has an associated photo. If it does, it's added to the resulting dict as
    entry 'photo'.

    photos_path is the path to the directory that the photos can be found
    in. Used so that the 'photo' value is an absolute path, or relative
    where these markdown files will reside.
    """
    e = et.parse(path).getroot()
    items = list(e.find("dict").iter())[1:]
    dct = dict_from_xml_tree(items)
    uuid = dct['UUID']
    jpg_filename = uuid + '.jpg'
    if jpg_filename in day_one_photos:
        dct['photo'] = photos_path + jpg_filename
    return dct

def get_filename_for_entry(entry):
    """Return the filename the given entry should be written to."""
    date = entry['Creation Date']
    date = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
    return date.strftime('%Y-%m') + '.md'

def sort_entries(entries):
    """Given a list of entries, sort them by the creation date, in ascending
order."""
    def unix_time(e):
        d = parse_date(e['Creation Date']).timetuple()
        return time.mktime(d)
    return sorted(entries, key=unix_time)

def format_entry(entry):
    """Return a string containing the entry in my desired format."""
    text = entry['Entry Text']
    # Since we have all our entries under a # header by day, we want to make
    # sure there are no confusing h1s below it in the entry.
    if text is not None:
        text = re.sub(r'^(#+) ', r'#\1 ', text, flags=re.MULTILINE)

    location = ''
    if 'Location' in entry:
        longitude = entry['Location']['Longitude']
        latitude = entry['Location']['Latitude']
        name = entry['Location'].get('Place Name')
        if name:
            location = u'\n*@({},{}: {})*\n'.format(longitude, latitude, name)
        else:
            location = u'\n*@({},{})*\n'.format(longitude, latitude)

    photo = ''
    if 'photo' in entry:
        photo = '\n![]({})\n'.format(entry['photo'])

    date = entry['Creation Date']
    date = parse_date(date)
    date = date.strftime('%Y-%m-%d %a %H:%M')
    datestring = '<{}>'.format(date)

    tags = entry.get('Tags')
    if tags and 'Review' in tags:
        return REVIEW_TEMPLATE.format(
            date=datestring,
            location=location,
            photo=photo,
            entry=text)
    return TEMPLATE.format(
                date=datestring,
                location=location,
                photo=photo,
                entry=text)


if __name__ == '__main__':
    journalfile = '/Users/isaachodes/Dropbox/Apps/Journal.dayone.final.backup/'
    entries = journalfile + 'entries/'
    photos_path = journalfile + 'photos/'

    day_one_entries = os.listdir(entries)
    day_one_photos = os.listdir(photos_path)  # all PNGs

    # Here we make a list of entries by month (well, filename == YYYY-MM.md)
    monthly_entries = collections.defaultdict(list)
    for path in day_one_entries:
        skip = False
        fullpath = entries + path
        entry = journal_entry_from_day_one_file(
            fullpath, day_one_photos, './photos/')
        if entry.get('Tags') is not None:
            if 'Workout' in entry['Tags']:
                skip = True
        filename = get_filename_for_entry(entry)
        if not skip:
            monthly_entries[filename].append(entry)

    sorted_entries = {}
    for month, entries in monthly_entries.iteritems():
        sorted_entries[month] = sort_entries(entries)

    # Here we write them all out
    for filename, entries in sorted_entries.iteritems():
        with open(filename, 'wb') as f:
            for entry in entries:
                entry_text = format_entry(entry)
                f.write(entry_text.encode("UTF-8"))
