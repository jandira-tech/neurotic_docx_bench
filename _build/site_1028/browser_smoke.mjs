// Browser integration check. New R2 requests use local build/ bytes for pre-upload review.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
const home=path.dirname(fileURLToPath(import.meta.url));
const base='http://127.0.0.1:8178';
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless:true});
try {
const context=await browser.newContext({viewport:{width:1600,height:1000}});
let localAssets=0;
context.on('response',response=>{
  if(response.url().startsWith(base+'/__assets/')) {
    assert.equal(response.status(),200,response.url());localAssets++;
  }
});
await context.route('https://pub-92c80eda1059428394970066c8500eda.r2.dev/**', async route=>{
  const key=new URL(route.request().url()).pathname.slice(1);
  if (/^(d2p_v1|redlines_0929ar|wordcraft1014)\//.test(key)) {
    const response=await route.fetch({url:base+'/__assets/'+key});
    assert.equal(response.status(),200,key);
    localAssets++;
    return route.fulfill({response});
  }
  return route.continue();
});
const page=await context.newPage();
const errors=[];
page.on('pageerror',error=>errors.push(error.message));
const health=await page.request.get(base+'/__health');assert.equal(health.status(),200);
const specs=[['index.html','v1'],['index.html','wordcraft_convert'],['redlines/index.html','redlines'],['redlines/index.html','wordcraft_compare']];
const checked=[];
for(const [rel,set] of specs){
  const file=path.join(home,'build','cases_'+set+'.json');
  if(!fs.existsSync(file))continue;
  console.log('Checking '+set);
  const rows=JSON.parse(fs.readFileSync(file));
  const row=rows.find(r=>r.shown.length===3&&Object.keys(r.pages).length>1)||rows[0];
  await page.goto(base+'/'+rel+'#'+row.group+'/'+row.case,{waitUntil:'networkidle'});
  assert.equal(await page.locator('script[src="/@console-pipe/client"]').count(),1);
  await page.waitForFunction(()=>document.querySelectorAll('#grid img').length>0);
  assert.match(await page.locator('#pageinfo').textContent(),new RegExp('of '+row.page_counts.reference+'$'));
  assert.ok((await page.locator('.colhead').allTextContents()).some(t=>t.includes('Pixel')));
  for(const [key,score] of Object.entries(row.scores)){
    if(score.pixel==null)continue;
    const heading=page.locator('.colhead').filter({hasText:row.versions[key]});
    assert.ok((await heading.count())>0,key+' version');
  }
  // The viewer deliberately lazy-loads offscreen pages. Scroll each into view before asserting.
  for(const img of await page.locator('#grid img').all()) {
    await img.scrollIntoViewIfNeeded();
    await page.waitForFunction(img=>img.complete&&img.naturalWidth>0,await img.elementHandle());
  }
  await page.locator('#grid img').first().scrollIntoViewIfNeeded();
  assert.equal(await page.locator('#grid img').count(),Object.values(row.pages).flat().filter(Boolean).length);
  assert.equal(await page.locator('.colhead a').count(),Object.keys(row.pdfs).length);
  await page.screenshot({path:path.join(home,'smoke_'+set+'.jpg'),fullPage:false,type:'jpeg',quality:80});
  for(const link of await page.locator('.colhead a').all()) {
    const url=await link.evaluate(a=>a.href);const response=await page.request.get(url);
    assert.equal(response.status(),200,url);assert.equal((await response.body()).subarray(0,5).toString(),'%PDF-');
  }
  await page.locator('#fxClear').click();
  // Filters reduce the table to one case and preserve the Pixel sort control.
  await page.locator('#fxGroup').selectOption(row.group);
  await page.locator('#filter').fill(row.case);
  await page.locator('#viewToggle').click();
  await page.waitForSelector('#scores table');
  const pixel=page.locator('#scores th[data-c]').filter({hasText:/^Pixel/}).first();
  await pixel.click();
  assert.ok((await pixel.getAttribute('class')).includes('sorted'));
  assert.equal(await page.locator('#scores tbody tr').count(),1);
  await page.screenshot({path:path.join(home,'smoke_'+set+'_scores.jpg'),fullPage:false,type:"jpeg",quality:80});
  // Verify descending and ascending numerical Pixel order on the two lowest scores.
  const sortCheck=await page.evaluate(group=>{
    const pool=DATA.filter(c=>c.group===group);
    const engine=ENGINES.find(([k])=>k!=='reference'&&pool.filter(c=>c.scores[k]?.pixel!=null).length>1)[0];
    const scores=pool.map(c=>c.scores[engine]?.pixel).filter(v=>v!=null).sort((a,b)=>a-b);
    state.filter='';Object.assign(state.fx,{group,pages:'',eng:engine,metric:'pixel',max:String(scores.find(v=>v>scores[0]) ?? scores[1]),differ:false});state.view='scores';state.sort={col:0,dir:1};render();
    const engines=ENGINES.filter(([k])=>k!=='reference'&&visibleCases().some(([c])=>!(c.dropped||[]).includes(k)));
    return {engine,col:3+engines.findIndex(([k])=>k===engine)*TABLE_COLS.length};
  },row.group);
  await page.locator(`#scores th[data-c="${sortCheck.col}"]`).click();
  const descending=await page.evaluate(engine=>[...document.querySelectorAll('#scores tbody tr')].map(tr=>DATA[+tr.dataset.i].scores[engine].pixel),sortCheck.engine);
  assert.ok(descending.length>=2);
  assert.ok(new Set(descending).size>1);
  assert.deepEqual(descending,[...descending].sort((a,b)=>b-a));
  await page.locator(`#scores th[data-c="${sortCheck.col}"]`).click();
  const ascending=await page.evaluate(engine=>[...document.querySelectorAll('#scores tbody tr')].map(tr=>DATA[+tr.dataset.i].scores[engine].pixel),sortCheck.engine);
  assert.deepEqual(ascending,[...ascending].sort((a,b)=>a-b));
  await page.evaluate(set=>console.log('SMOKE PASS: '+set+' images, PDF links, versions, Pixel sorting'),set);
  await page.waitForTimeout(200);
  checked.push({set,case:row.group+'/'+row.case,reference_pages:row.page_counts.reference,shown:row.shown.length});
}
// Historical selections have no Pixel score column or header label.
for(const rel of ['index.html','redlines/index.html']){
  await page.goto(base+'/'+rel,{waitUntil:'networkidle'});
  const legacy=await page.evaluate(()=>{
    const c=DATA.find(c=>!c.set&&Object.values(c.scores).every(s=>s.pixel==null)
      && !DATA.some(other=>other!==c&&other.group===c.group&&other.case.toLowerCase().includes(c.case.toLowerCase())));
    state.filter=c.case;Object.assign(state.fx,{group:c.group,pages:'',eng:'',metric:'',max:'',differ:false});state.sel=DATA.indexOf(c);state.view='scores';render();return c.case;
  });
  assert.equal(await page.locator('#scores tbody tr').count(),1);
  assert.equal(await page.locator('#scores th[data-c]').filter({hasText:/^Pixel/}).count(),0);
  checked.push({legacy,viewer:rel,pixel_column:false});
}
await page.waitForTimeout(300); // allow console-pipe's normal batching to reach the terminal
assert.deepEqual(errors,[]);
fs.writeFileSync(path.join(home,'browser_smoke.json'),JSON.stringify({checked,localAssets,healthStatus:health.status(),pageErrors:errors},null,2));
console.log(JSON.stringify({checked:checked.length,localAssets,pageErrors:errors}));
} finally { await browser.close(); }
