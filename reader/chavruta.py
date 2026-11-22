"""Connect each published shiur to the verified Shekhina archive."""
import hashlib
import json
import re
import time
from html import escape
from urllib.request import Request, urlopen

BASE = "https://shekhina.org/learn/"
SLUG = re.compile(r"cycle-\d+-[a-z0-9-]+-\d+")


def published_sheets():
    request = Request(BASE+"daf-sheets.json", headers={"Cache-Control":"no-cache"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=12) as response:
                data = json.loads(response.read(1_000_001))
            if not isinstance(data, list) or not data or not all(isinstance(s, str) and SLUG.fullmatch(s) for s in data):
                raise ValueError("Invalid sheet list")
            print("Confirmed permanent Shekhina editions:", len(data))
            return set(data)
        except (OSError, ValueError) as error:
            if attempt == 2:
                raise RuntimeError("Cannot verify the sheet manifest for this build") from error
            time.sleep(2 ** (attempt+1))


def add_links(output, editions, published):
    revisions = {}
    for row in editions:
        slug = row["id"]
        if not SLUG.fullmatch(slug):
            raise ValueError("Invalid daf identifier")
        folder = output / "shiur" / slug
        lesson = folder / "index.html"
        source = folder / "sources/index.html"
        markup = lesson.read_text()
        # Digest the unmodified publication, including its source sheet.
        revisions[slug] = hashlib.sha256(lesson.read_bytes() + b"\0" + source.read_bytes()).hexdigest()
        suffix = slug + "/" if slug in published else "?date=" + row["target_shabbat"]
        links = []
        for lang, label in (("en", "Chavruta worksheet"), ("he", "דף לימוד בחברותא")):
            href = BASE + lang + "/daf-yomi/" + suffix
            links.append(f'<a class="l-{lang}" lang="{lang}" hreflang="{lang}" href="{escape(href, quote=True)}">{label}</a>')
        if markup.count("</main>") != 1:
            raise ValueError("Missing learning section in " + slug)
        lesson.write_text(markup.replace("</main>", '<p class="chavruta-links">' + " · ".join(links) + '</p></main>'))
    linked = sorted(set(revisions).intersection(published))
    (output / "data/chavruta-sheets.json").write_text(json.dumps(linked), encoding="utf-8")
    (output / "data/chavruta-revisions.json").write_text(json.dumps(revisions, sort_keys=True, separators=(",", ":")))
