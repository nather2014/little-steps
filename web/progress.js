/* Rank, parent progress and private exam comparisons from the API. */
window.LearningProgress=(()=>{
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const percentage=(a,b)=>Math.min(100,Math.max(0,b?100*a/b:0));
 function hero(r){
  return '<section class="progress-card" aria-label="Level and rank"><div class="progress-card-top"><div><span class="progress-label">LEVEL</span><h2>Level '+r.level+' <span>· '+esc(r.level_name)+'</span></h2></div><strong class="progress-xp">'+r.xp.toLocaleString()+' <span>XP</span></strong></div><div class="xp-level-track" role="progressbar" aria-label="Progress to next level" aria-valuemin="0" aria-valuemax="'+r.level_target+'" aria-valuenow="'+r.level_xp+'"><span style="width:'+percentage(r.level_xp,r.level_target)+'%"></span></div><p class="progress-next">'+r.level_xp+' / '+r.level_target+' XP <span>to Level '+(r.level+1)+'</span></p><div class="progress-rank"><span class="progress-rank-icon" aria-hidden="true">◆</span><div><span class="progress-label">RANK</span><strong>'+esc(r.rank.name)+'</strong></div><strong class="progress-rr">'+r.rank.rr+' <span>RR</span></strong></div><p class="progress-rank-next">'+(r.rank.next_rank?r.rank.rr_needed+' RR to '+esc(r.rank.next_rank):'Top tier reached')+'</p></section>';

 }
 function dashboardHeader(r){return '<section class="dashboard-rank" aria-label="Rank and RR"><div class="eyebrow">YOUR RANK</div><h2><span class="rank-greeting-icon" aria-hidden="true">◆</span> '+esc(r.rank.name)+'</h2><p><strong>'+r.rank.rr+' RR</strong>'+ (r.rank.next_rank?' · '+r.rank.rr_needed+' RR to '+esc(r.rank.next_rank):' · Top tier reached')+'</p></section>'}
 function comparisonPanel(rows,child=false,initial){
  if(!rows.length)return '<section class="panel comparison-panel"><h2>Score vs exam average</h2><p class="empty">Complete a quiz to see a score comparison.</p></section>';
  return '<section class="panel comparison-panel"><h2>Score vs exam average</h2><label class="field">Choose an exam result<select id="comparison-select">'+rows.map(r=>'<option value="'+r.attempt_id+'" '+(initial===r.attempt_id?'selected':'')+'>'+esc(r.title)+' · '+(r.mode==='time_trial'?'Time Trials':r.mode==='practice'?'Practice':'Ranked test')+' · Week of '+esc(r.week_start)+' · '+esc(new Date(r.submitted_at).toLocaleString())+'</option>').join('')+'</select></label><div id="comparison-chart"></div><p class="hint">Same exam, class and mode; time trials also match round duration. The average uses each other learner’s first result and needs at least three other learners. Questions may vary in practice or after replacement.</p></section>';
 }
 function chart(r,child=false){
  const name=child?'Your child':'You',own=Number(r.score),avg=r.average===null?null:Number(r.average),hasAverage=avg!==null;
  const y=v=>220-v*1.7;
  const delta=hasAverage?Math.round((own-avg)*10)/10:null;
  const description=hasAverage?name+' scored '+own+'%; other learners averaged '+avg+'%.':name+' scored '+own+'%. The exam average is waiting for more learners.';
  const grid=[0,20,40,60,80,100].map(v=>'<line x1="45" x2="330" y1="'+y(v)+'" y2="'+y(v)+'" stroke="#e5e9e0"/><text x="36" y="'+(y(v)+4)+'" text-anchor="end">'+v+'</text>').join('');
  const averageBar=hasAverage?'<rect x="215" y="'+y(avg)+'" width="75" height="'+(avg*1.7)+'" rx="7" fill="#9180bd"/><text x="252" y="'+(y(avg)-10)+'" text-anchor="middle" class="chart-value">'+avg+'%</text>':'<rect x="215" y="50" width="75" height="170" rx="7" fill="#f6f5fa" stroke="#b8adc8" stroke-dasharray="5 5"/><text x="252" y="140" text-anchor="middle">Waiting</text>';
  return '<svg class="comparison-svg" viewBox="0 0 360 260" role="img" aria-label="'+esc(description)+'">'+grid+'<rect x="85" y="'+y(own)+'" width="75" height="'+(own*1.7)+'" rx="7" fill="#357259"/><text x="122" y="'+(y(own)-10)+'" text-anchor="middle" class="chart-value">'+own+'%</text>'+averageBar+'<text x="122" y="248" text-anchor="middle">'+name+'</text><text x="252" y="248" text-anchor="middle">Other learners</text></svg><p class="comparison-summary">'+(hasAverage?(delta===0?'Same as the exam average':Math.abs(delta)+' percentage points '+(delta>0?'above':'below')+' the exam average'):'Waiting for more learners ('+r.peer_count+' of 3 other learners)')+'</p>'+(hasAverage?'<p class="hint">Average: '+avg+'% across '+r.peer_count+' other learners.</p>':'')+'<div class="data-scroll"><table><thead><tr><th>Learner</th><th>Score</th></tr></thead><tbody><tr><td>'+name+'</td><td>'+own+'%</td></tr><tr><td>Other learners’ average</td><td>'+(hasAverage?avg+'%':'Not enough results yet')+'</td></tr></tbody></table></div>';
 }
 function wireComparison(target,rows,child=false,initial){
  const select=target.querySelector('#comparison-select'),chartTarget=target.querySelector('#comparison-chart');
  if(!select||!chartTarget)return;
  if(initial&&rows.some(r=>r.attempt_id===initial))select.value=String(initial);
  const draw=()=>{const row=rows.find(r=>r.attempt_id===Number(select.value));if(row)chartTarget.innerHTML=chart(row,child)};
  select.onchange=draw;draw();
 }
 return {hero,dashboardHeader,comparisonPanel,chart,wireComparison};
})();
