#!/usr/bin/env python

from urllib import FancyURLopener
import datetime
from optparse import OptionParser    
from xml.etree import ElementTree as ET

class TooManyPasswordsError(BaseException):
    def __init__(self, message=None):
        BaseException.__init__(self, message)

class UnauthorizedAccessError(BaseException):
    def __init__(self, message=None):
        BaseException.__init__(self, message)

class FancyURLopenerMod(FancyURLopener):
    """
    This overrides the default prompt_user_password, allowing for username and
    password to be passed from the command line.
    """
    def __init__(self, *args, **kwargs):
        try: self.username = kwargs['username']
        except KeyError: self.username = None
        try: self.password = kwargs['password']
        except KeyError: self.password = None

        # once urllib uses new style classes, or in python 3.0+, use:
        # super(FancyURLopenerMod, self).__init__(*args, **kwargs)
        # till then this will work, but not in python 3.0+:
        FancyURLopener.__init__(self, *args, **kwargs)

        # only try opening the account once
        #self.authtries = 0
        #self.maxauthtries = 3

        self.flag = False

    def prompt_user_passwd(self,host,realm):
        """
        overridden method of FancyURLopener, allowing for command line arguments
        """
        if self.flag: return None, None
        self.flag = True
    
        #self.authtries += 1
        #if self.maxauthtries and self.authtries > self.maxauthtries:
        #    #TODO print a final 'giving up on %username' message
        #    return TooManyPasswordsError

        import getpass
        try: 
            if self.username is not None: user = self.username
            else: user = raw_input("Enter username for %s at %s: " % (realm, host))
            if self.password is not None: passwd = self.password
            else: passwd = getpass.getpass("Enter password for %s in %s at %s: " %
                                           (user, realm, host))
            return user, passwd
        except KeyboardInterrupt:
            print
            return None, None

class GMail(object):

    def __init__(self, timezone=(0,0)):
        self.timezone = timezone
        self.xml_tags = {
                    'entry' : "{http://purl.org/atom/ns#}entry",
                    'fullcount' : "{http://purl.org/atom/ns#}fullcount",

                    'title' : "{http://purl.org/atom/ns#}title",
                    'summary' : "{http://purl.org/atom/ns#}summary",
                    'link' : "{http://purl.org/atom/ns#}link",
                    'modified' : "{http://purl.org/atom/ns#}modified",
                    'issued' : "{http://purl.org/atom/ns#}issued",
                    'id' : "{http://purl.org/atom/ns#}id",
                    'name' : "{http://purl.org/atom/ns#}author/{http://purl.org/atom/ns#}name",
                    'email' : "{http://purl.org/atom/ns#}author/{http://purl.org/atom/ns#}email"
                    }

    def open_feed(self, username=None, password=None):
        """
        uses gmail's atom feed to retrieve a summary of the inbox, returns an XML
        element tree
        
        FancyURLopenerMod is simply urllib.FancyURLopener with a modified
        prompt_user_password in order to accept command line arguments
        """
        url = 'https://mail.google.com/mail/feed/atom/'
        opener = FancyURLopenerMod(username = username, password = password)
        f = opener.open(url)
        feed = f.read()
        f.close()
        self.tree = ET.fromstring(feed)
        if self.tree.tag == 'HTML':
            #TODO make sure that unauthorized is in the page title
            raise UnauthorizedAccessError

    def _timezone(self):
        """
        calculates the timezone offsetin seconds, and the value of 1 day in seconds
        """
        # negative_day is used later in order to check whether the email came
        # 'Today','Yesterday', or 'The day before'
        timezone_tuple = (int(self.timezone[:-2]), int(self.timezone[-2:]))
        self.TZ = (timezone_tuple[0]*60 + timezone_tuple[1])*60
        assert self.TZ == 19800
        self.negative_day = (-24)*60*60
        assert self.negative_day < 0

    def _sanitize_datetime(self, datestring):
        """
        accepts the datestring as obtained from the atom feed and returns the time
        in your timezone and the date as one of 'Today','Yesterday', 'The day
        before' or the date itself (eg. January 1, 2011)
        """
        self._timezone()

        # the date in the feed is in the format 2011-11-20T05:13:59Z
        emaildate = datestring.split('T')[0]
        emailtime = datestring.split('T')[1].split('Z')[0]
        
        datetime_str = []
        datetime_str.extend([int(x) for x in emaildate.split('-')])
        datetime_str.extend([int(x) for x in emailtime.split(':')])

        email_datetime = datetime.datetime(*datetime_str)
        timezone_correction = datetime.timedelta(0,self.TZ)
        email_datetime += timezone_correction

        # calculate today, yesterday and the day before using the seconds value of 1 day
        today = datetime.datetime.today()
        yesterday = datetime.datetime.today() \
                    + datetime.timedelta(0,self.negative_day)
        daybefore = datetime.datetime.today() \
                    + datetime.timedelta(0,self.negative_day) \
                    + datetime.timedelta(0,self.negative_day)

        # %F displays the full date as %Y-%m-%d
        email_datetime_date = email_datetime.strftime('%F')
        today_date = today.strftime('%F')
        yesterday_date = yesterday.strftime('%F')
        daybefore_date = daybefore.strftime('%F')

        if email_datetime_date == today_date: sanitized_date = 'Today'
        elif email_datetime_date == yesterday_date: sanitized_date = 'Yesterday'
        elif email_datetime_date == daybefore_date: sanitized_date = 'Day before yesterday'
        else: sanitized_date = email_datetime.strftime('%B %d, %Y')

        sanitized_time = email_datetime.strftime('%l:%M %P')
        return sanitized_date, sanitized_time

    def printmail(self, summary=False, printcount=10, printall=False):
        """
        Returns the number of emails retrieved
        """
        print '\n', self.tree.find(self.xml_tags['title']).text, '\n'

        count = int(self.tree.find(self.xml_tags['fullcount']).text)
        if not count:
            print 'No new messages!'
            return 0
        
        printcount = int(printcount)
        if printall: printcount = -1

        for n, k in enumerate(self.tree.findall(self.tree[-1].tag)):
            if printcount == 0: break
            printcount -= 1
            sdate, stime = self._sanitize_datetime(k.find(self.xml_tags['issued']).text)
            print '%s. %s at %s: %s <%s> wrote "%s"' % (n+1, sdate,stime,
                                            k.find(self.xml_tags['name']).text,
                                            k.find(self.xml_tags['email']).text,
                                            k.find(self.xml_tags['title']).text)
            if summary: print '\tText: %s' % (k.find(self.xml_tags['summary']).text)

        return count


if __name__ == '__main__':

    usage = '%prog [options] [username1] [username2] ...'
    parser = OptionParser(usage=usage)
    parser.add_option("-u", "--username", dest="username",
            help="your gmail username. use this if you also want to specify the password on the command line. otherwise simply pass the usernames as arguments")
    parser.add_option("-p", "--password", dest="password", help="your gmail password")
    parser.add_option("-t", "--timezone", dest="timezone", default="+0530", help="specify your timezone in +/-HHMM format [default: %default]")
    parser.add_option("-n", dest="printcount", default=10,
                      help="print 'n' messages")
    parser.add_option("-s", "--summary", action="store_true", dest="summary",
                      default=False, help="prints the summary text that is generally visible in your gmail inbox [default: %default]")
    parser.add_option("-a", "--all", action="store_true", dest="printall",
                      default=False, help="prints all messages in your inbox")

    (options,args) = parser.parse_args()
    
    try: int(options.printcount)
    except ValueError:
        print 'The parameter to -n needs to be a number'
        exit()

    # accounts is a list of (username, password) tuples. if username/password
    # flags are provided they are added to the list before adding username/password
    # obtained from the args list. all accounts thus obtained are worked on in one go
    accounts = []

    # verifing that username and password flags are both provided, or neither are
    if options.username or options.password:
        try:
            assert options.username
            assert options.password
        except AssertionError:
            print 'The --username flag and the --password flag MUST be used in \
                    conjunction or avoided altogether'
        else:
            accounts = [(options.username, options.password)]

    feeds = []
    passwords = []
    
    import getpass
    for username in args:
        accounts.append((username, getpass.getpass('Enter password for account %s: ' % username)))

    count = []
    for username, password in accounts:
        mailchecker = GMail(timezone=options.timezone)
        try: mailchecker.open_feed(username=username, password = password)
        except UnauthorizedAccessError:
            print 'Incorrect password for account %s, ignoring.' % username

            #TODO implement a retry mechanism for incorrect password

            #print 'Incorrect password for %s, retrying: ' % username
            #try: mailchecker.open_feed(username=username, password = getpass.getpass('Incorrect password for %s, retrying: ' % username))
            #except TooManyPasswordsError:
            #    print 'Invalid password entered too many times, giving up.'
            #else:
            #    count.append(mailchecker.printmail(options.summary, options.printcount, options.printall))
        else:
            count.append(mailchecker.printmail(options.summary, options.printcount, options.printall))

    print '\n%s%s messages recieved' % (reduce(lambda x, y: x+y, count) if count else 'No', 
            ' ( %s )' % ' + '.join([str(i) for i in count]) if len(count)>1 else '' )
