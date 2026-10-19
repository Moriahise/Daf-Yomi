"""Deterministic Daf Yomi Bavli calendar; Hebcal's public-domain modern-cycle algorithm."""
from datetime import date,timedelta
from functools import lru_cache
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EPOCH=date(1975,6,24)
CYCLE_LENGTH=2711

@lru_cache(maxsize=1)
def tractates():
    data=json.loads((ROOT/'data/tractates.json').read_text())['tractates']
    if len(data)!=40 or sum(t['days'] for t in data)!=CYCLE_LENGTH:raise ValueError('Invalid Daf Yomi pagination table')
    return data

def tractate(key):return next(t for t in tractates() if t['id']==key)

def cycle_start(cycle):
    if not isinstance(cycle,int) or cycle<8:raise ValueError('Supported cycles begin with cycle 8 (modern Shekalim pagination)')
    return EPOCH+timedelta(days=(cycle-8)*CYCLE_LENGTH)

def learning_day(day):
    if isinstance(day,str):day=date.fromisoformat(day)
    elapsed=(day-EPOCH).days
    if elapsed<0:raise ValueError('Daf Yomi dates before modern pagination are outside this reader')
    cycle=8+elapsed//CYCLE_LENGTH;offset=elapsed%CYCLE_LENGTH;index=offset
    for t in tractates():
        if index<t['days']:
            daf=t['first_daf']+index
            refs=[t['reference_map'][f'{daf}{side}'] for side in ('a','b')] if t.get('reference_map') else [] if t.get('folio_provider')=='dafyomi.org' else [f'{t["sefaria"]} {daf}a',f'{t["sefaria"]} {daf}b']
            links=([f'https://www.dafyomi.org/index.php?masechta=meilah&daf={daf}{side}' for side in ('a','b')] if t.get('folio_provider')=='dafyomi.org' else ['https://www.sefaria.org/'+ref.replace(' ','_') for ref in refs])
            return {'date':day.isoformat(),'cycle':cycle,'day_in_cycle':offset+1,'tractate_id':t['id'],'tractate':{'en':t['en'],'he':t['he']},'daf':daf,'label':{'en':f'{t["en"]} {daf}','he':f'{t["he"]} דף {daf}'},'references':refs,'source_links':links,'id':f'cycle-{cycle}-{t["id"]}-{daf}'}
        index-=t['days']
    raise ValueError('Daf Yomi offset outside cycle')

def cycle_tractates(cycle):
    start=cycle_start(cycle);rows=[]
    for t in tractates():
        end=start+timedelta(days=t['days']-1)
        rows.append(dict(t,start=start.isoformat(),end=end.isoformat(),cycle=cycle))
        start=end+timedelta(days=1)
    return rows

READER_START = date(2026, 9, 20)


def reader_tractates(today):
    """One current or upcoming occurrence per tractate, from the reader's launch."""
    if isinstance(today, str):
        today = date.fromisoformat(today)
    floor = max(today, READER_START)
    cycle = learning_day(floor)['cycle']
    selected = {}
    for entry in cycle_tractates(cycle) + cycle_tractates(cycle + 1):
        if (date.fromisoformat(entry['start']) >= READER_START
                and date.fromisoformat(entry['end']) >= floor):
            selected.setdefault(entry['id'], entry)
    if len(selected) != len(tractates()):
        raise ValueError('Incomplete current and upcoming tractate path')
    return sorted(selected.values(), key=lambda entry: entry['start'])


def reader_calendar(today):
    cycle=learning_day(today)['cycle']
    return {'schema':1,'timezone':'Asia/Jerusalem','day_boundary':'civil-midnight','cycle':cycle,'cycle_start':cycle_start(cycle).isoformat(),'next_cycle_start':cycle_start(cycle+1).isoformat(),'days_per_cycle':CYCLE_LENGTH,'attribution':'Calendar calculation follows Hebcal; modern Daf Yomi pagination.','tractates':[{k:v for k,v in t.items() if k!='mapping_requires_editor'} for t in tractates()],'cycles':[{'cycle':n,'start':cycle_start(n).isoformat(),'end':(cycle_start(n+1)-timedelta(days=1)).isoformat(),'tractates':[{k:v for k,v in t.items() if k!='mapping_requires_editor'} for t in cycle_tractates(n)]} for n in (cycle,cycle+1)]}
