const assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');const base=process.env.TEST_BASE_URL||'http://localhost:8090';
(async()=>{const browser=await chromium.launch({headless:true}),errors=[];try{
 const ctx=await browser.newContext({viewport:{width:390,height:740},isMobile:true,hasTouch:true}),page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);await page.getByRole('button',{name:'Continue as guest',exact:true}).click();await page.getByLabel('First name or nickname').waitFor();
 const account=await page.evaluate(async()=>await(await fetch('/api/auth/me')).json());if(process.env.TEST_GUEST_ID_FILE)fs.appendFileSync(process.env.TEST_GUEST_ID_FILE,account.user.id+'\n');
 await page.getByLabel('First name or nickname').fill('Learning loop tester');await page.locator('#grade-field select').selectOption('2');await page.getByRole('button',{name:'Continue',exact:true}).click();await page.locator('.play-options').waitFor();
 assert.equal(await page.locator('[data-play-mode]').count(),4);
 assert.equal(await page.locator('#navigation').getByRole('button',{name:'Learn',exact:true}).count(),0);
 await page.locator('[data-play-mode="normal"]').click();await page.locator('#learning-topics').getByRole('button',{name:/Subtraction with borrowing/}).click();await page.locator('#quiz-dialog .option').first().waitFor();
 async function finish(){for(let i=0;i<10;i++){await page.locator('#quiz-dialog .option').first().click();await page.getByRole('button',{name:i===9?'Submit answers':'Next question →',exact:true}).click()}await page.getByRole('button',{name:'Back to learning →',exact:true}).waitFor()}
 await finish();let rows=await page.evaluate(async()=>await(await fetch('/api/attempts')).json());assert.equal(rows[0].rr_delta,0);assert.equal(rows[0].total,10);
 await page.locator('.result-reflection').first().locator('summary').click();await page.getByRole('button',{name:'I was unsure / guessed',exact:true}).first().click();await page.getByRole('button',{name:'Saved · revisit this skill',exact:true}).waitFor();
 await page.getByRole('button',{name:'Back to learning →',exact:true}).click();await page.locator('[data-play-mode="ranked"]').click();await page.getByRole('heading',{name:'Your ranked tests',exact:true}).waitFor();
 for(let round=0;round<2;round++){await page.getByRole('button',{name:'Start exam →',exact:true}).first().click();await page.locator('#quiz-dialog .option').first().waitFor();await finish();await page.getByRole('button',{name:'Back to learning →',exact:true}).click();await page.getByRole('heading',{name:'Your ranked tests',exact:true}).waitFor()}
 rows=await page.evaluate(async()=>await(await fetch('/api/attempts')).json());assert.equal(rows.filter(a=>a.mode==='ranked').length,2);assert.equal(new Set(rows.filter(a=>a.mode==='ranked').map(a=>a.exam_id)).size,1);
 await page.reload();await page.locator('.play-options').waitFor(); const data=await page.evaluate(async()=>await(await fetch('/api/learning')).json());assert.ok(data.notes.some(n=>n.reason==='unsure'));assert.deepEqual(errors,[]);
 console.log('Learning browser checks passed: Normal/ranked dashboard modes, no Learn tab, easier/normal practice, uncertainty, private persistence, mobile layout and repeat ranked tests.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
