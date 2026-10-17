/* The daily calendar runs locally; no account or API credential enters this reader. */
(() => {
  'use strict';
  const input=document.querySelector('#daf-date');if(!input)return;
  const normalize=t=>(t||'').normalize('NFKD').replace(/[\u0591-\u05c7]/g,'').toLowerCase();
  function filterStudies(){const tokens=normalize(document.querySelector('#search').value).split(/\s+/).filter(Boolean),focus=document.querySelector('#category').value,tractate=document.querySelector('#study-tractate').value,cycle=document.querySelector('#study-cycle').value;let count=0;document.querySelectorAll('.edition-card').forEach(card=>{card.hidden=!((focus==='all'||card.dataset.category===focus)&&(tractate==='all'||card.dataset.tractate===tractate)&&(cycle==='all'||card.dataset.cycle===cycle)&&tokens.every(t=>normalize(card.dataset.search).includes(t)));if(!card.hidden)count++;});document.querySelector('#no-results').hidden=count!==0;document.querySelector('#search-status').textContent=document.documentElement.dataset.mode==='he'?count+' שיעורים':count+' studies';}
  ['#search','#category','#study-tractate','#study-cycle'].forEach(selector=>document.querySelector(selector).addEventListener(selector==='#search'?'input':'change',filterStudies));document.querySelectorAll('[data-mode-set]').forEach(b=>b.addEventListener('click',filterStudies));
  const filters=new URL(location.href).searchParams;
  [['#study-tractate','tractate'],['#study-cycle','cycle']].forEach(([selector,key])=>{const select=document.querySelector(selector),value=filters.get(key);if(value&&Array.from(select.options).some(option=>option.value===value))select.value=value;});
  filterStudies();
  let calendar,catalogue,profiles,activeDate,lastToday;
  const utcDay=value=>Math.floor(Date.parse(value+'T00:00:00Z')/86400000);
  const iso=number=>new Date(number*86400000).toISOString().slice(0,10);
  const jerusalemToday=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Jerusalem',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  const pair=value=>{const fragment=document.createDocumentFragment();for(const language of ['en','he']){const span=document.createElement('span');span.className='l-'+language;span.lang=language;span.dir=language==='he'?'rtl':'ltr';span.textContent=value[language];fragment.append(span);}return fragment;};
  function calculate(value){
    const elapsed=utcDay(value)-utcDay('1975-06-24');if(!Number.isFinite(elapsed)||elapsed<0)throw Error('Choose a date from 24 June 1975 onward. / בחרו תאריך מ־24 ביוני 1975 ואילך.');
    const cycle=8+Math.floor(elapsed/2711),offset=elapsed%2711;let rest=offset;
    for(const tractate of calendar.tractates){if(rest<tractate.days){const daf=tractate.first_daf+rest;
      const refs=tractate.reference_map?['a','b'].map(side=>tractate.reference_map[daf+side]).filter(Boolean):tractate.mapping_requires_editor?[]:['a','b'].map(side=>tractate.sefaria+' '+daf+side);
      const links=tractate.folio_provider==='dafyomi.org'?['a','b'].map(side=>'https://www.dafyomi.org/index.php?masechta=meilah&daf='+daf+side):refs.map(ref=>'https://www.sefaria.org/'+encodeURIComponent(ref.replaceAll(' ','_'))+'?lang=bi');
      return {date:value,cycle,offset,daf,tractate,label:{en:tractate.en+' '+daf,he:tractate.he+' דף '+daf},links,id:'cycle-'+cycle+'-'+tractate.id+'-'+daf};}rest-=tractate.days;}
    throw Error('Calendar unavailable. / הלוח אינו זמין.');
  }
  function link(url,text){const a=document.createElement('a');a.href=url;a.replaceChildren(pair(text));a.target='_blank';a.rel='noopener noreferrer';return a;}
  function render(value){
    const row=calculate(value);activeDate=value;const target=document.querySelector('#daf-date-result');target.replaceChildren();
    const h=document.createElement('h3');h.append(pair(row.label));target.append(h);const p=document.createElement('p');p.append(pair({en:value+' · Cycle '+row.cycle,he:value+' · מחזור '+row.cycle}));target.append(p);
    row.links.forEach((url,i)=>target.append(link(url,{en:'Amud '+['a','b'][i]+' ↗',he:'עמוד '+['א׳','ב׳'][i]+' ↗'})));
    const study=catalogue.editions.find(e=>e.id===row.id);if(study){const a=document.createElement('a');a.className='button primary';a.href='./shiur/'+study.id+'/';a.append(pair({en:'Read study →',he:'לשיעור ←'}));target.append(a);}
    const url=new URL(location.href);url.searchParams.set('date',value);history.replaceState(null,'',url);
  }
  function updateToday(){
    const today=jerusalemToday(),row=calculate(today);document.querySelector('#today-daf').replaceChildren(pair(row.label));document.querySelector('#today-cycle').replaceChildren(pair({en:'Cycle '+row.cycle,he:'מחזור '+row.cycle}));
    const readable=new Intl.DateTimeFormat('en-GB',{timeZone:'UTC',dateStyle:'long'}).format(new Date(today+'T12:00:00Z'));const hebrew=new Intl.DateTimeFormat('he-IL-u-ca-hebrew',{timeZone:'UTC',dateStyle:'long'}).format(new Date(today+'T12:00:00Z'));document.querySelector('#today-date').replaceChildren(pair({en:readable,he:hebrew}));
    document.querySelectorAll('[data-daf-source]').forEach((a,i)=>{a.href=row.links[i]||row.links[0];});
    const study=catalogue.editions.find(e=>e.id===row.id),a=document.querySelector('#today-lesson');a.hidden=!study;if(study){a.href='./shiur/'+study.id+'/';a.replaceChildren(pair({en:'Read today’s study →',he:'לשיעור של היום ←'}));}
    if(profiles){const profile=profiles.profiles[((row.cycle-14)*2711+row.offset)%profiles.profiles.length];if(profile){const figure=document.querySelector('.daily-feature [data-rabbi-portrait]');figure.dataset.rabbiPortrait=profile.id;figure.querySelector('img').src='./assets/portraits/'+profile.id+'.webp';figure.querySelector('img').alt=profile.name;figure.querySelector('.portrait-name').textContent=profile.name;}}
    const listing=document.querySelector('#daily-calendar');listing.replaceChildren();for(let i=0;i<7;i++){const day=calculate(iso(utcDay(today)+i)),entry=document.createElement('div');entry.className='calendar-row';const date=document.createElement('span');date.textContent=day.date;const strong=document.createElement('strong');strong.append(pair(day.label));const study=catalogue.editions.find(e=>e.id===day.id);let read;if(study){read=document.createElement('a');read.href='./shiur/'+study.id+'/';read.append(pair({en:'Read study →',he:'לשיעור ←'}));}else{read=link(day.links[0],{en:'Original text ↗',he:'למקור ↗'});}entry.append(date,strong,read);listing.append(entry);}
  }
  async function start(){
    try{[calendar,catalogue,profiles]=await Promise.all(['data/daf-calendar.json','data/catalogue.json','assets/rabbis.json'].map(async url=>{const r=await fetch(url);if(!r.ok)throw Error('Calendar loading failed');return r.json();}));
      updateToday();lastToday=jerusalemToday();const requested=new URL(location.href).searchParams.get('date');input.value=requested&&/^\d{4}-\d{2}-\d{2}$/.test(requested)?requested:jerusalemToday();render(input.value);
      document.querySelector('#daf-date-form').addEventListener('submit',event=>{event.preventDefault();if(!input.reportValidity())return;try{render(input.value);}catch(error){document.querySelector('#daf-date-result').textContent=error.message;}});
      document.querySelector('#daf-today').addEventListener('click',()=>{input.value=jerusalemToday();render(input.value);});
      function refresh(){const today=jerusalemToday();if(today===lastToday)return;const following=activeDate===lastToday;updateToday();if(following){input.value=today;render(today);}lastToday=today;}
      setInterval(refresh,60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
    }catch(error){document.querySelector('#daf-date-result').textContent='The calendar could not load. The original source links above remain available. / לא ניתן לטעון את הלוח. הקישורים למקורות שלמעלה זמינים.';}
  }
  start();
})();
