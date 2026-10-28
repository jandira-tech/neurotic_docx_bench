// Real Playwright integration smoke; console capture uses vite-plugin-console-pipe.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
const home = path.dirname(fileURLToPath(import.meta.url));
const base = 'http://127.0.0.1:8179';
const rows = JSON.parse(fs.readFileSync(path.join(home, 'build/cases_d2p_jubarte.json')));
const html = fs.readFileSync(path.join(home, 'preview/index.html'), 'utf8');
const engines = JSON.parse(html.match(/const ENGINES = (.*?);\n/)[1]);
const source = fs.readFileSync(path.resolve(home,'../../index.html'),'utf8');
const sourceStart = source.indexOf('const DATA = ') + 'const DATA = '.length;
const sourceData = JSON.parse(source.slice(sourceStart,source.indexOf(';\n',sourceStart)));
const retainedSource = sourceData.find(c=>c.group==='v1/clean');
const hasMetrics = row => ['pixel', 'jaccard', 'ssim', 'text_boundary'].every(k => row.scores.jubarte?.[k] != null);
const specs = [
  rows.find(r => r.group === 'cases' && hasMetrics(r) && !rows.some(other => other !== r && other.group === r.group && other.case.toLowerCase().includes(r.case.toLowerCase()))),
  rows.find(r => r.group === 'corpus/clean' && r.shown.length > 3 && r.shown.length <= 8 && hasMetrics(r)),
  rows.find(r => r.group === 'corpus/tracking_without_comments' && hasMetrics(r)),
  rows.find(r => r.group === 'corpus/with_comments_clean' && r.shown.length > 3 && r.shown.length <= 8 && hasMetrics(r)),
  rows.find(r => r.group === 'wordcraft1014/convert' && r.shown.length === 3 && hasMetrics(r)),
];
assert.ok(specs.every(Boolean), 'Expected fixture, old cases and Wordcraft sample');
const browser = await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless:true});
try {
  const context = await browser.newContext({viewport:{width:1500,height:1000}});
  await context.addInitScript(engineKeys => {
    localStorage.clear();
    localStorage.setItem('ec.state', JSON.stringify({on:Object.fromEntries(engineKeys.map(k => [k, ['reference','jubarte'].includes(k)])), zoom:450, shown:100, filter:'', view:'viewer'}));
  }, engines.map(([key]) => key));
  const page = await context.newPage();
  const errors = [], badAssets = [], requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {
    if (response.url().startsWith(base+'/__assets/')) {
      requests.push({url:response.url(),status:response.status()});
      if(response.status() !== 200) badAssets.push(response.url());
    }
  });
  const health = await page.request.get(base+'/__health');
  assert.equal(health.status(),200);
  const checked = [];
  for(const row of specs) {
    await page.goto(base+'/?smoke='+encodeURIComponent(row.group)+'#'+row.group+'/'+row.case,{waitUntil:'networkidle'});
    await page.waitForFunction(identity=>DATA[state.sel].group+'/'+DATA[state.sel].case===identity,row.group+'/'+row.case);
    if(row.group === 'wordcraft1014/convert') {
      for(const key of ['jubarte-0.11.0','jubarte-0.12.0']) await page.locator(`#engines input[data-e="${key}"]`).check();
    }
    assert.equal(await page.locator('script[src="/@console-pipe/client"]').count(),1);
    const header = page.locator('.colhead').filter({has:page.locator('b', {hasText:/^jubarte$/})});
    assert.equal(await header.count(),1);
    const text = await header.innerText();
    assert.ok(text.includes('jubarte 0.14.0'),text);
    for(const metric of ['Pixel', 'J', 'SSIM', 'TB']) assert.ok(text.includes(' · '+metric+' '),text);
    assert.ok(!(await page.locator('.colhead b').allTextContents()).some(t=>/jubarte-0\.(11|12)\.0/.test(t)));
    const actual = await page.evaluate(() => {
      const c=DATA[state.sel];
      return {group:c.group,case:c.case,shown:c.shown,pages:c.pages.jubarte,reference:c.pages.reference,pageCounts:c.page_counts};
    });
    assert.equal(actual.case,row.case);
    assert.equal(actual.pages.length,actual.reference.length);
    assert.deepEqual(actual.shown ?? row.shown,row.shown);
    assert.match(await page.locator('#pageinfo').innerText(),new RegExp('of '+actual.pageCounts.reference+'$'));
    for(const img of await page.locator('#grid img').all()) {
      await img.scrollIntoViewIfNeeded();
      await page.waitForFunction(img=>img.complete&&img.naturalWidth>0,await img.elementHandle());
    }
    await page.locator('#grid img').first().scrollIntoViewIfNeeded();
    const pdfURL=await header.locator('a').getAttribute('href');
    const pdf=await page.request.get(new URL(pdfURL,base).href);
    assert.equal(pdf.status(),200);
    assert.equal((await pdf.body()).subarray(0,5).toString(),'%PDF-');
    await page.screenshot({path:path.join(home,'smoke_'+row.group.replaceAll('/','_')+'.jpg'),type:'jpeg',quality:80});
    await page.locator('#fxClear').click();
    await page.locator('#fxGroup').selectOption(row.group);
    await page.locator('#filter').fill(row.case);
    await page.locator('#viewToggle').click();
    await page.waitForSelector('#scores table');
    assert.equal(await page.locator('#scores tbody tr').count(),1);
    assert.ok((await page.locator('#scores .eng').allTextContents()).some(t=>t.includes('jubarte 0.14.0')));
    const metricLabels=await page.locator('#scores th[data-c]').allTextContents();
    for(const label of ['Pixel','J','SSIM','TB']) assert.ok(metricLabels.some(t=>t.startsWith(label)));
    await page.evaluate(group=>{
      state.filter='';state.fx.group=group;state.view='scores';state.sort={col:0,dir:1};render();
    },row.group);
    const column=await page.evaluate(()=>{
      const rows=visibleCases().map(([c])=>c);
      const engines=ENGINES.filter(([k])=>k!=='reference'&&rows.some(c=>!(c.dropped||[]).includes(k)));
      const tableCols=TABLE_COLS.filter(m=>m!=='pixel'||rows.some(c=>Object.values(c.scores).some(s=>s.pixel!=null)));
      return 3+engines.findIndex(([k])=>k==='jubarte')*tableCols.length;
    });
    for(const direction of [-1,1]) {
      await page.locator(`#scores th[data-c="${column}"]`).click();
      const values=await page.evaluate(()=>[...document.querySelectorAll('#scores tbody tr')].map(tr=>DATA[+tr.dataset.i].scores.jubarte?.pixel).filter(v=>v!=null));
      assert.deepEqual(values,[...values].sort((a,b)=>direction*(a-b)));
    }
    await page.evaluate(identity=>console.log('SMOKE PASS '+identity+' jubarte 0.14.0 Pixel/J/SSIM/TB, aligned images, page PDF and Pixel sorting'),row.group+'/'+row.case);
    checked.push({group:row.group,case:row.case,shown:row.shown,header:text,pdfStatus:pdf.status()});
  }
  // Confirm a current v1 case still uses its original scores/version/assets.
  await page.goto(base+'/?smoke=retained',{waitUntil:'networkidle'});
  const retained=await page.evaluate(()=>{
    const c=DATA.find(c=>c.group==='v1/clean');
    state.sel=DATA.indexOf(c);state.filter='';state.fx.group='v1/clean';state.view='viewer';render();
    return {case:c.case,version:c.versions.jubarte,pixel:c.scores.jubarte.pixel,
      versions:c.versions,scores:c.scores,pageCounts:c.page_counts};
  });
  assert.equal(retained.case,retainedSource.case);
  assert.deepEqual(retained.versions,retainedSource.versions);
  assert.deepEqual(retained.scores,retainedSource.scores);
  assert.deepEqual(retained.pageCounts,retainedSource.page_counts);
  await page.waitForTimeout(500); // normal console-pipe flush
  assert.deepEqual(errors,[]);
  assert.deepEqual(badAssets,[]);
  fs.writeFileSync(path.join(home,'browser_smoke.json'),JSON.stringify({healthStatus:health.status(),checked,retained,localAssetRequests:requests,pageErrors:errors,badAssets},null,2));
  console.log(JSON.stringify({checked:checked.length,localAssetRequests:requests.length,pageErrors:errors}));
} finally {
  await browser.close();
}
