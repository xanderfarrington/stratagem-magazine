import os
import re
import html
import feedparser
from bs4 import BeautifulSoup
from jinja2 import Template
from playwright.sync_api import sync_playwright

RSS_FEED_URL = "https://stratageminitiative.substack.com/feed"
OUTPUT_DIR = "output"
HTML_FILE = f"{OUTPUT_DIR}/magazine.html"
PDF_FILE = f"{OUTPUT_DIR}/stratagem_magazine.pdf"

MAX_ARTICLES = 5
FILTER_KEYWORD = "Deep Dive"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def extract_article_content(entry):
    raw_html = ""

    if "content" in entry and entry.content:
        raw_html = entry.content[0].value
    elif "summary" in entry:
        raw_html = entry.summary

    soup = BeautifulSoup(raw_html, "html.parser")

    content = []

    for tag in soup.find_all(["p", "h2", "h3", "blockquote", "li"]):
        text = clean_text(tag.get_text(" "))
        if not text:
            continue

        if tag.name == "h2":
            content.append({"type": "heading", "text": text})
        elif tag.name == "h3":
            content.append({"type": "subheading", "text": text})
        elif tag.name == "blockquote":
            content.append({"type": "quote", "text": text})
        elif tag.name == "li":
            content.append({"type": "bullet", "text": text})
        else:
            content.append({"type": "paragraph", "text": text})

    return content


def load_articles_from_rss():
    feed = feedparser.parse(RSS_FEED_URL)

    if feed.bozo:
        raise RuntimeError(f"RSS feed error: {feed.bozo_exception}")

    articles = []

    for entry in feed.entries:
        title = clean_text(html.unescape(entry.get("title", "Untitled Article")))

        if FILTER_KEYWORD.lower() not in title.lower():
            continue

        article = {
            "title": title,
            "subtitle": clean_text(entry.get("summary", "")),
            "author": clean_text(entry.get("author", "")),
            "date": clean_text(entry.get("published", "")),
            "url": entry.get("link", ""),
            "content": extract_article_content(entry),
        }

        articles.append(article)

        if len(articles) >= MAX_ARTICLES:
            break

    if not articles:
        raise ValueError("No Deep Dive articles found in RSS feed.")

    return articles


MAGAZINE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Stratagem Magazine</title>
  <style>
    @page {
      size: Letter;
      margin: 0.7in;
    }

    body {
      font-family: Georgia, serif;
      color: #111;
      background: white;
      line-height: 1.45;
    }

    .cover {
      page-break-after: always;
      height: 9in;
      display: flex;
      flex-direction: column;
      justify-content: center;
      border-top: 10px solid #111;
      border-bottom: 2px solid #111;
    }

    .kicker {
      font-family: Arial, sans-serif;
      text-transform: uppercase;
      letter-spacing: 0.15em;
      font-size: 12px;
      margin-bottom: 20px;
    }

    .cover h1 {
      font-size: 58px;
      line-height: 0.95;
      margin: 0;
    }

    .cover p {
      font-family: Arial, sans-serif;
      font-size: 16px;
      margin-top: 28px;
      max-width: 520px;
    }

    .toc {
      page-break-after: always;
    }

    .toc h1 {
      font-size: 36px;
      border-bottom: 2px solid #111;
      padding-bottom: 10px;
    }

    .toc-item {
      margin: 18px 0;
      font-size: 18px;
    }

    .article {
      page-break-before: always;
    }

    .article-header {
      margin-bottom: 28px;
      border-bottom: 2px solid #111;
      padding-bottom: 18px;
    }

    .label {
      font-family: Arial, sans-serif;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 11px;
      margin-bottom: 12px;
    }

    .article h1 {
      font-size: 38px;
      line-height: 1.05;
      margin: 0 0 12px 0;
    }

    .meta {
      font-family: Arial, sans-serif;
      font-size: 11px;
      color: #555;
      margin-bottom: 10px;
    }

    .subtitle {
      font-family: Arial, sans-serif;
      font-size: 16px;
      color: #444;
    }

    .article-body {
      column-count: 2;
      column-gap: 0.35in;
      font-size: 11.5pt;
    }

    .article-body p {
      margin-top: 0;
      margin-bottom: 12px;
    }

    .article-body h2 {
      break-after: avoid;
      column-span: all;
      font-family: Arial, sans-serif;
      font-size: 22px;
      margin: 24px 0 10px;
      border-top: 1px solid #111;
      padding-top: 10px;
    }

    .article-body h3 {
      font-family: Arial, sans-serif;
      font-size: 16px;
      margin: 18px 0 8px;
    }

    blockquote {
      column-span: all;
      font-size: 22px;
      line-height: 1.25;
      margin: 24px 0;
      padding-left: 18px;
      border-left: 4px solid #111;
      font-style: italic;
    }

    .source {
      margin-top: 28px;
      font-family: Arial, sans-serif;
      font-size: 9px;
      color: #555;
      word-break: break-all;
    }
  </style>
</head>

<body>

  <section class="cover">
    <div class="kicker">The Stratagem Initiative</div>
    <h1>Deep Dive<br>Magazine</h1>
    <p>A print-ready collection of Stratagem Deep Dive articles, automatically formatted from Substack RSS.</p>
  </section>

  <section class="toc">
    <h1>Contents</h1>
    {% for article in articles %}
      <div class="toc-item">{{ loop.index }}. {{ article.title }}</div>
    {% endfor %}
  </section>

  {% for article in articles %}
    <section class="article">
      <div class="article-header">
        <div class="label">Deep Dive</div>
        <h1>{{ article.title }}</h1>
        <div class="meta">
          {% if article.author %}{{ article.author }}{% endif %}
          {% if article.date %} · {{ article.date }}{% endif %}
        </div>
      </div>

      <div class="article-body">
        {% for item in article.content %}
          {% if item.type == "heading" %}
            <h2>{{ item.text }}</h2>
          {% elif item.type == "subheading" %}
            <h3>{{ item.text }}</h3>
          {% elif item.type == "quote" %}
            <blockquote>{{ item.text }}</blockquote>
          {% elif item.type == "bullet" %}
            <p>• {{ item.text }}</p>
          {% else %}
            <p>{{ item.text }}</p>
          {% endif %}
        {% endfor %}
      </div>

      <div class="source">Source: {{ article.url }}</div>
    </section>
  {% endfor %}

</body>
</html>
"""


def render_html(articles):
    template = Template(MAGAZINE_TEMPLATE)
    html_output = template.render(articles=articles)

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_output)


def export_pdf():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{os.path.abspath(HTML_FILE)}", wait_until="load")

        page.pdf(
            path=PDF_FILE,
            format="Letter",
            print_background=True,
            margin={
                "top": "0.7in",
                "right": "0.7in",
                "bottom": "0.7in",
                "left": "0.7in",
            },
        )

        browser.close()


def main():
    articles = load_articles_from_rss()
    render_html(articles)
    export_pdf()

    print(f"Done. PDF saved to {PDF_FILE}")


if __name__ == "__main__":
    main()
