from datetime import datetime, date
from pathlib import Path
import json,tempfile,unittest
from zoneinfo import ZoneInfo
from build import build,ROOT,refresh_tractates
import daf_calendar as calendar
from portraits import Document

class ReaderTests(unittest.TestCase):
    def test_tractate_links_follow_current_and_upcoming_cycles(self):
        original=(ROOT/'site/tractates/index.html').read_text()
        text=refresh_tractates(original,date(2026,10,19));doc=Document(text)
        cards=[node for node in doc.nodes if node.has('tractate-card')]
        self.assertEqual(len(cards),40)
        self.assertEqual(cards[0].attrs['data-tractate'],'bekhorot')
        for card,entry in zip(cards,calendar.reader_tractates('2026-10-19'),strict=True):
            self.assertEqual(card.attrs['data-tractate'],entry['id'])
            link=next(node for node in doc.nodes if node.tag=='a' and card.opening_end<=node.start<card.closing_start)
            self.assertEqual(link.attrs['href'],'../?date='+entry['start']+'#calendar')
            self.assertIn('Cycle '+str(entry['cycle']),text[card.start:card.end])
            self.assertIn(entry['end'],text[card.start:card.end])
        self.assertNotIn('2020-01-05',text)
        berakhot=next(card for card in cards if card.attrs['data-tractate']=='berakhot')
        self.assertIn('?date=2027-06-08#calendar',text[berakhot.start:berakhot.end])
        self.assertEqual(refresh_tractates(text,date(2026,10,19)),text)

    def test_completed_tractate_moves_to_its_next_occurrence(self):
        original=(ROOT/'site/tractates/index.html').read_text()
        text=refresh_tractates(original,date(2026,11,19));doc=Document(text)
        cards=[node for node in doc.nodes if node.has('tractate-card')]
        self.assertEqual(cards[0].attrs['data-tractate'],'arakhin')
        bekhorot=next(card for card in cards if card.attrs['data-tractate']=='bekhorot')
        self.assertIn('?date=2034-02-21#calendar',text[bekhorot.start:bekhorot.end])

    def test_current_daf_and_both_sides_match_the_calendar(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'site';result=build(ROOT/'site',output,datetime(2026,10,17,23,30,tzinfo=ZoneInfo('UTC')))
            self.assertEqual(result['daf'],'Bekhorot 30');text=(output/'index.html').read_text();nodes=Document(text).nodes
            source=next(n for n in nodes if n.attrs.get('data-daf-source')=='0');self.assertIn('Bekhorot_30a',source.attrs['href'])
            self.assertIn('Bekhorot 30',text);self.assertEqual(sum(n.attrs.get('id')=='daf-date' for n in nodes),1)
    def test_tractate_overview_advances_at_the_next_cycle_without_api_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'site';build(ROOT/'site',output,datetime(2027,6,8,8,tzinfo=ZoneInfo('Asia/Jerusalem')))
            text=(output/'tractates/index.html').read_text();doc=Document(text)
            first=next(n for n in doc.nodes if n.attrs.get('data-tractate')=='berakhot')
            self.assertIn('2027-06-08',text[first.start:first.end]);self.assertIn('Cycle 15',text)

    def test_reading_guides_and_both_languages_remain_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'site';build(ROOT/'site',output);self.assertEqual((ROOT/'site/sources/index.html').read_bytes(),(output/'sources/index.html').read_bytes())
            self.assertEqual(len(json.loads((output/'data/daf-calendar.json').read_text())['tractates']),40)
            for p in output.rglob('*.html'):
                text=p.read_text();self.assertNotIn('DAFYOMI_REVIEW_API_KEY',text);self.assertNotIn('Fachliche Freigabe',text);self.assertNotIn('redaktion/',text)

if __name__=='__main__':unittest.main()
