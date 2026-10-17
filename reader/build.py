"""Build the public reader copy with a current daily calendar and local portraits."""
from datetime import datetime,date,timedelta
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import shutil,sys
from urllib.parse import urlparse,unquote
from pyluach import dates
sys.path.insert(0,str(Path(__file__).resolve().parent))
import daf_calendar as calendar
from portraits import Document
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
PUBLIC={'index.html','404.html','robots.txt','sitemap.xml','.nojekyll','about/index.html','sources/index.html','tractates/index.html'}
PUBLIC|={'assets/'+n for n in ['site.css','site.js','sources.css','source-library.js','sefaria-navigation.js','mark.svg','daf.css','daf.js','portraits.css']}
PUBLIC|={'data/'+n for n in ['calendar.json','catalogue.json','source-provenance.json','sefaria-library.json','daf-calendar.json']}

def bi(en,he):
    return '<span class="l-en" lang="en" dir="ltr">'+escape(en)+'</span><span class="l-he" lang="he" dir="rtl">'+escape(he)+'</span>'

def check_input(source):
    import re
    if sum(p.stat().st_size for p in source.rglob('*') if p.is_file())>20_000_000:raise ValueError('Reader source exceeds limit')
    for p in source.rglob('*'):
        if p.is_symlink():raise ValueError('No symbolic reader assets')
        if not p.is_file():continue
        name=p.relative_to(source).as_posix()
        if name not in PUBLIC and not re.fullmatch(r'shiur/[a-z0-9]+(?:-[a-z0-9]+)*/(?:sources/)?index.html',name):raise ValueError('Unknown public asset: '+name)
    for e in json.loads((source/'data/catalogue.json').read_text())['editions']:
        if set(e)!={'id','title','parashah','target_shabbat','category'}:raise ValueError('Unknown reader catalogue fields')

def build(source,output,now=None):
    check_input(source)
    if output.exists():raise ValueError('Output already exists')
    shutil.copytree(source,output)
    shutil.copytree(ROOT/'reader/portraits',output/'assets/portraits')
    shutil.copyfile(ROOT/'reader/rabbis.json',output/'assets/rabbis.json')
    now=now or datetime.now(ZoneInfo('Asia/Jerusalem'));today=now.astimezone(ZoneInfo('Asia/Jerusalem')).date();row=calendar.learning_day(today)
    (output/'data/daf-calendar.json').write_text(json.dumps(calendar.reader_calendar(today),ensure_ascii=False,indent=2)+'\n')
    profiles=json.loads((ROOT/'reader/rabbis.json').read_text())['profiles']
    profile=profiles[((row['cycle']-14)*2711+row['day_in_cycle']-1)%len(profiles)]
    for p in profiles:
        f=output/p['image']
        if sha256(f.read_bytes()).hexdigest()!=p['image_sha256']:raise ValueError('Portrait checksum mismatch')
    home=(output/'index.html').read_text();doc=Document(home);edits=[]
    values={'today-daf':bi(row['label']['en'],row['label']['he']),'today-cycle':bi('Cycle '+str(row['cycle']),'מחזור '+str(row['cycle'])),'today-date':bi(today.strftime('%d %B %Y'),dates.GregorianDate.from_pydate(today).to_heb().hebrew_date_string())}
    feature=next(n for n in doc.nodes if n.has('daily-feature'))
    for node in doc.nodes:
        if node.attrs.get('id') in values:edits.append((node.opening_end,node.closing_start,values[node.attrs['id']]))
        if 'data-daf-source' in node.attrs:
            opening=home[node.start:node.opening_end];old=node.attrs['href'];url=row['source_links'][int(node.attrs['data-daf-source'])]
            edits.append((node.start,node.opening_end,opening.replace('href="'+escape(old,quote=True)+'"','href="'+escape(url,quote=True)+'?lang=bi"' if '?' not in url else 'href="'+escape(url,quote=True)+'"')))
        if feature.opening_end<=node.start<feature.closing_start and 'data-rabbi-portrait' in node.attrs:
            old=node.attrs['data-rabbi-portrait'];markup=home[node.start:node.end]
            original=next(p for p in profiles if p['id']==old)
            markup=markup.replace(old,profile['id']).replace(escape(original['name'],quote=True),escape(profile['name'],quote=True))
            edits.append((node.start,node.end,markup))
    # A server-rendered current study link is never borrowed from a previous date.
    node=next(n for n in doc.nodes if n.attrs.get('id')=='today-lesson')
    study=next((e for e in json.loads((output/'data/catalogue.json').read_text())['editions'] if e['id']==row['id']),None)
    markup='<a class="text-link" id="today-lesson"'+(' href="./shiur/'+study['id']+'/">'+bi('Read today’s study →','לשיעור של היום ←') if study else ' hidden>')+'</a>'
    edits.append((node.start,node.end,markup))
    for start,end,markup in sorted(edits,reverse=True):home=home[:start]+markup+home[end:]
    (output/'index.html').write_text(home)
    validate(output)
    return {'date':today.isoformat(),'daf':row['label']['en'],'cycle':row['cycle'],'portraits':len(profiles),'public_files':sum(p.is_file() for p in output.rglob('*'))}

def validate(output):
    for page in output.rglob('*.html'):
        doc=Document(page.read_text());ids=[n.attrs['id'] for n in doc.nodes if 'id' in n.attrs]
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate HTML IDs')
        for node in doc.nodes:
            for attr in ['href','src']:
                value=node.attrs.get(attr,'');url=urlparse(value)
                if not value or url.scheme or url.netloc or not url.path:continue
                path=(page.parent/unquote(url.path)).resolve()
                if not path.is_relative_to(output.resolve()):raise ValueError('Escaping reader asset')
                if not path.is_file() and not (path/'index.html').is_file():raise ValueError('Missing reader asset: '+str(path))
    if sum(p.stat().st_size for p in output.rglob('*') if p.is_file())>20_000_000:raise ValueError('Reader size exceeds limit')

if __name__=='__main__':print(json.dumps(build(ROOT/'site',ROOT/'_site'),ensure_ascii=False))
