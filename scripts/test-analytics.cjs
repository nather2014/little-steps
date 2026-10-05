const assert=require('node:assert/strict');
const {summarize}=require('../web/analytics.js');
assert.deepEqual(summarize([]),{attempts:0,accuracy:null,topics:[],weeks:[],wrong:[]});
const result=summarize([
 {correct:1,total:2,week_start:'2026-09-28',subject:'maths',submitted_at:'2026-10-01',review:[{topic:'Numbers',correct:true},{topic:'Shapes',correct:false,prompt:'Triangle'}]},
 {correct:2,total:2,week_start:'2026-10-05',subject:'maths',submitted_at:'2026-10-06',review:[{topic:'Numbers',correct:true},{topic:'Shapes',correct:true}]}
]);
assert.equal(result.accuracy,75);assert.equal(result.topics[0].topic,'Shapes');assert.equal(result.topics[0].accuracy,50);assert.equal(result.weeks[0].accuracy,50);assert.equal(result.weeks[1].accuracy,100);assert.equal(result.wrong.length,1);
console.log('Analytics checks passed');
