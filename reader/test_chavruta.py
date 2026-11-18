import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from chavruta import add_links, published_sheets


class ChavrutaLinks(unittest.TestCase):
    def test_public_manifest_recovers_after_transient_failure(self):
        slug = "cycle-15-berakhot-2"
        with patch("chavruta.time.sleep"), patch("chavruta.urlopen", side_effect=[
                TimeoutError(), io.BytesIO(json.dumps([slug]).encode())]) as fetch:
            self.assertEqual(published_sheets(), {slug})
            self.assertEqual(fetch.call_count, 2)

    def test_invalid_remote_identifier_uses_dated_links(self):
        with patch("chavruta.time.sleep"), patch("chavruta.urlopen", side_effect=lambda *a, **kw:
                io.BytesIO(b'["../../wrong"]')):
            self.assertEqual(published_sheets(), set())

    def test_confirmed_links_and_fallback_for_a_new_edition(self):
        first, second = ("cycle-15-berakhot-2", "cycle-15-berakhot-3")
        editions = [{"id":first, "target_shabbat":"2027-06-08"}, {"id":second, "target_shabbat":"2027-06-09"}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/"data").mkdir()
            for slug in (first,second):
                folder = root/"shiur"/slug
                (folder/"sources").mkdir(parents=True)
                (folder/"index.html").write_text("<main>Test</main>")
                (folder/"sources/index.html").write_text("Sources")
            add_links(root,editions,{first})
            for lang in ("en","he"):
                base = "https://shekhina.org/learn/"+lang+"/daf-yomi/"
                self.assertIn(base+first+"/",(root/"shiur"/first/"index.html").read_text())
                self.assertIn(base+"?date=2027-06-09",(root/"shiur"/second/"index.html").read_text())
            expected = hashlib.sha256(b"<main>Test</main>\0Sources").hexdigest()
            self.assertEqual(json.loads((root/"data/chavruta-revisions.json").read_text()),{first:expected,second:expected})
