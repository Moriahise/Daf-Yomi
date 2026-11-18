"""Check the public round trip from each pilot shiur into a real answered record."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
import time
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import Request, urlopen

from portraits import Document

SITE = "https://shekhina.org/"
DAF = "https://moriahise.github.io/Daf-Yomi/"
PILOT = [f"cycle-15-berakhot-{i}" for i in range(2, 9)]


@lru_cache(maxsize=150)
def get(url):
    with urlopen(Request(url,headers={"User-Agent":"Daf-Yomi-publication-check/1.0"}), timeout=15) as response:
        return response.read(4_000_001).decode("utf-8")


def links(page):
    return [node.attrs["href"] for node in Document(page).nodes if node.tag=="a" and node.attrs.get("href")]


@lru_cache(maxsize=60)
def verify_primary(url):
    # A small GET also works on primary sites which do not implement HEAD.
    with urlopen(Request(url,headers={"User-Agent":"Daf-Yomi-publication-check/1.0"}), timeout=15) as response:
        if not response.read(512):
            raise ValueError("Empty primary source: "+url)
    return True


def check_slug(slug, release):
    shiur = DAF+"shiur/"+slug+"/"
    outbound = links(get(shiur))
    primary = set(links(get(shiur+"sources/")))
    for lang, other in (("en","he"), ("he","en")):
        path = "learn/"+lang+"/daf-yomi/"+slug+"/"
        target = SITE+path
        if target not in outbound:
            raise ValueError("Shiur has not linked the permanent sheet yet: "+target)
        sheet = get(target)
        doc = Document(sheet)
        addresses = links(sheet)
        assert any(n.tag=="link" and n.attrs.get("rel")=="canonical" and n.attrs.get("href")==target for n in doc.nodes), target
        assert any(n.tag=="html" and n.attrs.get("lang")==lang for n in doc.nodes), target
        assert "/learn/"+other+"/daf-yomi/"+slug+"/" in addresses and shiur in addresses and shiur+"sources/" in addresses, target
        refs = sorted(u for u in primary.intersection(addresses) if urlsplit(u).netloc in ("www.sefaria.org","www.sefaria.org.il"))
        assert refs, target
        for url in refs:
            verify_primary(url)
        records = [u for u in addresses if u.startswith("/qa.html?id=")]
        if not records and slug not in PILOT:
            continue
        assert records and any(n.tag=="blockquote" for n in doc.nodes),target
        pid = parse_qs(urlsplit(records[0]).query)["id"][0]
        sign = sha256(pid.encode()).hexdigest()
        get(urljoin(SITE,records[0]))
        record=json.loads(get(release+"content/"+sign[:2]+"/"+sign+".json"))
        assert record["id"]==pid and record["kind"]=="qa" and record["answers"], pid
        print(lang,slug,pid,"verified",flush=True)


def main():
    for attempt in range(4):
        try:
            ids = json.loads(get(SITE+"learn/daf-sheets.json"))
            if not set(PILOT).issubset(ids):
                raise ValueError("Pilot sheets missing from the public manifest")
            release = urljoin(SITE,json.loads(get(SITE+"catalog/manifest.json"))["data_base"])
            sample = list(PILOT)
            remaining = sorted(set(ids).difference(PILOT))
            if remaining:
                sample.append(remaining[datetime.now(timezone.utc).date().toordinal()%len(remaining)])
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda s: check_slug(s,release),sample))
            print("Verified both directions, primary-source links and archive records for",len(sample),"dafim")
            return
        except (OSError,ValueError,AssertionError,KeyError,IndexError) as err:
            if attempt == 3:
                raise
            print("Retrying publication check:",err,flush=True)
            get.cache_clear()
            time.sleep(20)


if __name__ == "__main__":
    main()
