import traceback
from email.MIMEText import MIMEText
from smtplib import SMTP
import re
import logging
import sys

import time
import requests
from lxml import html


subject = 'quant-ph'
sender = 'lazarusnotifier@gmail.com'
passwd = 'electrons'
receiver = 'pcreinhold@gmail.com'
alerted_filename = 'arxiv_previously_alerted.txt'

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
    "Joseph Emerson", "David Lyons", "Rajamani Vijay", "Bob Coecke"]


def log_uncaught_exceptions(ex_cls, ex, tb):
    logging.critical(''.join(traceback.format_tb(tb)))
    logging.critical('{0}: {1}'.format(ex_cls, ex))

sys.excepthook = log_uncaught_exceptions

logging.basicConfig(
    filename='arxiv_search.log', level=logging.DEBUG,
    format="%(levelname)s : %(asctime)s : %(message)s"
)
logging.info("started arxiv search")
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

try:
    previously_alerted = open(alerted_filename, 'r').read().split('\n')
    previously_alerted = map(str.strip, previously_alerted)
    previously_alerted = filter(lambda x: x, previously_alerted)
    logging.info("%s found", alerted_filename)
    logging.info(",".join(previously_alerted))
except IOError:
    previously_alerted = []
    logging.warn("%s not found", alerted_filename)

def match_name(name, text):
    first, last = name.split(' ')
    return first[0] == text[0] and last == text.split(' ')[-1]

def send_email_html(src, passwd, dest, text, subj):
    t = MIMEText(text, 'html')
    t['Subject'] = subj
    t['To'] = dest
    s = SMTP('smtp.gmail.com:587')
    s.starttls()
    s.login(src, passwd)
    s.sendmail(src, dest, t.as_string())
    logging.info("Sent mail to " + dest)

def get_tree(url):
    page = requests.get(url)
    return html.fromstring(page.text.encode('utf-8'))

email_body = ""
new_alerts = []
tree = get_tree('http://arxiv.org/list/quant-ph/pastweek?show=200')
tree.make_links_absolute('http://arxiv.org')
atrees = tree.xpath('//div[@class="list-authors"]')
agroups = [atree.xpath('a/text()') for atree in atrees]
ids = tree.xpath('//a[@title="Abstract"]/text()')
urls = tree.xpath('//a[@title="Abstract"]/@href')
links = tree.xpath('//span[@class="list-identifier"]')
assert atrees
assert agroups
assert ids
assert urls
assert links

for authors, ident, links, url in zip(agroups, ids, links, urls):
    if ident in previously_alerted:
        logging.info("%s previously alerted, skipping", ident)
        continue
    if any(any(match_name(sa, a) for a in authors) for sa in search_authors):
        new_alerts.append(ident)
        item_tree = get_tree(url)
        blocks = item_tree.xpath('//div[@class="leftcolumn"]')[0].getchildren()[1:5]
        blocks.insert(1, links)
        email_body += "\n".join(map(html.tostring, blocks))
        time.sleep(1) # be nice...

css = "<style>%s</style>" % open("arXiv.css").read()
email_html = "<html><head>%s</head><body>%s</body></html>" % (css, email_body)

with open('arxiv_email.html', 'w') as f:
    f.write(email_html)

with open(alerted_filename, 'a') as f:
    f.write('\n'.join(new_alerts) + '\n')

if new_alerts:
    logging.info('%d new items, emailing', len(new_alerts))
    send_email_html(sender, passwd, receiver, email_html, 'arXiv update')
else:
    logging.info('No new items')

logging.info("completed arxiv search")
