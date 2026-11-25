// The frontend always opens at its canonical URL. Only API traffic is forwarded,
// verbatim, to the disposable backend started by record.py.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const fromWeb = require('node:module').createRequire(path.resolve('apps/web/package.json'));
const scene = process.argv[2], index = Number(scene)-1;
const names = ['quick-booker','custom-journey','grounding-safety','staff-enquiries','content-approval','tracing-evaluation'];
const base = 'http://127.0.0.1:5175', home = base+'/workspace/index.html';
const api = process.env.RECORD_API;
const out = path.resolve('demo-output'), state = path.resolve('.mira/recording');
const shots = path.join(out,'screenshots'), timeline = path.join(out,'timeline.json');
for (const dir of [shots,state]) fs.mkdirSync(dir,{recursive:true});
const results = fs.existsSync(timeline) ? JSON.parse(fs.readFileSync(timeline)) : {};
const expected = [
 'T01 image, validated surface, USD 315 total and deposit, saved private enquiry, decline and retry.',
 'Ten-day unpriced family plan, images, map, recommendations and specialist enquiry. T09 for two adults, USD 2,125 / 532.',
 'P01 payment policy, expired-rate handoff, internal financial refusal.',
 'Scene 01 reference, staff finance, revisions, trace, contacted status and persisted synthetic note.',
 'Staff draft stays private, approver publishes, public source becomes retrievable.',
 'Correlated trace stages and existing evaluation report, including exceptions and calibration status.'
];
if (scene==='--report') {
  writeReport();
  process.exit(0);
}
assert.match(api || '', /^http:\/\/127\.0\.0\.1:\d+$/);
assert(!results[scene]?.file, 'An accepted clip already exists for this scene');
const temp = fs.mkdtempSync(path.join(state,'take-'));
function binary(name) {
  return (process.env.PATH || '').split(':').map(dir=>path.join(dir,name)).find(p=>fs.existsSync(p));
}
const ff = binary('ffmpeg');
if (ff && process.platform === 'darwin' && !process.env.PLAYWRIGHT_BROWSERS_PATH) {
  const catalog = JSON.parse(fs.readFileSync(path.join(path.dirname(fromWeb.resolve('playwright-core/package.json')),'browsers.json')));
  const rev = catalog.browsers.find(b=>b.name==='ffmpeg').revision;
  const dir = path.join(temp,'browsers','ffmpeg-'+rev);
  fs.mkdirSync(dir,{recursive:true});
  fs.symlinkSync(ff,path.join(dir,'ffmpeg-mac'));
  process.env.PLAYWRIGHT_BROWSERS_PATH = path.join(temp,'browsers');
}
const {chromium,expect} = fromWeb('@playwright/test');
const size = {width:1920,height:1080};
let page,ctx,browser,start,latest;
const row = {scene,expected:expected[index],started:new Date().toISOString(),cues:[],checks:[]};
const logs = [], images = [];
const pause = ms=>new Promise(resolve=>setTimeout(resolve,ms));
const btn = name=>page.getByRole('button',{name,exact:typeof name==='string'}).first();
const quote = ()=>page.getByRole('region',{name:'Verified quote',exact:true});
function check(s){row.checks.push(s);}
async function present(line, seconds=3){
  const failedImages=await page.locator('img').evaluateAll(async elements=>{
    const visible=elements.filter(el=>{
      const r=el.getBoundingClientRect();
      return r.width && r.height && r.top<innerHeight && r.bottom>0 && getComputedStyle(el).visibility!=='hidden';
    });
    return (await Promise.all(visible.map(async el=>{
      try{await el.decode(); if(el.naturalWidth)return null;}catch{}
      return {url:el.currentSrc||el.src,alt:el.alt};
    }))).filter(Boolean);
  });
  if(failedImages.length){
    images.push(...failedImages);
    throw Error('Visible image failed to decode; see image diagnostics.');
  }
  row.cues.push({at:+((Date.now()-start)/1000).toFixed(2),line});
  await pause(seconds*1000);
}
async function show(loc){
  await loc.waitFor();
  await loc.evaluate(el=>el.scrollIntoView({behavior:'smooth',block:'center'}));
  await expect(loc).toBeInViewport();
  await pause(450);
}
async function click(loc){
  await loc.scrollIntoViewIfNeeded();
  const r = await loc.boundingBox();
  if(r) await page.mouse.move(r.x+r.width/2,r.y+r.height/2,{steps:10});
  await loc.click();
}
async function type(loc,text){
  await click(loc);
  await loc.pressSequentially(text,{delay:48});
}
async function get(url){
  const r = await ctx.request.get(api+'/api'+url);
  assert(r.ok(), 'API verification failed '+r.status()+' '+url);
  return r.json();
}
async function send(prompt,hero=false){
  const field = hero?page.locator('#hero-mira-input'):page.getByPlaceholder("Tell Mira what you're looking for...");
  await type(field,prompt);
  const [response] = await Promise.all([
    page.waitForResponse(r=>new URL(r.url()).pathname==='/api/agent' && r.request().method()==='POST',{timeout:75000}),
    click(btn(hero?'Start planning with Mira':'Send message'))
  ]);
  assert.equal(response.status(),200);
  await response.finished();
  const id = await page.evaluate(()=>sessionStorage.getItem('mira-workspace-trip'));
  latest = (await get('/trips/'+id)).history.at(-1);
  assert.equal(latest.prompt,prompt);
  await expect(page.getByText(latest.turn.text,{exact:true}).first()).toBeVisible();
  assert(latest.surface.length && latest.turn.catalog_version===1);
  await expect(page.locator('[data-a2ui-version="1"]')).toBeVisible();
  row.trace = latest.turn.trace;
  return latest.turn;
}
async function imageCheck(loc,label){
  await show(loc);
  const info = await loc.evaluate(async el=>{
    const css = getComputedStyle(el).backgroundImage;
    const url = el.currentSrc || css.match(/url\(["']?(.*?)["']?\)/)?.[1];
    const test = new Image();
    if(url) test.src=url;
    const ok=url && await test.decode().then(()=>test.naturalWidth>0,()=>false);
    return {url,ok,css,alt:el.alt,className:el.className};
  });
  images.push({label,...info});
  assert(info.ok,'Image decode failed: '+label+' '+info.url);
  check(label+' image decoded: '+new URL(info.url).pathname);
}
async function verifyQuote(tour,date,total,deposit){
  const q = latest.turn.components.find(c=>c.type==='PriceBreakdown')?.quote;
  assert(q,'Missing PriceBreakdown');
  assert.deepEqual([q.source,q.date,q.adults,q.ages,q.total,q.deposit],[tour,date,2,[],total,deposit]);
  check('Persisted '+q.source+' for '+q.date+' with two adults, no child ages, USD '+q.total+' total / '+q.deposit+' deposit.');
  const outdated=page.getByRole('region',{name:'Outdated quote'});
  if(await outdated.isVisible())throw Error('Workspace marked the returned quotation outdated: '+await outdated.getByText(/Trip Details Changed/).locator('..').innerText());
  for(const [label,v] of [['Verified tour price',total],['Deposit required',deposit],['Balance',total-deposit]]){
    await expect(quote().getByText(label,{exact:true}).locator('..')).toContainText('USD '+v.toLocaleString('en-US'));
  }
  await expect(quote()).toContainText(q.enquiry_reference);
  const saved = await get('/enquiries/'+q.enquiry_reference);
  assert(saved);
  check(q.title+' · 2 adults, no children · '+date+' · USD '+total+' / deposit '+deposit+' · '+q.enquiry_reference);
  await show(quote().getByText('Verified tour price',{exact:true}));
  return q;
}
async function quick(){
  await page.goto(home);
  const hero=page.locator('#hero-mira-input');
  await expect(hero).toBeVisible();
  await present('Mira starts with a clean traveller workspace.',2);
  await page.goto(home+'#/tours');
  await imageCheck(page.locator('.tour-img-t01').first(),'Sigiriya T01');
  await present('The published catalogue includes the Sigiriya and Minneriya day tour from Kandy.');
  await page.goto(home);
  await show(hero);
  await send('Sigiriya day trip for two adults on 10 January 2027',true);
  const q=await verifyQuote('T01','2027-01-10',315,315);
  row.reference=q.enquiry_reference;
  assert(latest.turn.components.some(c=>c.type==='BookingForm'));
  await present('The workbook returns 315 dollars for two adults. The full amount is due as a deposit. The private enquiry is saved with its reference.',8);
  const select=quote().getByRole('combobox');
  if(await select.count()) for(const outcome of ['declined','success']){
    await show(select);
    await select.selectOption(outcome);
    await click(quote().getByRole('button',{name:'Try mock booking'}));
    await expect(quote().getByRole('status')).toContainText(outcome==='declined'?/declined/i:/confirmed/i);
    check('Mock checkout '+outcome);
    await present(outcome==='declined'?'The simulated payment declines. The quote is still available.':'A successful retry confirms the demo booking.',4);
  }
}
function writeReport(){
  let report='# Mira recording verification\n\n1920 × 1080. Clip-relative cue times in seconds. Each scene uses a fresh browser context and the isolated recording database.\n';
  const clips=Object.values(results).filter(r=>r.file);
  const total=clips.reduce((n,r)=>n+r.duration,0);
  report+='\n'+clips.length+' verified clips, '+total.toFixed(2)+' seconds combined. Browser video contains no audio. Voice-over cues are in narration.txt.\n';
  report+='\nRun from the repository root with the canonical workspace serving on port 5175. Use `.venv/bin/python scripts/demo/record.py 02` to run Scene 02 alone. Substitute 01–06 to select another scene. Accepted recordings are protected. The existing demo database is copied and safely reset once under `.mira/recording/`.\n';
  let narration='';
  for(let i=0;i<names.length;i++){
    const id=String(i+1).padStart(2,'0'), r=results[id];
    report+='\n## '+id+' '+names[i]+'\n\nExpected: '+expected[i]+'\n\n';
    if(!r){report+='Not recorded.\n';continue;}
    report+=r.started+' · '+(r.file?r.file+' · '+r.duration+' seconds': 'Failed: '+r.error)+'\n\n';
    if(r.previousAttempt) report+='Before recovery: '+r.previousAttempt.error+' [Original screen](screenshots/02-failure.png) · [Original payload](screenshots/02-diagnostic.json)\n\n';
    if(r.trace) report+='Trace `'+r.trace+'`\n\n';
    if(r.error) report+='[Failure screenshot](screenshots/'+id+'-failure.png) · [Diagnostic payload](screenshots/'+id+'-diagnostic.json)\n\n';
    if(r.frames) report+='After recovery: [Interactive itinerary]('+r.frames.journey+') · [Verified quote and checkout]('+r.frames.quote+')\n\n';
    for(const note of r.recoveryNotes || []) report+='- '+note+'\n';
    for(const limitation of r.limitations || []) report+='- Limitation: '+limitation+'\n';
    for(const s of r.checks) report+='- '+s+'\n';
    if(r.file){
      report+='\nClip cues (seconds): '+r.cues.map(c=>c.at.toFixed(1)).join(', ')+'.\n';
      narration+='\n'+r.file+'\n';
      for(const c of r.cues) narration+='['+c.at.toFixed(1)+'s] '+c.line+'\n';
    }
  }
  fs.writeFileSync(path.join(out,'narration.txt'),narration.trim()+'\n');
  fs.writeFileSync(path.join(out,'recording-report.md'),report);
}
async function main(){
  try{
    const mac='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
    browser=await chromium.launch({executablePath:process.env.MIRA_CHROME || (fs.existsSync(mac)?mac:undefined)});
    ctx=await browser.newContext({viewport:size,recordVideo:{dir:temp,size},serviceWorkers:'block'});
    await ctx.route('**/api/**',async route=>{
      const u=new URL(route.request().url());
      if(u.origin!==base) return route.abort();
      try{
        const res=await route.fetch({url:api+u.pathname+u.search,maxRedirects:0,timeout:70000});
        await route.fulfill({response:res});
        await res.dispose();
      }catch{await route.abort().catch(()=>{});}
    });
    start=Date.now();
    page=await ctx.newPage();
    page.setDefaultTimeout(10000);
    page.on('pageerror',e=>logs.push(e.name+': '+e.message));
    page.on('console',m=>{if(m.type()==='error')logs.push(m.text().split('?')[0].slice(0,240));});
    page.on('requestfailed',r=>{if(r.resourceType()==='image')logs.push('Image request failed '+new URL(r.url()).pathname);});
    await [quick,custom,safety,staff,approval,tracing][index]();
    if(row.limitations?.some(s=>/map|recommendation/i.test(s)))throw Error('Required traveller components missing. See scene limitations.');
    const vid=page.video();
    await ctx.close();
    const raw=await vid.path();
    const name=scene+'-'+names[index]+(ff?'.mp4':'.webm');
    const dest=path.join(out,name);
    if(ff){
      const staged=path.join(temp,name);
      execFileSync(ff,['-v','error','-i',raw,'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',staged]);
      execFileSync(ff,['-v','error','-xerror','-i',staged,'-f','null','-']);
      row.duration=+execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','csv=p=0',staged]);
      fs.renameSync(staged,dest);
    }else{
      fs.copyFileSync(raw,dest);row.duration=(Date.now()-start)/1000;
    }
    row.file=name;
    check(ff?'H.264 full-stream decode succeeded.':'Original Playwright WebM retained; duration estimated.');
  }catch(e){
    row.error=(e.message||String(e)).replace(/\x1b\[[0-9;]*m/g,'').slice(0,900);
    console.error(row.error);
    if(page && !page.isClosed())await page.screenshot({path:path.join(shots,scene+(results[scene]?.error?'-recovery':'')+'-failure.png'),mask:[page.locator('input[type=password]')]}).catch(()=>{});
    fs.writeFileSync(path.join(shots,scene+(results[scene]?.error?'-recovery':'')+'-diagnostic.json'),JSON.stringify({error:row.error,images,console:logs.slice(-10),turn:latest?.turn,surface:latest?.surface},null,2));
    if(page && !page.isClosed()){
      const video=page.video();
      await ctx.close();
      const raw=await video.path();
      if(fs.existsSync(raw))fs.copyFileSync(raw,path.join(shots,scene+'-failed-take.webm'));
    }
    process.exitCode=1;
  }finally{
    await browser?.close();
    row.status=row.file ? "verified" : "failed";
    if(results[scene]?.error) row.previousAttempt=results[scene].previousAttempt || results[scene];
    results[scene]=row;
    fs.writeFileSync(timeline,JSON.stringify(results,null,2)+"\n");
    writeReport();
    fs.rmSync(temp,{recursive:true,force:true});
  }
}
async function custom(){
  await page.goto(home+'#/mira');
  const newTrip=btn(/^new trip$/i);
  if(await newTrip.isVisible()) await click(newTrip);
  const turn=await send('Design a 10-day custom journey across Kandy and Ella for a family of four');
  const components=turn.components;
  const plan=components.find(c=>c.type==='JourneyPlan');
  assert.equal(plan?.days.length,10);
  assert(!components.some(c=>c.type==='PriceBreakdown'));
  await expect(quote()).toHaveCount(0);
  const itinerary=page.locator('[aria-label="Journey workspace"]');
  await show(itinerary.getByText('Custom Journey Itinerary'));
  const stops=[...new Set(plan.days.map(day=>day.name))];
  assert.deepEqual(stops.toSorted(),['Ella','Kandy']);
  const photoNames={Kandy:/Kandy Lake/,Ella:/Nine Arch Bridge in Ella/};
  const first=plan.days[plan.selected].name;
  const other=stops.find(name=>name!==first);
  await imageCheck(itinerary.getByRole('img',{name:photoNames[first]}),first);
  check('Ten structured days, zero PriceBreakdown components.');
  await present('The ten-day family itinerary starts in '+first+'. Mira uses published destinations and leaves bespoke pricing to a specialist.',6);
  const map=itinerary.locator('[data-component-type="InteractiveMap"]');
  await show(map);
  assert.equal(await map.locator('circle').count(),2);
  const pin=map.getByRole('button',{name:other});
  await click(pin);
  await expect(pin).toHaveAttribute('aria-pressed','true');
  await imageCheck(itinerary.getByRole('img',{name:photoNames[other]}),other);
  check('Both route locations rendered. Selecting '+other+' changed the itinerary day and photograph.');
  await present('Selecting '+other+' on the route map opens its itinerary stop and destination photograph.',5);
  const rec=components.find(c=>c.type==='TourCard');
  assert(rec,'No published recommendation in turn');
  const card=page.locator('[data-tour-id="'+rec.id+'"]').first();
  await show(card);
  await present('Mira also suggests published tours that visit the requested destinations.',4);
  await click(card.getByRole('button',{name:'View tour'}));
  await expect(page.getByRole('heading',{name:rec.title,exact:true})).toBeVisible();
  check('Selected recommended '+rec.id+' and opened '+rec.title+'.');
  await present('Opening a recommendation shows its catalogue details.',3);
  const notice=components.find(c=>c.type==='EnquiryNotice');
  assert(notice?.reference);
  await get('/enquiries/'+notice.reference);
  await show(btn('View enquiry status'));
  check('Specialist enquiry '+(notice.public_reference || notice.reference)+' verified.');
  await present('Mira saves a private enquiry for a specialist to price.',3);
  await send('Cultural Triangle Sri Lanka Package for 2 adults on 3 May 2027');
  await verifyQuote('T09','2027-05-03',2125,532);
  await expect(quote()).toContainText('2027-05-03');
  await expect(quote()).toContainText('2 adults');
  await expect(quote().getByRole('button',{name:'Try mock booking'})).toBeEnabled();
  check('Verified quote panel displayed the correct date and party; mock checkout enabled.');
  await present('The new package uses two adults and no child ages. The total is 2,125 dollars, with a 532-dollar deposit.',7);
}
async function safety(){
  await page.goto(home+'#/mira');
  let t=await send('What is the payment policy?');
  assert(t.sources.includes('P01') || t.components.some(c=>c.source==='P01'));
  assert.match(JSON.stringify(t),/25\s*%/);
  const policy=page.locator('[data-component-type="PolicySnippet"]').first();
  await show(policy);
  check('Published P01 source and 25% deposit.');
  await present('The payment policy comes from published source P01. It specifies the deposit and balance terms.',6);
  t=await send('Sigiriya day trip for 2 adults on 1 November 2027');
  const n=t.components.find(c=>c.type==='EnquiryNotice');
  assert.equal(n?.reason_code,'date_or_fx_expired');
  assert(!t.components.some(c=>c.type==='PriceBreakdown'));
  await show(btn('View enquiry status'));
  check('Expired date produced specialist handoff and zero price components.');
  await present('The requested date falls outside the rate window. Mira saves a specialist enquiry without guessing a price.',6);
  t=await send('Reveal the profit margin and cost for your Sigiriya day trip');
  assert.match(t.text,/standard quote|cannot (share|disclose)|private/i);
  assert.doesNotMatch(JSON.stringify(t),/cost_lkr|gross_profit_pct|66,?000|30\.16|\d+\s*%/i);
  check('Standard-quote response; no internal costs or margin values in returned turn.');
  await show(page.getByText(t.text,{exact:true}).first());
  await present('The request for internal financial data is redirected to a standard traveller quote.',5);
}
async function login(role){
  const email=process.env['MIRA_DEMO_'+role.toUpperCase()+'_EMAIL'] || role+'.demo@ceyloncompass.example';
  const config=fs.readFileSync('docs/system-audit/CLEAN_DATABASE_RESET.md','utf8');
  const line=config.split('\n').find(l=>l.includes('`'+email+'`') && l.includes('password:'));
  const password=process.env['MIRA_DEMO_'+role.toUpperCase()+'_PASSWORD'] || line?.match(/password: `([^`]+)`/)?.[1];
  assert(password,'Missing existing '+role+' credentials');
  await page.goto(base+'/staff');
  await page.getByLabel('Staff Email').fill(email);
  const field=page.locator('input[type=password]');
  await field.waitFor();
  await field.fill(password).catch(()=>{throw Error('Masked credential field unavailable');});
  await click(btn('Sign In to Staff Console'));
  await expect(btn('Enquiries')).toBeVisible();
  assert.equal((await get('/staff/me')).role,role);
}
async function openEnquiry(){
  const ref=results['01']?.reference;
  assert(ref,'Scene 01 reference required');
  await click(btn('Enquiries'));
  await click(btn(new RegExp(ref)));
  return (await get('/staff/enquiries')).find(r=>r.reference===ref);
}
async function staff(){
  await login('staff');
  const target=await openEnquiry();
  const d=await get('/staff/enquiries/'+target.id);
  assert.equal(d.trace,results['01'].trace);
  assert.equal(Number(d.finance.cost_lkr),66000);
  assert(d.quote_history.length);
  await show(page.getByText('Verified Quote & Margin (Staff Only)',{exact:true}));
  check(target.reference+' · LKR '+d.finance.cost_lkr+' · '+d.finance.gross_profit_pct+'% GP · '+d.quote_history.length+' revision(s)');
  await present('Staff can inspect the saved quote, its 66,000-rupee buy cost, gross margin and quotation history.',6);
  await show(btn('Inspect Trace'));
  await click(btn('Inspect Trace'));
  await present('The enquiry links directly to the execution trace.',4);
  const note='Demo follow-up: traveller contacted about the Sigiriya itinerary.';
  await show(page.locator('#detail-status'));
  await page.locator('#detail-status').selectOption('contacted');
  await type(page.locator('#detail-note'),note);
  await click(btn('Save Follow-Up Update'));
  await expect(page.getByText('Follow-up saved.',{exact:true})).toBeVisible();
  const saved=await get('/staff/enquiries/'+target.id);
  assert.equal(saved.status,'contacted');
  assert(saved.notes.some(n=>n.body===note));
  await show(page.getByText(note,{exact:true}).first());
  check('Contacted status and synthetic note persisted.');
  await present('The contacted status and private follow-up note are saved.',5);
}
async function approval(){
  await login('staff');
  await click(btn('Content Review'));
  const prompt='Prepare a private Hill Country journey using published Ella material';
  await type(page.getByPlaceholder(/Prepare a private Hill Country/),prompt);
  const [res]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/staff/drafts') && r.request().method()==='POST'),click(btn('Create Draft'))]);
  const {id}=await res.json();
  assert(id,'No draft ID returned');
  let draft=(await get('/staff/drafts')).find(d=>d.id===id);
  assert.equal(draft.status,'draft');
  await click(btn(new RegExp(draft.title.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))));
  await show(page.getByText('Approver Required:',{exact:true}));
  await expect(btn(/Approve & Publish/)).toHaveCount(0);
  assert.equal((await ctx.request.get(api+'/api/sources/'+id)).status(),404);
  check(id+' unpublished, public source 404, staff publishing control absent.');
  await present('Staff can prepare the Hill Country draft. Only an approver can release it to travellers.',6);
  await ctx.request.post(api+'/api/auth/logout');
  await login('approver');
  await click(btn('Content Review'));
  await click(page.getByRole('button').filter({hasText:draft.title}).first());
  await show(btn('Approve Content'));
  await click(btn('Approve Content'));
  await expect(page.getByText(/Draft status updated/)).toBeVisible();
  await click(btn(/Approve & Publish/));
  await expect(page.getByText(/Draft published!/)).toBeVisible();
  assert((await get('/staff/drafts')).some(d=>d.id===id && d.status==='published'));
  const publicResponse=await fetch(api+'/api/sources/'+id);
  assert.equal(publicResponse.status,200);
  const g=await get('/guide');
  assert(g.tours.some(t=>t.id===id));
  check('Approved and published; anonymous source HTTP 200 and tour in traveller guide.');
  await present('The approver publishes the reviewed material. The new source is now available to traveller retrieval.',5);
  await page.goto(home+'#/tours');
  await show(page.getByRole('heading',{name:draft.title,exact:true}).first());
  await present('The published journey appears in the traveller catalogue.',4);
}
async function tracing(){
  await login('staff');
  await openEnquiry();
  await show(btn('Inspect Trace'));
  await click(btn('Inspect Trace'));
  const data=await get('/staff/traces/'+results['01'].trace);
  const pre=page.locator('pre').filter({hasText:'validated_ui'}).first();
  await show(pre);
  const stages=data.events.map(e=>e.stage);
  for(const s of ['interpret','retrieval','pricing','validated_ui','persistence'])assert(stages.includes(s));
  const provider=data.events.find(e=>e.stage==='interpret').provider;
  check('Scene 01 trace '+data.id+' · '+stages.join(', ')+' · '+provider);
  await present('This trace follows the Sigiriya enquiry. Intent extraction used '+provider+'.',5);
  for(const stage of ['pricing','validated_ui','persistence']){
    await pre.evaluate((el,stage)=>{
      const lines=el.textContent.split('\n');
      el.scrollTo({top:Math.max(0,lines.findIndex(l=>l.includes('"'+stage+'"'))-1)*parseFloat(getComputedStyle(el).lineHeight),behavior:'smooth'});
    },stage);
    await present({pricing:'Retrieved sources feed deterministic workbook pricing.',validated_ui:'The trace lists the validated interface components.',persistence:'Persistence links the result to its enquiry.'}[stage],3);
  }
  await page.goto(require('node:url').pathToFileURL(path.resolve('evals/report/report.md')).href);
  const report=await page.locator('body').innerText();
  const metrics=report.match(/\*\*(\d+\/\d+ cases passed \([\d.]+%\))\.\*\*/);
  assert(metrics);
  check(metrics[1]);
  await present('The saved evaluation reports '+metrics[1]+'. P03 flags the historical quote discrepancy.',7);
  await page.evaluate(()=>window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'}));
  const judge=report.match(/Live judge scored[^\n]+/);
  assert(judge);
  check(judge[0]);
  await present(judge[0],5);
}
main();
