# Save your Google Web History in a sqlite database.
#
#
# Usage:
#
# First run google_history.py
# Then use this program as:
# python google_history_db.py output1 [output2 ...] > out.db
#

import sys
import codecs
import sqlite3
from datetime import datetime

try:
    from elementtree import ElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET

if sys.version_info[0] == 2:
    def write_bytes(s):
        sys.stdout.write(s.encode('utf8'))
else:
    def write_bytes(s):
        sys.stdout.buffer.write(s.encode('utf8'))

TABLENAME = "googlehistory"

def history_to_db(*history):
    conn = sqlite3.connect(":memory:",
            detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    conn.execute("""CREATE TABLE %s(
        title text, link text, date timestamp unique, category text,
        description text)""" % TABLENAME)

    unique = 0
    duplicates = 0
    for fname in history:
        with open(fname) as f:
            for line in f:
                try:
                    rss = ET.fromstring(line)
                except Exception as e:
                    print("MISSED!", line)
                    raise SystemExit
                items = rss.find('channel').findall('item')
                data = []
                for item in items:
                    title = item.find('title').text or ''
                    link = item.find('link').text or ''
                    date = _date_parser(item.find('pubDate').text)
                    category = item.find('category').text or ''
                    description = item.find('description').text or ''
                    data.append((title, link, date, category, description))

                unique_items = set([i[1] for i in data])
                duplicates += len(data) - len(unique_items)
                unique += len(unique_items)
                sys.stderr.write('Adding %d items\n' % len(unique_items))
                conn.executemany("""INSERT OR IGNORE INTO %s(
                        title, link, date, category,
                        description) VALUES (?, ?, ?, ?, ?)""" % TABLENAME,
                        data)

    for line in conn.iterdump():
        write_bytes(line + '\n')

    return unique, duplicates


def _date_parser(datestr):
    """date_parser specific for the expected rss output."""
    return datetime.strptime(datestr, '%a, %d %b %Y %H:%M:%S %Z')


if __name__ == "__main__":
    u, d = history_to_db(*sys.argv[1:])
    sys.stderr.write("Added %d items, discarded %d duplicates\n" % (u, d))
