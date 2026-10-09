const {test}=require('node:test');
const assert=require('node:assert/strict');
const {cleanReel,combine,onePerAccount}=require('./app.js');
const row={url:'https://www.instagram.com/reel/Ab12/?utm_source=test',username:'@WONDUKGU',views:10000000,checked_at:'2026-10-09T00:00:00Z'};
test('canonical reel URL and threshold boundary',()=>{
  const clean=cleanReel(row,'manual:entered');
  assert.equal(clean.url,'https://www.instagram.com/reel/Ab12/');
  assert.equal(clean.username,'wondukgu');
  assert.equal(clean.source,'manual:entered');
  assert.equal(cleanReel({...row,views:9999999},'manual:entered'),null);
});
test('reject external URLs, credentials and invalid counts',()=>{
  for(const url of ['javascript:alert(1)','https://www.instagram.com.evil.test/reel/Ab12/','https://user@www.instagram.com/reel/Ab12/','https://www.instagram.com/p/Ab12/','http://www.instagram.com/reel/Ab12/'])assert.equal(cleanReel({...row,url},'manual:entered'),null);
  for(const views of [true,'10000000',NaN,Infinity,10000000.5])assert.equal(cleanReel({...row,views},'manual:entered'),null);
});
test('import cannot assign an API source and note/date are bounded',()=>{
  const clean=cleanReel({...row,source:'auto:filtered',note:'a'.repeat(1000),checked_at:'invalid'},'manual:import');
  assert.equal(clean.source,'manual:import');assert.equal(clean.note.length,500);assert.equal(clean.checked_at,null);
});
test('manual annotation does not replace API observation',()=>{
  assert.equal(combine([cleanReel(row,'auto:filtered')],[cleanReel(row,'manual:entered')]).length,2);
});
test('show only the highest-view reel per account without deleting observations',()=>{
  const input=[{username:'wisdm',views:12000000},{username:'WISDM',views:37000000},{username:'other',views:15000000}];
  const result=onePerAccount(input);
  assert.equal(result.length,2);
  assert.equal(result.find(r=>r.username.toLowerCase()==='wisdm').views,37000000);
  assert.equal(input.length,3);
});
