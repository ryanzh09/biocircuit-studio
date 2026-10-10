/* Full browser regression checks; uses an isolated Chrome profile. */
const fs=require('fs'), path=require('path'), assert=require('assert');
const {chromium}=require('playwright');
const BASE_URL=process.env.APP_URL || 'http://127.0.0.1:8517';
const ROOT=path.resolve(__dirname,'..');
const OUTPUT=path.join(__dirname,'output'); fs.mkdirSync(OUTPUT,{recursive:true});
const reports=[];
function passed(name,detail=''){reports.push({name,status:'pass',detail}); console.log('PASS',name,detail);}
(async()=> {
 const browser=await chromium.launch({...(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {}),headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage();
 const errors=[];
  await page.screenshot({path:path.join(OUTPUT,'initial.png')});
 page.on('pageerror',e=>errors.push(e.message));
 try {
  await page.goto(BASE_URL);
  await page.getByRole('button',{name:'Open Chip Design Workshop',exact:true}).click();
  await page.getByRole('combobox',{name:/Assay preset/}).click();
  await page.getByRole('option',{name:'Endothelial drug-response barrier assay',exact:true}).click();
  await page.getByRole('textbox',{name:'Control Condition',exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelector('input[aria-label="Control Condition"]')?.value==='Vehicle control');
  assert.equal(await page.getByRole('textbox',{name:'Time Points / Measurement Schedule',exact:true}).inputValue(),'');
  await page.screenshot({path:path.join(OUTPUT,'workshop-input.png'),fullPage:true});
  const fill=async(name,value)=>{const el=page.getByRole('textbox',{name,exact:true});await el.fill(value);await el.press('Tab');};
  await fill('Biological Sample Baseline','Pretreatment after stabilization');
  await fill('Time Points / Measurement Schedule','baseline, 24 h, 48 h');
  await fill('Active area (cm²)','0.45');
  await fill('Measurement Settings','5 Hz to 100 kHz; 10 mV rms');
  await fill('Data Export Plan','Workflow JSON and spectra/results CSV');
  await fill('Experimental Metadata Plan','Record sample ID, chip ID, condition, time point, biological replicate, and settings.');
  await page.getByRole('button',{name:'Generate Workflow Draft',exact:true}).click();
  await page.getByText('Workflow status: draft awaiting researcher review',{exact:true}).waitFor();
  await page.screenshot({path:path.join(OUTPUT,'workflow-summary.png'),fullPage:true});
  passed('Preset, plan entry, local generation and draft guidance');
  for (const [view,name] of [['Build View','build'],['Operate View','operate'],['Analyze View','analyze'],['Export','export']]) {
   await page.getByRole('button',{name:view,exact:true}).click();
   await page.getByRole('heading',{name:view,exact:true}).waitFor();
   await page.screenshot({path:path.join(OUTPUT,`workflow-${name}.png`),fullPage:true});
  }
  passed('All output views render');
  const dl=page.waitForEvent('download'); await page.getByRole('button',{name:'Download JSON',exact:true}).click();
  const download=await dl; const jsonPath=path.join(OUTPUT,'browser-workflow.json');await download.saveAs(jsonPath);
  const workflow=JSON.parse(fs.readFileSync(jsonPath,'utf8'));
  assert.equal(workflow.fit_lab_template.control_condition,'Vehicle control');
  assert.equal(workflow.fit_lab_template.measurement_schedule,'baseline, 24 h, 48 h');
  assert.equal(workflow.fit_lab_template.active_area_cm2,0.45);
  passed('Workflow JSON download preserves entered planning fields');
  await page.getByRole('button',{name:'Open Workflow in Fit Lab',exact:true}).click();
  await page.getByRole('heading',{name:'Fit Lab',exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelectorAll('iframe').length>0);
  let frame;
  for(let i=0;i<50;i++) { frame=page.frames().find(f=>f!==page.mainFrame());if(frame && await frame.locator('#mainChart').count())break; await new Promise(r=>setTimeout(r,100)); }
  assert(frame);
  await frame.waitForFunction(()=>typeof chart!=='undefined' && chart && chart.data.datasets.length===2);
  assert.equal(await frame.locator('#ctx-active_area_cm2').inputValue(),'0.45');
  assert.equal(await frame.locator('#ctx-control_condition').inputValue(),'Vehicle control');
  assert.equal(await frame.locator('#ctx-sample_id').inputValue(),'');
  assert.equal(await frame.locator('#legend-exp').textContent(),'Demo data');
  assert((await frame.locator('#fit-review-text').textContent()).includes('diverges'));
  await page.screenshot({path:path.join(OUTPUT,'fitlab-demo.png'),fullPage:true});
  passed('Fit Lab handoff, empty sample placeholders, demo-specific guidance and chart');
  await frame.locator('#fit-btn').click();
  await frame.waitForFunction(()=>lastFitParams!==null,{timeout:30000});
  const fit=await frame.evaluate(()=>({p:lastFitParams,shown:getParams(),rows:exportRows(),firstY:chart.data.datasets[1].data[0].y,modelY:Math.log10(lastFitModel.mag[0])}));
  assert.equal(fit.shown.Rb,fit.p[0]);assert.equal(fit.shown.CLER,fit.p[1]);assert(Math.abs(fit.firstY-fit.modelY)<1e-12);
  assert(fit.p.every(Number.isFinite));
  assert(!(await frame.locator('#fit-review-text').textContent()).includes('diverges'));
  passed('Auto-fit preserves exact model/parameter/export agreement');
  await frame.locator('#ctx-active_area_cm2').fill('0.9');
  const scaled=await frame.evaluate(()=>exportRows());
  assert(Math.abs(scaled[1][scaled[0].indexOf('TEER_Ohm_cm2')]-fit.p[1]*0.9)<1e-8);
  await frame.locator('#ctx-active_area_cm2').fill('0.45');
  passed('Changing sensing area updates derived values and exported metadata');
  await frame.locator('#boot-n').fill('20');
  await frame.locator('#boot-btn').click();
  await frame.waitForFunction(()=>bootResults!==null,{timeout:45000});
  assert.equal(await frame.evaluate(()=>bootResults.samples.length),20);
  passed('Bootstrap uncertainty completes for current spectrum');
  // Changing data must invalidate the current fit and its bootstrap.
  await frame.locator('#tp-select').selectOption('0');
  assert(await frame.locator('#boot-btn').isDisabled());
  assert.equal(await frame.evaluate(()=>lastFitParams),null);
  passed('Changing spectra clears stale fit and bootstrap');
  // Reuse two existing built-in demo spectra; no private laboratory fixture.
  const csvText=await frame.evaluate(()=>{
   const rows=[DATA.freq];
   for(let k=0;k<2;k++) rows.push(DATA.re[k].map((r,i)=>Math.hypot(r,DATA.im[k][i])),DATA.re[k],DATA.im[k],DATA.re[k].map((r,i)=>Math.atan2(DATA.im[k][i],r)*180/Math.PI));
   return rows.map(r=>r.join(',')).join('\n');
  });
  await frame.locator('#file-input').setInputFiles({name:'existing-demo-roundtrip.csv',mimeType:'text/csv',buffer:Buffer.from(csvText)});
  await frame.waitForFunction(()=>datasetSource==='uploaded');
  assert.equal(await frame.evaluate(()=>fitHistory.length),0);
  assert(await frame.locator('#save-btn').isDisabled());
  assert.equal(await frame.locator('#legend-exp').textContent(),'Uploaded data (unverified)');
  assert(!(await frame.locator('#fit-review-text').textContent()).includes('diverges'));
  passed('Existing demo spectra round-trip through CSV upload with unverified provenance');
  await frame.locator('#tp-select').selectOption('1');
  await frame.locator('#ctx-sample_id').fill('sample,"A"');
  await frame.locator('#ctx-sample_condition').fill('treated');
  await frame.locator('#ctx-time_point').fill('24 h');
  await frame.locator('#ctx-biological_replicate').fill('replicate-1');
  await frame.locator('#ctx-chip_id').fill('chip-01');
  await frame.locator('#ctx-measurement_settings').fill('5 Hz-100 kHz; 10 mV');
  assert.equal(await frame.locator('#legend-exp').textContent(),'Uploaded data (unverified)');
  const selected=await frame.locator('#tp-select').inputValue();
  await frame.locator('#tp-select').selectOption('0');
  assert.equal(await frame.locator('#ctx-sample_id').inputValue(),'');
  await frame.locator('#tp-select').selectOption(selected);
  assert.equal(await frame.locator('#ctx-sample_id').inputValue(),'sample,"A"');
  assert.equal(await frame.locator('#ctx-data_provenance').inputValue(),'unverified');
  passed('Sample metadata and unverified provenance persist per spectrum');
  await frame.locator('#fit-btn').click();
  await frame.waitForFunction(()=>lastFitParams!==null,{timeout:30000});
  const rows=await frame.evaluate(()=>exportRows());
  const idx=k=>rows[0].indexOf(k);
  assert.equal(rows[1][idx('sample_id')],'sample,"A"');
  assert.equal(rows[1][idx('time_point')],'24 h');
  assert.equal(rows[1][idx('control_condition')],'Vehicle control');
  assert.equal(rows[1][idx('active_area_cm2')],'0.45');
  assert.equal(rows[1][idx('data_provenance')],'unverified');
  const fitdl=page.waitForEvent('download');await frame.locator('#save-btn').click();await (await fitdl).saveAs(path.join(OUTPUT,'browser-fit-results.csv'));
  passed('Fitted CSV download contains spectrum-specific metadata');
  // Bad input must leave prior valid data and results intact.
  const prior=await frame.evaluate(()=>JSON.stringify(DATA));
  await frame.locator('#file-input').setInputFiles({name:'bad.csv',mimeType:'text/csv',buffer:Buffer.from('1,2,3\n4,5,6')});
  await frame.waitForFunction(()=>document.getElementById('file-status').textContent.includes('Could not read file'));
  assert.equal(await frame.evaluate(()=>JSON.stringify(DATA)),prior);
  assert.equal(await frame.evaluate(()=>fitHistory.length),1);
  passed('Malformed CSV reports an error and preserves valid dataset/results');
  for (const id of ['phase','nyquist','bode']) {await frame.locator('#tab-'+id).click();assert(await frame.evaluate(()=>chart.data.datasets.length>=2));}
  passed('All three plot modes render');
  await page.screenshot({path:path.join(OUTPUT,'fitlab-uploaded-demo.png'),fullPage:true});
  // Verify JSON reload in a fresh session, independently of in-memory handoff.
  const reloadPage=await context.newPage();await reloadPage.goto(BASE_URL);
  await reloadPage.getByRole('button',{name:'Open Fit Lab',exact:true}).click();
  await reloadPage.locator('input[type=file]').setInputFiles(jsonPath);
  await reloadPage.getByText('0.45 cm²',{exact:true}).waitFor();
  passed('Downloaded workflow reloads in a fresh Fit Lab session');
  await page.getByRole('button',{name:'Home',exact:true}).click();
  await page.getByRole('button',{name:'Open Chip Design Workshop',exact:true}).click();
  await page.getByRole('button',{name:'Edit Input',exact:true}).click();
  await page.getByRole('textbox',{name:'Time Points / Measurement Schedule',exact:true}).waitFor();
  assert.equal(await page.getByRole('textbox',{name:'Time Points / Measurement Schedule',exact:true}).inputValue(),'baseline, 24 h, 48 h');
  passed('Edit Input restores entered planning fields after navigation');
  await page.getByRole('button',{name:'Reset',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('input[aria-label="Control Condition"]')?.value==='');
  assert.equal(await page.getByRole('textbox',{name:'Time Points / Measurement Schedule',exact:true}).inputValue(),'');
  passed('Reset clears plan fields in the real browser');
  await reloadPage.close();
  assert.deepEqual(errors,[]);
  passed('No uncaught browser JavaScript errors');
  // Standalone copy works with browser networking disabled (Chart.js is local).
  const offline=await browser.newContext({offline:true,viewport:{width:1200,height:900}});
  const op=await offline.newPage();await op.goto('file://'+path.join(ROOT,'software/microfluidic-eis-agent/fitlab_assets/eis_simulator_v2.html'));
  await op.waitForFunction(()=>typeof chart!=='undefined' && chart && chart.data.datasets.length===2);
  await op.screenshot({path:path.join(OUTPUT,'fitlab-offline.png'),fullPage:true});
  passed('Standalone Fit Lab chart works offline');
  await offline.close();
 } catch(e) { reports.push({name:'Failure',status:'fail',detail:e.stack}); console.error(e.stack);await page.screenshot({path:path.join(OUTPUT,'browser-failure.png'),fullPage:true}).catch(()=>{}); process.exitCode=1; }
 finally {fs.writeFileSync(path.join(OUTPUT,'browser-test-results.json'),JSON.stringify(reports,null,2));await browser.close();}
})();
