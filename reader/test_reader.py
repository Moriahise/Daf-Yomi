from datetime import datetime
from pathlib import Path
import json,tempfile,unittest
from zoneinfo import ZoneInfo
from build import build,ROOT
from portraits import Document

class ReaderTests(unittest.TestCase):
    def test_current_daf_and_both_sides_match_the_calendar(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'site';result=build(ROOT/'site',output,datetime(2026,10,17,23,30,tzinfo=ZoneInfo('UTC')))
            self.assertEqual(result['daf'],'Bekhorot 30');text=(output/'index.html').read_text();nodes=Document(text).nodes
            source=next(n for n in nodes if n.attrs.get('data-daf-source')=='0');self.assertIn('Bekhorot_30a',source.attrs['href'])
            self.assertIn('Bekhorot 30',text);self.assertEqual(sum(n.attrs.get('id')=='daf-date' for n in nodes),1)
    def test_reading_guides_and_both_languages_remain_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'site';build(ROOT/'site',output);self.assertEqual((ROOT/'site/sources/index.html').read_bytes(),(output/'sources/index.html').read_bytes())
            self.assertEqual(len(json.loads((output/'data/daf-calendar.json').read_text())['tractates']),40)
            for p in output.rglob('*.html'):
                text=p.read_text();self.assertNotIn('DAFYOMI_REVIEW_API_KEY',text);self.assertNotIn('Fachliche Freigabe',text);self.assertNotIn('redaktion/',text)

if __name__=='__main__':unittest.main()
