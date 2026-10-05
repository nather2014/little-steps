"""Generate original, independent maths and reasoning challenges (not official papers)."""
import json
from pathlib import Path
from fractions import Fraction
bank={str(g):[] for g in range(-1,11)}
def add(out,topic,prompt,answer,*wrong):
    options=list(map(str,[answer,*wrong]))
    assert len(options)==4 and len(set(options))==4,(prompt,options)
    offset=sum(map(ord,prompt))%4
    options=options[offset:]+options[:offset]
    out.append([prompt,options,options.index(str(answer)),topic])
def numeric(out,topic,prompt,a):add(out,topic,prompt,a,a+1,a+2,a-1)
for g in range(-1,11):
    maths=[];reason=[]
    for n in range(1,9):
        if g<=0:
            numeric(maths,'Counting stories',f'{n} birds sit on a branch. One more bird joins. How many birds are there?',n+1)
            numeric(maths,'Missing numbers',f'What number is missing: {n}, __, {n+2}?',n+1)
            numeric(maths,'Taking away',f'There are {n+2} blocks. You put away 2. How many remain?',n)
        elif g<=2:
            numeric(maths,'Two-step stories',f'Mira has {n+3} stickers, gets 4 more, then gives 2 away. How many remain?',n+5)
            numeric(maths,'Equal groups',f'There are {n} baskets with {g+1} apples in each. How many apples altogether?',n*(g+1))
            numeric(maths,'Missing numbers',f'A number plus {n+2} equals {2*n+7}. What is the number?',n+5)
        elif g<=5:
            numeric(maths,'Multi-step reasoning',f'{n+2} boxes each hold {g+2} pencils. After 3 pencils are used, how many remain?',(n+2)*(g+2)-3)
            numeric(maths,'Measurement puzzles',f'A rectangle is {n+g} cm long and {g} cm wide. What is its perimeter in cm?',2*(n+2*g))
            numeric(maths,'Fractions in stories',f'One third of {3*(n+g)} marbles are blue. How many are not blue?',2*(n+g))
        elif g<=8:
            numeric(maths,'Ratio reasoning',f'Red and blue beads are in the ratio 2:3. There are {5*(n+g)} beads in total. How many are blue?',3*(n+g))
            numeric(maths,'Percentage reasoning',f'A book costs ₹{100*(n+1)}. A 20% discount is given. What is the sale price in rupees?',80*(n+1))
            numeric(maths,'Equations',f'If 3x + {n} = {3*(n+g)+n}, what is x?',n+g)
        else:
            numeric(maths,'Algebraic reasoning',f'Two positive numbers sum to {2*n+3} and differ by 3. What is their product?',n*(n+3))
            numeric(maths,'Coordinate reasoning',f'The midpoint of ({2*n}, {2*g}) and ({2*n+4}, {2*g+6}) is (x, y). What is x + y?',n*2+g*2+5)
            numeric(maths,'Sequences',f'An arithmetic sequence starts at {n} with common difference {g-5}. What is the 10th term?',n+9*(g-5))
        step=1 if g<=0 else 2 if g<=2 else g+1
        numeric(reason,'Number patterns',f'What comes next: {n}, {n+step}, {n+2*step}, __?',n+3*step)
        if g<=0:
            add(reason,'Repeating patterns',f'Pattern {n}: circle, square, circle, square, circle, __. What comes next?','Square','Circle','Triangle','Star')
            numeric(reason,'Ordering',f'{n+2} children stand in a line. The first child leaves. How many children are in the line now?',n+1)
        elif g<=3:
            numeric(reason,'Position puzzles',f'Asha is {n+1}th from the front and 3rd from the back. How many children are in the line?',n+3)
            add(reason,'Classification',f'Which item does not belong to this set ({n}): apple, mango, carrot, banana?','Carrot','Apple','Mango','Banana')
        else:
            numeric(reason,'Growing patterns',f'What comes next: {n}, {n+2}, {n+6}, {n+12}, __?',n+20)
            numeric(reason,'Position puzzles',f'A learner is {n+g}th from the left and {n+2}th from the right. How many learners are in the row?',2*n+g+1)
    # Avoid indistinguishable repeated visual/classification items.
    reason=[q for q in reason if not q[3] in ('Repeating patterns','Classification') or q is next(x for x in reason if x[3]==q[3])]
    if g<=0:
        for topic,p,a,w1,w2,w3 in [
            ('Shapes','Which shape has three straight sides?','Triangle','Circle','Square','Oval'),
            ('Size','Which word means the opposite of big?','Small','Tall','Round','Long'),
            ('Sorting','Which item is usually worn on your feet?','Shoes','Hat','Scarf','Gloves'),
            ('Daily order','What do you usually do before eating a meal?','Wash your hands','Put food on the floor','Sleep at the table','Hide the plate')]:add(reason,topic,p,a,w1,w2,w3)
    elif g>=4:
        for topic,p,a,w1,w2,w3 in [
            ('Logical deduction','All zibs are wugs. All wugs are tams. What must be true?','All zibs are tams','All tams are zibs','No zibs are tams','All wugs are zibs'),
            ('Logical deduction','Some painters are runners. Can we conclude that all painters are runners?','No, only some are known to be runners','Yes, all are runners','Yes, none are runners','No painters exist'),
            ('Direction sense','Facing north, you turn right, then right again. Which direction do you face?','South','North','East','West'),
            ('Direction sense','Walk 3 km east and then 3 km west. Where are you relative to the start?','At the starting point','3 km east','6 km east','3 km west')]:add(reason,topic,p,a,w1,w2,w3)
    for sid,name,qs in [('maths','Maths',maths),('reasoning','Logical Reasoning',reason)]:
        assert len(qs)>=10 and len({q[0] for q in qs})==len(qs)
        bank[str(g)].append({'id':'olympiad_'+sid,'name':('Early Challenge: ' if g<=0 else 'Olympiad: ')+name,'topic':'Original problem-solving challenges · Patterns, puzzles and application','sources':[],'questions':qs})
path=Path(__file__).resolve().parents[1]/'backend/data/olympiad.json'
path.write_text(json.dumps(bank,ensure_ascii=False,indent=2)+'\n')
print(sum(len(s['questions']) for ss in bank.values() for s in ss),'original challenge questions')

import runpy
expand_class2 = runpy.run_path(str(Path(__file__).resolve().parent / "expand-class2.py"))["expand"]
expand_class2()
