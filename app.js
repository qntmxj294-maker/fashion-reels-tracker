'use strict';
const MIN_VIEWS = 10000000;
function cleanReel(row, source) {
  if (!row || typeof row !== 'object' || typeof row.views !== 'number' || !Number.isSafeInteger(row.views) || row.views < MIN_VIEWS) return null;
  let parsed;
  try { parsed = new URL(row.url); } catch { return null; }
  const match = parsed.pathname.match(/^\/reel\/([A-Za-z0-9_-]+)\/?$/);
  if (parsed.protocol !== 'https:' || !['www.instagram.com', 'instagram.com'].includes(parsed.hostname) || parsed.port || parsed.username || parsed.password || !match) return null;
  const username = String(row.username || '').replace(/^@/, '').toLowerCase();
  if (!/^[a-z0-9._]{1,30}$/.test(username)) return null;
  const validDate = x => typeof x === 'string' && Number.isFinite(Date.parse(x)) ? x : null;
  return {id:match[1], url:'https://www.instagram.com/reel/'+match[1]+'/', username, views:row.views,
    checked_at:validDate(row.checked_at), posted_at:validDate(row.posted_at),
    category:String(row.category || '미분류').slice(0,40), note:String(row.note || '').slice(0,500),
    source, metric:String(row.metric || '').slice(0,30)};
}
function combine(auto, manual) {
  // Keep both observations when one link has an API record and a manual annotation.
  return [...auto, ...manual];
}
if (typeof module !== 'undefined') module.exports = {cleanReel, combine};
if (typeof document !== 'undefined') {
  const $ = id => document.getElementById(id);
  const KEY = 'wondukgu-reels-manual-v2';
  let auto = [], manual = [], storageOK = true;
  const fmt = x => Number(x).toLocaleString('ko-KR');
  const date = x => x ? new Date(x).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',year:'2-digit',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '날짜 없음';
  function el(tag, cls, value) { const x=document.createElement(tag); if(cls)x.className=cls; if(value!==undefined)x.textContent=value; return x; }
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '[]');
    if (!Array.isArray(saved)) throw Error('Invalid backup');
    manual = saved.map(r=>cleanReel(r, r.source === 'manual:import' ? 'manual:import' : 'manual:entered')).filter(Boolean);
  } catch {
    storageOK=false;
    $('manual-status').textContent='브라우저 저장소를 읽을 수 없습니다. 저장한 뒤 JSON 백업을 내려받으세요.';
  }
  function save() {
    try { localStorage.setItem(KEY,JSON.stringify(manual)); storageOK=true; }
    catch { storageOK=false; }
    return storageOK;
  }
  function render() {
    const q=$('search').value.trim().toLowerCase(), mode=$('source').value, sort=$('sort').value;
    const all=combine(auto,manual);
    $('total').textContent=fmt(new Set(all.map(r=>r.id)).size);
    const rows=all.filter(r=>(mode==='all'||r.source.startsWith(mode+':')) && (r.username+' '+r.note+' '+r.category).toLowerCase().includes(q));
    rows.sort((a,b)=>sort==='views'?b.views-a.views:(Date.parse(b[sort==='recent'?'posted_at':'checked_at'])||0)-(Date.parse(a[sort==='recent'?'posted_at':'checked_at'])||0));
    $('cards').replaceChildren();
    if (!rows.length) {
      const box=el('div','empty');box.append(el('h2','',q||mode!=='all'?'조건에 맞는 릴스가 없어요':'첫 레퍼런스를 저장해보세요'),el('p','', '직접 저장에 링크와 조회수를 입력하면 바로 사용할 수 있습니다. 자동 수집은 GitHub와 Apify를 연결한 뒤 시작됩니다.'));
      $('cards').append(box);
    }
    for (const row of rows) {
      const card=el('article','card'),top=el('div','card-top');
      const isManual=row.source.startsWith('manual:');
      top.append(el('span','tag'+(isManual?' manual':''),isManual?(row.source==='manual:import'?'가져온 자료':'직접 입력'):'API 수집'));
      if (isManual) {
        const button=el('button','delete','삭제');button.type='button';button.setAttribute('aria-label',row.username+' 직접 저장 기록 삭제');
        button.onclick=()=>{manual=manual.filter(x=>x.id!==row.id);save();render();};top.append(button);
      }
      const views=el('div','views',fmt(row.views));views.append(el('span','','회'));
      card.append(top,el('div','handle','@'+row.username),views,el('div','record','기록 '+date(row.checked_at)));
      if (row.posted_at) card.append(el('div','record','게시 '+date(row.posted_at)));
      card.append(el('div','record',isManual?'조회수를 사용자가 입력한 자료':'수집 지표: '+(row.metric||'기존 기록')));
      if(row.category!=='미분류')card.append(el('div','record',row.category));
      if(row.note)card.append(el('p','note',row.note));
      const link=el('a','open','릴스 원본 보기 ↗');link.href=row.url;link.target='_blank';link.rel='noopener noreferrer';card.append(link);$('cards').append(card);
    }
  }
  $('manual-form').onsubmit=event=>{
    event.preventDefault();
    const row=cleanReel({url:$('reel-url').value.trim(),username:$('reel-user').value.trim(),views:Number($('reel-views').value),category:$('reel-category').value,note:$('reel-note').value,checked_at:new Date().toISOString()},'manual:entered');
    if(!row){$('manual-status').textContent='인스타 릴스 링크, 계정명, 1,000만 이상인 정수 조회수를 확인해주세요.';return;}
    manual=manual.filter(x=>x.id!==row.id);manual.push(row);
    $('manual-status').textContent=save()?'저장했습니다. 같은 링크는 최신 입력으로 갱신됩니다.':'화면에 추가했습니다. 저장소를 쓸 수 없어 JSON 백업이 필요합니다.';
    $('manual-form').reset();render();
  };
  $('export').onclick=()=>{
    const blob=new Blob([JSON.stringify({schema_version:2,exported_at:new Date().toISOString(),items:combine(auto,manual)},null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='fashion-reels-backup-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    $('manual-status').textContent='백업 다운로드를 요청했습니다.';
  };
  $('import').onchange=async event=>{
    const file=event.target.files[0];if(!file)return;
    try {
      if(file.size>5*1024*1024)throw Error('Large file');
      const input=JSON.parse(await file.text()),rows=Array.isArray(input)?input:input.items;
      if(!Array.isArray(rows)||rows.length>5000)throw Error('Invalid format');
      const valid=rows.map(r=>cleanReel(r,'manual:import')).filter(Boolean),map=new Map(manual.map(r=>[r.id,r]));
      for(const row of valid)map.set(row.id,row);manual=[...map.values()];
      const persisted=save();render();$('manual-status').textContent=valid.length+'개 기록을 가져왔습니다. '+(rows.length-valid.length)+'개 제외.'+(persisted?'':' 저장소 오류: JSON 백업을 내려받으세요.');
    } catch {$('manual-status').textContent='가져오기 실패: 5MB 이하 JSON 백업 파일인지 확인해주세요.';}
    event.target.value='';
  };
  async function fetchJSON(path){const response=await fetch(path+'?t='+Date.now(),{cache:'no-store'});if(!response.ok)throw Error('HTTP');return response.json();}
  async function load() {
    if(location.protocol==='file:' || document.documentElement.dataset.manualOnly==='true'){
      $('status').textContent='직접 저장 모드 · API 호출이나 비용 없이 사용합니다. 브라우저 저장소에 보관하며 자동으로 조회수를 갱신하지 않습니다.';
      $('reload').disabled=true;render();return;
    }
    const results=await Promise.allSettled(['data/reels.json','data/status.json','data/budget.json'].map(fetchJSON));
    if(results[0].status!=='fulfilled'){$('status').textContent='자동 데이터를 읽지 못했습니다. 기존 화면 기록은 유지되며 직접 저장을 사용할 수 있습니다.';render();return;}
    const data=results[0].value;
    auto=(Array.isArray(data.items)?data.items:[]).map(r=>cleanReel(r,'auto:'+(String(r.source||'').endsWith('apify')?'apify':'filtered'))).filter(Boolean);
    const handles=Array.isArray(data.monitored_accounts)?data.monitored_accounts.filter(h=>typeof h==='string'&&/^[a-zA-Z0-9._]{1,30}$/.test(h)):[];
    $('account-count').textContent=fmt(handles.length);$('account-links').replaceChildren();
    for(const handle of handles){const a=el('a','','@'+handle);a.href='https://www.instagram.com/'+handle+'/reels/';a.target='_blank';a.rel='noopener noreferrer';$('account-links').append(a);}
    if(results[2].status==='fulfilled'){
      const cutoff=Date.now()-31*86400000;
      const sum=(results[2].value.reservations||[]).filter(r=>Date.parse(r.reserved_at)>cutoff).reduce((n,r)=>n+(Number(r.cap_usd)||0),0);
      $('reserved').textContent='$'+sum.toFixed(2);
    }
    const stamp=data.last_api_response_at||data.last_successful_check;
    $('status').textContent=stamp?'마지막 API 응답 '+date(stamp)+' · 수집 범위와 예산에 따른 일부 결과입니다. 카드별 기록 시점을 확인하세요.':'자동 수집 전입니다. 직접 저장은 지금 사용할 수 있습니다.';
    if(stamp&&Date.now()-Date.parse(stamp)>48*3600000)$('status').textContent+=' 48시간 이상 지난 기록입니다.';
    if(results[1].status==='fulfilled'){
      const status=results[1].value;$('details').replaceChildren();
      if(!status.last_attempt_at)$('details').textContent='실행 기록 없음';
      for(const entry of status.accounts||[]){$('details').append(el('p','', '@'+entry.username+' · '+(entry.status==='response_received'?'응답 수신 / 조건 통과 '+entry.qualifying+'개':'실패 / '+(entry.error||'확인 필요'))));}
      if((status.accounts||[]).some(r=>r.status==='error'))$('status').textContent+=' 일부 계정 수집이 실패했습니다. 상세 상태를 확인하세요.';
    }
    render();
  }
  ['search','source','sort'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',render));
  $('reload').onclick=()=>load().catch(()=>{$('status').textContent='자동 데이터 형식을 확인해주세요. 직접 저장 기록은 유지됩니다.';});
  render();load().catch(()=>{$('status').textContent='자동 데이터 형식을 확인해주세요. 직접 저장 기록은 유지됩니다.';});
}
