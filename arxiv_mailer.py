import traceback
import feedparser
from HTMLParser import HTMLParser
# noinspection PyUnresolvedReferences
from email.MIMEText import MIMEText
from smtplib import SMTP
import re
import logging
import sys


def log_uncaught_exceptions(ex_cls, ex, tb):
    logging.critical(''.join(traceback.format_tb(tb)))
    logging.critical('{0}: {1}'.format(ex_cls, ex))

sys.excepthook = log_uncaught_exceptions

logging.basicConfig(
    filename='arxiv_search.log', level=logging.DEBUG,
    format="%(levelname)s : %(asctime)s : %(message)s"
)
logging.info("started arxiv search")

subject = 'quant-ph'
arxiv = 'http://arxiv.org/rss/' + subject
rss = feedparser.parse(arxiv)
logging.debug(','.join(i['title'] for i in rss['items']))

search_authors = [
    "Robert Schoelkopf","Michel Devoret", "Liang Jiang", "Steve Girvin",
    "Gerhard Kirchmair", "Hanhee Paik", "David Schuster",
    "Leonardo DiCarlo", "Andrew Houck", "Johannes Majer",
    "Adreas Walraff", "Irfan Siddiqi", "Konrad Lehnert",
    "Vladimir Manucharyan", "Flavius Schackert",
    "Blake Johnson", "Jerry Chow", "Jay Gambetta", "John Teufel",
    "Matthew Reed", "John Martinis", "Andrew Cleland",
    "Alexandre Blais", "David Cory", "Raymand Laflamme",
    "Adrian Lupascu", "Leo Kouwenhoven", "Scott Aaronson",
    "Joseph Emerson", "David Lyons"]

sender = 'lazarusnotifier@gmail.com'
passwd = ''
receiver = 'pcreinhold@gmail.com'

try:
    previously_alerted = open('arxiv_previously_alerted.txt').readlines()
    logging.info("arxiv_previously_alerted.txt found")
    logging.debug(",".join(previously_alerted))
except IOError:
    previously_alerted = []
    logging.warn("arxiv_previously_alerted.txt not found")

def strip_tags(html):
    s = HTMLStripper()
    s.feed(html)
    return s.get_data()

class HTMLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def match_name(name, text):
    first, last = name.split(' ')
    return first[0] == text[0] and last == text.split(' ')[-1]

def email_html(src, passwd, dest, text, subj):
    t = MIMEText(text, 'html')
    t['Subject'] = subj
    t['To'] = dest
    s = SMTP('smtp.gmail.com:587')
    s.starttls()
    s.login(src, passwd)
    s.sendmail(src, dest, t.as_string())
    logging.info("Sent mail to " + dest)

to_alert = []
for item in rss['items']:
    if item['id'] in previously_alerted:
        continue
    authors = map(strip_tags, item['author'].split(','))
    logging.info('authors: %s' % authors)
    if any(any(match_name(sa, a) for a in authors) for sa in search_authors):
        to_alert.append(item)

if to_alert:
    blocks = []
    for item in to_alert:
        title_str = re.split(r' \(arXiv.*\)$', item['title'])[0]
        title_html = '<h3><a href="%s">%s</a></h3>' % (item['link'], title_str)
        blocks.append('\n</br>\n'.join([title_html, item['author'], item['summary']]))

    alert_html = "\n</br>\n".join(blocks)

    email_html(sender, passwd, receiver, alert_html, 'arXiv update')

    open('_previously_alerted.txt', 'a+').writelines([i['id'] for i in to_alert])
else:
    logging.info("Nothing to alert, exiting without emailing")

logging.info("completed arxiv search")
