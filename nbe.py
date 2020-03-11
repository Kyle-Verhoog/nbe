from email.message import EmailMessage
import re
from urllib.request import urlopen
import os
import smtplib, ssl

from bs4 import BeautifulSoup as bs
import requests


SMTP_PORT = os.getenv("SMTP_PORT", 465)
SMTP_URL = os.getenv("SMTP_URL", "smtp.gmail.com")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


def render_verses(verses):
    verse_html = ""

    for v in verses["verses"]:
        verse_html += f"<sup>{v['verse']}</sup>{v['text']}"

    return f"""
    <div>
        <h2>{verses['reference']}</h2>
        {verse_html}
    </div>
    """


page = urlopen("https://normansennema.com/archives/category/meditations")
s = bs(page, "html.parser")

# Find the first article
a_article = s.find("a", attrs={"href": re.compile(".*archives.*"),})

article_url = a_article.attrs["href"]
article_page = urlopen(article_url)
s = bs(article_page, "html.parser")
content = s.find("div", attrs={"class": "entry-content"})

bible_urls = s.find_all(
    "a", attrs={"href": re.compile("biblegateway.com"),}, text=re.compile(":")
)
verses = [requests.get(f"https://bible-api.com/{a.text}").json() for a in bible_urls]

email_body = f"""
<div>
{str(content)}
{"".join([render_verses(v) for v in verses])}
</div>
"""


with smtplib.SMTP_SSL(
    "smtp.gmail.com", 465, context=ssl.create_default_context()
) as server:
    server.login(SMTP_USER, SMTP_PASS)
    email = EmailMessage()
    email["Subject"] = a_article.text
    email["From"] = SMTP_USER
    email["To"] = SMTP_USER
    email.set_content(email_body, subtype="html")
    server.send_message(email, to_addrs=[])
