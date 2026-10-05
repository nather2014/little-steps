(function(root){
  function summarize(attempts){
    const topics=new Map(),weeks=new Map();let correct=0,total=0;
    for(const a of attempts){
      correct+=a.correct;total+=a.total;
      const w=weeks.get(a.week_start)||{week:a.week_start,correct:0,total:0,attempts:0};
      w.correct+=a.correct;w.total+=a.total;w.attempts++;weeks.set(a.week_start,w);
      for(const q of a.review){
        const key=a.subject+'|'+q.topic;
        const t=topics.get(key)||{subject:a.subject,topic:q.topic,correct:0,total:0};
        t.total++;if(q.correct)t.correct++;topics.set(key,t);
      }
    }
    return {attempts:attempts.length,accuracy:total?Math.round(correct/total*100):null,
      topics:[...topics.values()].map(t=>({...t,accuracy:Math.round(t.correct/t.total*100)})).sort((a,b)=>a.accuracy-b.accuracy),
      weeks:[...weeks.values()].map(w=>({...w,accuracy:Math.round(w.correct/w.total*100)})).sort((a,b)=>a.week.localeCompare(b.week)),
      wrong:attempts.flatMap(a=>a.review.filter(q=>!q.correct).map(q=>({...q,subject:a.subject,date:a.submitted_at}))) };
  }
  const api={summarize};if(typeof module!=='undefined')module.exports=api;else root.LearningAnalytics=api;
})(globalThis);
