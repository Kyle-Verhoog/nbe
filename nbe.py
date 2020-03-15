import email
import imaplib
import re
from urllib.request import urlopen
import os
import smtplib, ssl, sqlite3
import time

from bs4 import BeautifulSoup as bs
import requests


conn = sqlite3.connect("db.sqlite3")
cur = conn.cursor()
cur.execute("""
create table if not exists users (email text);
""")


class RequiredEnv:
    def __init__(self, prefix=None):
        self.missing_required_keys = []
        self._prefix = prefix

    def __enter__(self):
        return self

    def getkey(self, key):
        return f"{self._prefix}{key}"

    def getenv(self, key, default=None, required=False):
        act_key = self.getkey(key)
        if required and act_key not in os.environ:
            self.missing_required_keys.append(key)
        return os.getenv(f"{act_key}", default)

    def __exit__(self, type, value, traceback):
        if self.missing_required_keys:
            import sys
            sys.tracebacklimit = 0
            raise Exception("\n".join([f"'{self.getkey(key)}' required setting not provided" for key in self.missing_required_keys]))


with RequiredEnv(prefix="SMTP_") as settings:
    SMTP_PORT = settings.getenv("PORT", 465)
    SMTP_URL = settings.getenv("URL", "smtp.gmail.com")
    SMTP_USER = settings.getenv("USER", required=True)
    SMTP_PASS = settings.getenv("PASS", required=True)


def render_verses(verses):
    # TODO: handle multiple chapters
    verse_html = ""

    for v in verses["verses"]:
        verse_html += f"<sup>{v['verse']}</sup>{v['text']}"

    return f"""
    <div>
        <h2>{verses['reference']}</h2>
        {verse_html}
    </div>
    """

def update_recipients():
    addrs = set()
    cur.execute("select * from users")
    for row in cur.fetchall():
        addr, = row
        addrs.add(addr)

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(SMTP_USER, SMTP_PASS)
    mail.select("inbox")
    status, data = mail.search(None, "ALL")
    mail_ids = []
    for block in data:
        mail_ids += block.split()

    # mail should be chronologically sorted?
    for i in mail_ids:
        status, data = mail.fetch(i, "(RFC822)")

        for response_part in data:
            if isinstance(response_part, tuple):
                message = email.message_from_bytes(response_part[1])

                mail_from = message['from']
                from_addr = mail_from.split("<")[-1].split(">")[0]
                mail_subject = message['subject']

                if "stop" in mail_subject and from_addr in addrs:
                    cur.execute("delete from users where email=?", [from_addr])
                    addrs.remove(from_addr)
                elif "subscribe" in mail_subject and from_addr not in addrs:
                    cur.execute("insert into users(email) values(?)", [from_addr])
                    addrs.add(from_addr)
    conn.commit()
    return addrs


def get_email():
    page = urlopen("https://normansennema.com/archives/category/meditations")
    s = bs(page, "html.parser")

    # Find the first article
    a_article = s.find("a", attrs={"href": re.compile(".*archives.*"),})

    article_url = a_article.attrs["href"]
    article_page = urlopen(article_url)
    s = bs(article_page, "html.parser")
    content = s.find("div", attrs={"class": "entry-content"})

    bible_urls = content.find_all(
        "a", attrs={"href": re.compile("biblegateway.com"),}
    )

    # Convert the Norm-written verse to something the bible-api can read.
    def parse_verse(raw):
        # TODO
        return raw

    verses = [requests.get(f"https://bible-api.com/{parse_verse(a.text)}").json() for a in bible_urls]

    subject = a_article.text
    email_body = f"""
    <div>
    {str(content)}
    {"".join([render_verses(v) for v in verses])}
    <div>
        &nbsp;&nbsp;
        See the full post <a href="{article_url}">here</a> | Reply with the subject 'stop' to this email to unsubscribe from the list.
    </div>
    </div>
    """
    return subject, email_body


def send_email(subject, body, to_addrs):
    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, context=ssl.create_default_context()
    ) as server:
        server.login(SMTP_USER, SMTP_PASS)
        mail = email.message.EmailMessage()
        mail["Subject"] = subject
        mail["From"] = email.headerregistry.Address("Norm's Blog", SMTP_USER.split("@")[0], SMTP_USER.split("@")[1])
        mail["To"] = SMTP_USER
        mail.set_content(body, subtype="html")
        server.send_message(mail, to_addrs=to_addrs)


def update_and_send():
    to_addrs = update_recipients()
    if not to_addrs:
        # TODO: log
        return
    subject, body = get_email()
    send_email(subject, body, to_addrs)


if __name__ == "__main__":
    # runserver()
    update_and_send()
    #while True:
    #    time.sleep(60*5)
