# Print your Google Web History to stdout. Each stdout line
# corresponds to a XML file with a part of your history.
#
#
# Usage:
#
# python google_history.py [username] [password] [earlier output] > output
#
# Username and password must be entered if not specified in command line.
# If a file containing an earlier output is given, this program will
# grab your history up to the latest earlier history.

import sys
from datetime import datetime
from dateutil.parser import parse as date_parser
from getpass import getpass

try:
    import urllib2 as urllib
except ImportError:
    import urllib
try:
    from elementtree import ElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET

BASE_URL = 'https://www.google.com/history/lookup?'
START_PAGE = BASE_URL + 'output=rss&num=%d'
MOREH_PAGE = BASE_URL + 'month=%d&day=%d&yr=%d&output=rss&num=9999'

def grab_history(username, passwd, datestop=None):
    if datestop is None:
        fetch_num = 9999
        datestop = datetime.now()
    else:
        fetch_num = 1

    sys.stderr.write("Fetching %s's history\n" % (username))

    pwdmgr = urllib.HTTPPasswordMgrWithDefaultRealm()
    pwdmgr.add_password(None, START_PAGE % fetch_num, username, passwd)
    auth = urllib.HTTPBasicAuthHandler(pwdmgr)
    opener = urllib.build_opener(auth)
    urllib.install_opener(opener)

    sys.stderr.write('Reading initial feed (this may take some time).. ')
    sys.stderr.flush()
    tries = 10
    while tries:
        try:
            data = urllib.urlopen(START_PAGE % fetch_num).read()
        except urllib.HTTPError as e:
            sys.stderr.write('\n%s\n' % e)
            sys.stderr.write("No history was fetched\n")
            raise SystemExit
        except urllib.URLError:
            sys.stderr.write(' retrying..')
            sys.stderr.flush()
            tries -= 1
        else:
            break
    if not tries:
        sys.stderr.write(' :/\n')
        return None
    sys.stderr.write(' ok\n')

    nsaved_items = 0
    while True:
        rss = ET.fromstring(data) # Could store this in a database

        date = _rss_dateindx(rss, -1)
        channel = rss.find('channel')
        items = channel.findall('item')
        if datestop >= date:
            cut_at = _rbin_search(items, datestop)
            for item in items[cut_at:]:
                channel.remove(item)
            nsaved_items += cut_at - 1
            sys.stdout.write(ET.tostring(rss))
            sys.stderr.write('Stopping\n')
            break

        nsaved_items += len(items)
        sys.stdout.write(data + '\n')

        new_url = MOREH_PAGE % (date.month, date.day, date.year)
        sys.stderr.write('Reading feed starting at %d-%02d-%02d..' % (
            date.year, date.month, date.day))
        sys.stderr.flush()
        new_data = urllib.urlopen(new_url).read()
        sys.stderr.write(' ok\n')
        if data == new_data:
            sys.stderr.write('done\n')
            break
        data = new_data

    return nsaved_items


def _rss_dateindx(xmlrss, indx):
    raw_date = xmlrss.find('channel').findall('item')[indx].find('pubDate').text
    return date_parser(raw_date)

def _rbin_search(rssitems, datestop):
    """'Reversed' binary search"""
    low = 0
    high = len(rssitems)
    while low < high:
        mid = (low + high) // 2
        item = date_parser(rssitems[mid].find('pubDate').text)
        if datestop > item:
            high = mid
        elif datestop < item:
            low = mid + 1
        else:
            return mid
    return -1


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.stderr.write("Login: ")
        username = sys.stdin.readline()
    else:
        username = sys.argv[1]
    if len(sys.argv) < 3:
        try:
            passwd = getpass()
        except KeyboardInterrupt:
            raise SystemExit
    else:
        passwd = sys.argv[2]
    if len(sys.argv) == 4:
        prev = open(sys.argv[3])
        first_prev_date = _rss_dateindx(ET.fromstring(prev.readline()), 0)
        prev.close()
    else:
        first_prev_date = None

    n = grab_history(username, passwd, first_prev_date)
    if n:
        sys.stderr.write("Saved %d items\n" % n)
