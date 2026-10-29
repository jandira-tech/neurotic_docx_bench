// Real Playwright integration smoke; console capture uses vite-plugin-console-pipe.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
const home=path.dirname(fileURLToPath(import.meta.url));
const base='http://127.0.0.1:8180';
function dataFrom(file) {
  const html=fs.readFileSync(file,'utf8'), start=html.indexOf('const DATA = ')+'const DATA = '.length;
  return JSON.parse(html.slice(start,html.indexOf(';\n',start)));
}
const data=dataFrom(path.join(home,'preview/redlines/index.html'));
const redlinesHTML=fs.readFileSync(path.join(home,'preview/redlines/index.html'),'utf8');
const conversionHTML=fs.readFileSync(path.join(home,'preview/index.html'),'utf8');
const conversionData=dataFrom(path.join(home,'preview/index.html'));
const retainedURLs=new Set([...data,...conversionData].flatMap(c=>[...Object.values(c.pages||{}).flat(),...Object.values(c.pdfs||{})]).filter(url=>typeof url==='string'&&url.startsWith('https://pub-92c80eda1059428394970066c8500eda.r2.dev/')&&!/\/renew1030\//.test(url)));
const allKeys=[...new Set([redlinesHTML,conversionHTML].flatMap(html=>JSON.parse(html.match(/const ENGINES = (.*?);\n/)[1]).map(([key])=>key)))];
const records=JSON.parse(fs.readFileSync(path.join(home,'build/cases.json'),'utf8'));
const oldKeys=['jubarte-0.11.0','jubarte-0.12.0','jubarte-093','docxodus-12.6.5','docxodus-13.0.0'];
const targets=['jubarte-rust','docxodus'];
const metrics=['pixel','jaccard','ssim','text_boundary'];
const success=c=>targets.every(k=>c.pages[k]?.length && metrics.every(m=>c.scores[k]?.[m]!=null));
const groups=['redlines/tracking_without_comments','redlines/with_comments_tracking','wordcraft1014/compare','ar/accept_all','ar/reject_all'];
const samples=groups.map(group=>data.find(c=>c.group===group&&success(c)));
assert.ok(samples.every(Boolean),'Expected successful legacy, Wordcraft and both accept/reject groups with metrics');
for(const group of ['ar/accept_all','ar/reject_all']) assert.equal(data.filter(c=>c.group===group).length,400,group);
const failures=[
  ...['ar/accept_all','ar/reject_all'].map(group=>records.find(r=>r.group===group&&r.tool==='superdoc'&&r.failure_type==='generation')),
  records.find(r=>r.failure_type==='word'),
];
assert.ok(failures.every(Boolean),'Expected SuperDoc generation failures in both modes and a Word failure');
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
let coveragePage,coverageActive=false;
function saveCoverage(entries) {
  // Preserve upstream's raw V8 source/functions/ranges before any optional filtering.
  fs.writeFileSync(path.join(home,'browser_coverage.json'),JSON.stringify(entries));
  return entries.filter(entry=>typeof entry.url==='string'&&entry.url.startsWith(base+'/')
    &&!entry.url.includes('/@')&&typeof entry.source==='string'&&entry.source.includes('const DATA = '));
}
try {
  const context=await browser.newContext({viewport:{width:1600,height:1000}});
  const errors=[],badAssets=[],requests=[],remoteRequests=[],unexpectedRemote=[],checked=[],coverage=[];
  await context.route('**/*',route=>{
    const url=route.request().url();
    if (/^https?:/.test(url)&&!url.startsWith(base+'/')) {
      if(retainedURLs.has(url)) {remoteRequests.push(url);return route.continue();}
      unexpectedRemote.push(url);return route.abort();
    }
    return route.continue();
  });
  await context.addInitScript(({allKeys,defaultKeys,selection})=>{
    localStorage.clear();
    const keys=[...defaultKeys,...(new URLSearchParams(location.search).get('lanes')||'').split(',')];
    localStorage.setItem('ec.state',JSON.stringify({on:Object.fromEntries(allKeys.map(k=>[k,keys.includes(k)])),sel:selection,zoom:420,shown:100,filter:'',view:'viewer'}));
  },{allKeys,defaultKeys:['reference','jubarte',...targets,...oldKeys],selection:data.indexOf(samples[0])});
  const page=await context.newPage();
  coveragePage=page;
  page.on('pageerror',error=>errors.push(error.message));
  page.on('response',response=>{
    if(retainedURLs.has(response.url())&&response.status()!==200)badAssets.push(response.url());
    if(response.url().startsWith(base+'/__assets/')) {
      requests.push({url:response.url(),status:response.status()});
      if(response.status()!==200)badAssets.push(response.url());
    }
  });
  const health=await page.request.get(base+'/__health');
  assert.equal(health.status(),200);
  assert.deepEqual(await health.json(),{ok:true});
  await page.coverage.startJSCoverage({resetOnNavigation:false,reportAnonymousScripts:true});
  coverageActive=true;
  async function openCase(row,extra=[]) {
    // Lane state is set before navigation so the first render uses only selected local assets.
    await page.goto(base+'/redlines/?smoke='+encodeURIComponent(row.group)+'&lanes='+encodeURIComponent(extra.join(','))+'#'+row.group+'/'+row.case,{waitUntil:'networkidle'});
    await page.evaluate(keys=>{
      for(const [k] of ENGINES)state.on[k]=keys.includes(k);
      render();
    },['reference',...targets,...oldKeys,...extra]);
    await page.waitForFunction(identity=>DATA[state.sel].group+'/'+DATA[state.sel].case===identity,row.group+'/'+row.case);
    assert.equal(await page.locator('script[src="/@console-pipe/client"]').count(),1);
    const visible=await page.locator('.colhead b').allTextContents();
    for(const old of oldKeys)assert.ok(!visible.includes(old),'Stale lane visible: '+old);
    return visible;
  }
  async function imagesAndPDFs() {
    for(const img of await page.locator('#grid img').all()) {
      await img.scrollIntoViewIfNeeded();
      await page.waitForFunction(img=>img.complete&&img.naturalWidth>0,await img.elementHandle());
    }
    if(await page.locator('#grid img').count()) await page.locator('#grid img').first().scrollIntoViewIfNeeded();
    const pdfs=[];
    for(const link of await page.locator('.colhead a').all()) {
      const url=await link.evaluate(a=>a.href),response=await page.request.get(url);
      assert.equal(response.status(),200,url);
      assert.equal((await response.body()).subarray(0,5).toString(),'%PDF-',url);
      pdfs.push(url);
    }
    return pdfs;
  }
  async function oneCaseTable(row) {
    await page.locator('#fxClear').click();
    await page.locator('#fxGroup').selectOption(row.group);
    await page.locator('#filter').fill(row.case);
    await page.locator('#viewToggle').click();
    await page.waitForSelector('#scores table');
    assert.equal(await page.locator('#scores tbody tr').count(),1);
    const labels=await page.locator('#scores .eng').allTextContents();
    for(const old of oldKeys)assert.ok(!labels.some(label=>label.includes(old)),'Stale table lane: '+old);
  }
  for(const row of samples) {
    const active=row.group.startsWith('ar/')?['superdoc']:[];
    await openCase(row,active);
    const headings={};
    for(const [key,label,version] of [['jubarte-rust','jubarte','0.14.0'],['docxodus','docxodus','14.2.0']]) {
      const header=page.locator('.colhead').filter({has:page.locator('b',{hasText:new RegExp('^'+label+'$')})});
      assert.equal(await header.count(),1,key);
      const text=await header.innerText();
      assert.ok(text.includes(version),text);
      for(const [metric,label] of [['pixel','Pixel'],['jaccard','J'],['ssim','SSIM'],['text_boundary','TB']]) {
        assert.ok(text.includes(' · '+label+' '+row.scores[key][metric].toFixed(1)+'%'),text);
      }
      assert.equal(await header.locator('a').count(),1,key+' PDF');
      headings[key]=text;
    }
    const actual=await page.evaluate(()=>DATA[state.sel]);
    assert.deepEqual(actual.shown,row.shown);
    assert.match(await page.locator('#pageinfo').innerText(),new RegExp('of '+row.page_counts.reference+'$'));
    const pdfs=await imagesAndPDFs();
    const slug=row.group.replaceAll('/','_');
    await page.screenshot({path:path.join(home,'smoke_'+slug+'.jpg'),type:'jpeg',quality:80});
    await oneCaseTable(row);
    for(const version of ['0.14.0','14.2.0'])assert.ok((await page.locator('#scores .eng').allTextContents()).some(t=>t.includes(version)));
    for(const metric of ['Pixel','J','SSIM','TB'])assert.ok((await page.locator('#scores th[data-c]').allTextContents()).some(t=>t.startsWith(metric)));
    await page.screenshot({path:path.join(home,'smoke_'+slug+'_scores.jpg'),type:'jpeg',quality:80});
    await page.evaluate(group=>{
      state.filter='';Object.assign(state.fx,{group,pages:'',eng:'',metric:'',max:'',differ:false});
      state.view='scores';state.shown=DATA.length;state.sort={col:0,dir:1};render();
    },row.group);
    const column=await page.evaluate(()=>{
      const rows=visibleCases().map(([c])=>c);
      const engines=ENGINES.filter(([k])=>k!=='reference'&&rows.some(c=>!(c.dropped||[]).includes(k)));
      const tableCols=TABLE_COLS.filter(m=>m!=='pixel'||rows.some(c=>Object.values(c.scores).some(s=>s.pixel!=null)));
      return 3+engines.findIndex(([k])=>k==='jubarte-rust')*tableCols.length;
    });
    for(const direction of [-1,1]) {
      await page.locator(`#scores th[data-c="${column}"]`).click();
      const values=await page.evaluate(()=>[...document.querySelectorAll('#scores tbody tr')].map(tr=>DATA[+tr.dataset.i].scores['jubarte-rust']?.pixel).filter(v=>v!=null));
      assert.ok(new Set(values).size>1,'Pixel sort requires distinct values');
      assert.deepEqual(values,[...values].sort((a,b)=>direction*(a-b)));
    }
    await page.evaluate(identity=>console.log('SMOKE PASS '+identity+' versions, metrics, images, PDFs, Pixel descending/ascending'),row.group+'/'+row.case);
    checked.push({group:row.group,case:row.case,shown:row.shown,headings,pdfs,pixelSort:['descending','ascending']});
  }
  for(const failure of failures) {
    const row=data.find(c=>c.group===failure.group&&c.case===failure.case),key=failure.column;
    assert.ok(row,'Failure row retained');
    assert.equal(row.scores[key].pixel,0);
    assert.equal((row.pages[key]||[]).filter(Boolean).length,0);
    assert.ok(!row.pdfs?.[key]);
    assert.ok(row.errors?.[key]);
    await openCase(row,[key]);
    const label=key==='superdoc'?'SuperDoc':key==='jubarte-rust'?'jubarte':key;
    const heading=page.locator('.colhead').filter({has:page.locator('b',{hasText:new RegExp('^'+label+'$')})});
    assert.equal(await heading.count(),1,'Failure lane visible');
    assert.match(await heading.innerText(),/Pixel 0\.0%/);
    assert.match(await heading.innerText(),/no scored PDF/);
    assert.equal(await heading.locator('a').count(),0,'Failure has no PDF');
    const column=await page.evaluate(label=>[...document.querySelectorAll('.colhead b')].findIndex(b=>b.textContent===label),label);
    const lane=page.locator('#grid .col').nth(column);
    assert.equal(await lane.locator('img').count(),0,'Failure has no candidate images');
    assert.ok(await lane.locator('.missing').count()>0);
    await imagesAndPDFs();
    await heading.scrollIntoViewIfNeeded();
    const slug=failure.group.replaceAll('/','_')+'_'+key+'_'+failure.failure_type;
    await page.screenshot({path:path.join(home,'smoke_failure_'+slug+'.jpg'),type:'jpeg',quality:80});
    await oneCaseTable(row);
    const failureCell=await page.evaluate(key=>{
      const pool=visibleCases().map(([c])=>c),c=pool[0];
      const engines=ENGINES.filter(([k])=>k!=='reference'&&pool.some(c=>!(c.dropped||[]).includes(k)));
      const cols=TABLE_COLS.filter(m=>m!=='pixel'||pool.some(c=>Object.values(c.scores).some(s=>s.pixel!=null)));
      return {index:3+engines.findIndex(([k])=>k===key)*cols.length+cols.indexOf('pixel'),pixel:c.scores[key]?.pixel};
    },key);
    assert.equal(failureCell.pixel,0);
    assert.equal((await page.locator('#scores tbody tr td').nth(failureCell.index).innerText()).trim(),'0.0%');
    await page.screenshot({path:path.join(home,'smoke_failure_'+slug+'_scores.jpg'),type:'jpeg',quality:80});
    checked.push({group:row.group,case:row.case,column:key,failureType:failure.failure_type,pixel:0,candidateAssets:0});
    await page.evaluate(summary=>console.log('SMOKE PASS failure '+summary),slug);
  }
  // The unchanged conversion copy provides local navigation to the renewed redlines viewer.
  const conversion=conversionData.find(c=>c.pages.jubarte?.[0]?.includes('/renew1028/'));
  assert.ok(conversion,'Retained conversion sample with local assets');
  await page.goto(base+'/#'+conversion.group+'/'+conversion.case,{waitUntil:'networkidle'});
  const nav=page.locator('a[href="redlines/"]');
  assert.ok(await nav.count()>0);
  await nav.first().click();
  await page.waitForURL(base+'/redlines/**');
  assert.equal(await page.locator('script[src="/@console-pipe/client"]').count(),1);
  coverage.push(...await page.coverage.stopJSCoverage());
  coverageActive=false;
  const viewerCoverage=saveCoverage(coverage);
  await page.waitForTimeout(500); // normal console-pipe batching
  assert.deepEqual(errors,[]);
  assert.deepEqual(badAssets,[]);
  assert.deepEqual(unexpectedRemote,[]);
  fs.writeFileSync(path.join(home,'browser_smoke.json'),JSON.stringify({healthStatus:health.status(),checked,localAssetRequests:requests,pageErrors:errors,badAssets,retainedRemoteRequests:remoteRequests,unexpectedRemote,coverageFile:'browser_coverage.json'},null,2));
  console.log(JSON.stringify({checked:checked.length,localAssetRequests:requests.length,pageErrors:errors,coverageScripts:viewerCoverage.length}));
} finally {
  if(coverageActive&&coveragePage) {
    try {
      const partial=saveCoverage(await coveragePage.coverage.stopJSCoverage());
      console.log('Partial browser coverage saved after failed smoke: '+partial.length+' viewer scripts (raw V8 source/functions/ranges; no source-level percentage conversion)');
    } catch(error) {
      console.error('Could not capture partial browser coverage: '+error.message);
    }
  }
  await browser.close();
}

