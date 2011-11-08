#!/usr/bin/env python

from urllib import FancyURLopener
import datetime
from optparse import OptionParser    
from xml.etree import ElementTree as ET


usage = '%prog [options]'
parser = OptionParser(usage=usage)
parser.add_option("-u", "--username", dest="username", help="your gmail username")
parser.add_option("-p", "--password", dest="password", help="your gmail password")
parser.add_option("-s", "--summary", action="store_true", dest="summary",
                  default=False, help="prints the summary text that is \
                                       generally visible in your gmail inbox \
                                       [default: %default]")
parser.add_option("-v", "--verbose", action="store_true", dest="summary",
                  default=False, help="same as --summary")

(options,args) = parser.parse_args()


class FancyURLopenerMod(FancyURLopener):
    """
    This overrides the default prompt_user_password, allowing for username and
    password to be passed from the command line.
    """
    def __init__(self, *args, **kwargs):
        # uncomment this once urllib uses new style classes, or in python 3.0+
        # super(FancyURLopenerMod, self).__init__(*args, **kwargs)

        # till then this will work, but not in python 3.0+
        FancyURLopener.__init__(self, *args, **kwargs)

    def prompt_user_passwd(self,host,realm):
        import getpass
        try: 
            if options.username: 
                user = options.username
            else: user = raw_input("Enter username for %s at %s: " % (realm,
                                                                      host))
            if options.password: passwd = options.password
            else: passwd = getpass.getpass("Enter password for %s in %s at %s: " %
                                           (user, realm, host))
            return user, passwd
        except KeyboardInterrupt:
            print
            return None, None

url = 'https://hvardhan.r@mail.google.com/mail/feed/atom/'
opener = FancyURLopenerMod()
f = opener.open(url)
feed = f.read()

tree = ET.fromstring(feed)

TZ = (+5,30)
negative_day = (-24,0)

# convert TZ to seconds
TZ = (TZ[0]*60 + TZ[1])*60
negative_day = (negative_day[0]*60 + negative_day[1])*60

def sanitize_datetime(datestring):
    emaildate = datestring.split('T')[0]
    emailtime = datestring.split('T')[1].split('Z')[0]
    
    datetime_str = []
    datetime_str.extend([int(x) for x in emaildate.split('-')])
    datetime_str.extend([int(x) for x in emailtime.split(':')])

    email_datetime = datetime.datetime(*datetime_str)
    timezone_correction = datetime.timedelta(0,TZ)
    email_datetime += timezone_correction

    # check date
    today = datetime.datetime.today()
    yesterday = datetime.datetime.today() + datetime.timedelta(0,negative_day)
    daybefore = datetime.datetime.today() + datetime.timedelta(0,negative_day) \
                + datetime.timedelta(0,negative_day)

    email_datetime_date = email_datetime.strftime('%F')
    today_date = today.strftime('%F')
    yesterday_date = yesterday.strftime('%F')
    daybefore_date = daybefore.strftime('%F')

    if email_datetime_date == today_date: sanitized_date = 'Today'
    elif email_datetime_date == yesterday_date: sanitized_date = 'Yesterday'
    elif email_datetime_date == daybefore_date: sanitized_date = 'Day before yesterday'
    else: sanitized_date = email_datetime_date.strftime('%B %d, %Y')

    # check time
    sanitized_time = email_datetime_time = email_datetime.strftime('%l:%M %P')

    return sanitized_date, sanitized_time


entry = "{http://purl.org/atom/ns#}entry"
fullcount = "{http://purl.org/atom/ns#}fullcount"

title = "{http://purl.org/atom/ns#}title"
summary = "{http://purl.org/atom/ns#}summary"
link = "{http://purl.org/atom/ns#}link"
modified = "{http://purl.org/atom/ns#}modified"
issued = "{http://purl.org/atom/ns#}issued"
id = "{http://purl.org/atom/ns#}id"
name = "{http://purl.org/atom/ns#}author/{http://purl.org/atom/ns#}name"
email = "{http://purl.org/atom/ns#}author/{http://purl.org/atom/ns#}email"


print

count = int(tree.find(fullcount).text)

if not count:
    print 'No new messages!\n'
    exit()

for k in tree.findall(tree[-1].tag):
    sdate, stime = sanitize_datetime(k.find(issued).text)
    print '%s at %s: %s <%s> wrote "%s"' % (sdate, stime, k.find(name).text, k.find(email).text, k.find(title).text)
    if options.summary: print '\t\tText: %s' % (k.find(summary).text)

print '\nTotal: %s unread messages\n' % count
