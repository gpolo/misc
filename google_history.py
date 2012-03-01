# Print your Google Web History to stdout. Each stdout line
# corresponds to a XML file with a part of your history.
#
#
# Usage:
#
# python google_history.py [-u username] [-p password] [-i prev_output] > output
#
# Username and password must be entered if not specified in command line.
# If a file containing an earlier output is given, this program will
# grab your history up to the latest earlier history.
#

import sys
import codecs
from getpass import getpass
from datetime import datetime
from optparse import OptionParser

try:
    import urllib2 as urllib
    def write_bytes(s):
        sys.stdout.write(s.encode('utf8'))
except ImportError:
    from urllib import request as urllib
    def write_bytes(s):
        sys.stdout.buffer.write(s.encode('utf8'))
try:
    from elementtree import ElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET


ENCODING = 'ISO-8859-1'
BASE_URL = 'https://www.google.com/history/lookup?'
START_PAGE = BASE_URL + 'output=rss&num=%d'
MOREH_PAGE = BASE_URL + 'month=%d&day=%d&yr=%d&output=rss&num=9999'

def grab_history(username, passwd, datestop=None):
    if datestop is None:
        fetch_num = 9999
        datestop = datetime(year=1970, day=1, month=1)
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
            if cut_at == -1: # XXX
                break

            for item in items[cut_at:]:
                channel.remove(item)
            nsaved_items += cut_at - 1
            write_bytes(ET.tostring(rss).decode(ENCODING) + '\n')
            sys.stderr.write('Stopping\n')
            break

        nsaved_items += len(items)
        write_bytes(data.decode(ENCODING) + '\n')

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
    return _date_parser(raw_date)

def _rbin_search(rssitems, datestop):
    """'Reversed' binary search"""
    low = 0
    high = len(rssitems)
    while low < high:
        mid = (low + high) // 2
        item = _date_parser(rssitems[mid].find('pubDate').text)
        if datestop > item:
            high = mid
        elif datestop < item:
            low = mid + 1
        else:
            return mid
    return -1

def _date_parser(datestr):
    """date_parser specific for the expected rss output."""
    return datetime.strptime(datestr, '%a, %d %b %Y %H:%M:%S %Z')


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-u", dest="username", help="Username",
            metavar="USERNAME")
    parser.add_option("-p", dest="password", help="Password",
            metavar="PASSWORD")
    parser.add_option("-i", dest="prev_output", help="Previous output",
            metavar="FILE")

    options, args = parser.parse_args()
    if options.username is None:
        sys.stderr.write("Login: ")
        sys.stderr.flush()
        username = sys.stdin.readline().rstrip()
    else:
        username = options.username
    if options.password is None:
        try:
            passwd = getpass()
        except KeyboardInterrupt:
            raise SystemExit
    else:
        passwd = options.password
    if options.prev_output is not None:
        prev = codecs.open(options.prev_output, encoding=ENCODING)
        first_prev_date = _rss_dateindx(
                ET.fromstring(prev.readline().encode('utf8')), 0)
        prev.close()
    else:
        first_prev_date = None

    n = grab_history(username, passwd, first_prev_date)
    if n:
        sys.stderr.write("Got %d items\n" % n)
