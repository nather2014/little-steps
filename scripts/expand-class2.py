"""Idempotent, original Class 2 questions; leaves other grades unchanged."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]

def expand():
 regular=json.loads((ROOT/'backend/data/curriculum.json').read_text());olympiad=json.loads((ROOT/'backend/data/olympiad.json').read_text())
 sets={s['id']:s for s in regular['2']+olympiad['2']};known={sid:{q[0] for q in s['questions']} for sid,s in sets.items()};added={sid:0 for sid in sets}
 def add(sid,topic,prompt,answer,wrong,explanation,difficulty='normal'):
  if prompt in known[sid]:return
  choices=list(dict.fromkeys([str(answer)]+[str(x) for x in wrong if str(x)!=str(answer)]));assert len(choices)>=4,(prompt,choices)
  choices=choices[:4];shift=int(hashlib.sha256(prompt.encode()).hexdigest()[:2],16)%4;choices=choices[shift:]+choices[:shift]
  sets[sid]['questions'].append([prompt,choices,choices.index(str(answer)),topic,{'difficulty':difficulty,'explanation':explanation,'generator':'class2-expansion-v1'}]);known[sid].add(prompt);added[sid]+=1
 def num(sid,topic,prompt,answer,explanation,difficulty='normal'):
  wrong=[answer+1,answer+10,max(0,answer-1),answer+2,max(0,answer-2),answer+20]
  add(sid,topic,prompt,answer,wrong,explanation,difficulty)
 # Number sense, operations, measurement and small everyday problems.
 for n in range(12,100,5):
  num('maths','Place value',f'How many tens are in {n}?',n//10,f'{n} has {n//10} tens and {n%10} ones.','easier')
  num('maths','Place value',f'How many ones are in {n}?',n%10,f'The ones digit of {n} is {n%10}.','easier')
  num('maths','Comparing numbers',f'Which number comes just after {n}?',n+1,f'Count forward one: {n} + 1 = {n+1}.','easier')
  num('maths','Comparing numbers',f'Which number comes just before {n}?',n-1,f'Count back one: {n} − 1 = {n-1}.','easier')
 for a in range(11,61,3):
  b=2+a%9
  num('maths','Addition',f'Add {a} and {b}.',a+b,f'{a} + {b} = {a+b}.')
  num('maths','Subtraction',f'Subtract {b} from {a}.',a-b,f'{a} − {b} = {a-b}.')
  num('maths','Addition',f'Meera has {a} stickers. She gets {b} more. How many stickers does she have now?',a+b,f'Getting more means add: {a} + {b} = {a+b}.')
  num('maths','Subtraction',f'A basket has {a} mangoes. {b} are taken out. How many mangoes remain?',a-b,f'Taking away means subtract: {a} − {b} = {a-b}.')
 for groups in range(2,7):
  for each in range(2,6):
   num('maths','Equal groups',f'{groups} plates have {each} biscuits each. How many biscuits are there altogether?',groups*each,f'Add {each} once for each of the {groups} plates: {groups} × {each} = {groups*each}.')
   num('maths','Sharing equally',f'Share {groups*each} beads equally among {groups} children. How many beads does each child get?',each,f'{groups} equal groups of {each} make {groups*each}.')
 for n in range(2,16):
  num('maths','Patterns',f'What comes next: {n}, {n+2}, {n+4}, __?',n+6,'Each number increases by 2.')
  num('maths','Patterns',f'What comes next: {n*5}, {(n+1)*5}, {(n+2)*5}, __?',(n+3)*5,'Count forward in steps of 5.')
 for n in range(4,16):
  num('maths','Measurement',f'A red ribbon is {n} cm long. A blue ribbon is {n+1+n%5} cm long. How many centimetres longer is the blue ribbon?',1+n%5,f'Compare the lengths: {n+1+n%5} − {n} = {1+n%5} centimetres.')
  num('maths','Data',f'A chart shows {n} children chose apples and {n+2} chose bananas. How many children chose these fruits altogether?',2*n+2,f'Add the two groups: {n} + {n+2} = {2*n+2}.')
 for h in range(1,12):
  num('maths','Time',f'One hour after {h} o’clock, what hour will the clock show?',h+1,f'The hour after {h} o’clock is {h+1} o’clock.','easier')
 for name,sides in [('triangle',3),('square',4),('rectangle',4),('pentagon',5),('hexagon',6)]:
  num('maths','Shapes',f'A {name} has how many straight sides?',sides,f'A {name} has {sides} straight sides.','easier')
 # English: explicit tasks avoid multiple grammatically valid article answers.
 article_words=[('apple','an'),('orange','an'),('egg','an'),('umbrella','an'),('ant','an'),('elephant','an'),('owl','an'),('igloo','an'),('insect','an'),('eraser','an'),('arm','an'),('ear','an'),('alligator','an'),('apron','an'),('onion','an'),('octopus','an'),('ice cube','an'),('envelope','an'),('engine','an'),('oar','an'),('ball','a'),('cat','a'),('dog','a'),('book','a'),('pencil','a'),('kite','a'),('bus','a'),('tree','a'),('flower','a'),('cup','a'),('desk','a'),('hat','a'),('sock','a'),('rabbit','a'),('tiger','a'),('lion','a'),('window','a'),('chair','a'),('nest','a'),('spoon','a')]
 for word,article in article_words:add('english','Articles',f"Choose 'a' or 'an': ___ {word}.",article,['an' if article=='a' else 'a','is','are'],f"Use '{article}' before '{word}' because it begins with {'a vowel' if article=='an' else 'a consonant'} sound.",'easier')
 plurals=[('cat','cats'),('dog','dogs'),('book','books'),('tree','trees'),('cup','cups'),('pen','pens'),('bird','birds'),('flower','flowers'),('ball','balls'),('kite','kites'),('hat','hats'),('toy','toys'),('boy','boys'),('girl','girls'),('car','cars'),('door','doors'),('chair','chairs'),('shoe','shoes'),('sock','socks'),('egg','eggs'),('bus','buses'),('box','boxes'),('dish','dishes'),('brush','brushes'),('fox','foxes'),('bench','benches'),('baby','babies'),('puppy','puppies'),('city','cities'),('story','stories'),('leaf','leaves'),('wolf','wolves'),('child','children'),('foot','feet'),('tooth','teeth'),('mouse','mice')]
 for singular,plural in plurals:add('english','Plurals',f'What is the plural of “{singular}”?',plural,[singular,singular+'ing',singular+'ed'],f'One {singular}; more than one are {plural}.')
 opposites=[('hot','cold'),('big','small'),('up','down'),('in','out'),('open','closed'),('happy','sad'),('clean','dirty'),('full','empty'),('fast','slow'),('early','late'),('near','far'),('wet','dry'),('day','night'),('inside','outside'),('above','below'),('left','right'),('thick','thin'),('hard','soft'),('heavy','light'),('new','old'),('long','short'),('tall','short'),('wide','narrow'),('first','last')]
 for word,answer in opposites:add('english','Opposites',f'Which word means the opposite of “{word}”?',answer,[x for x in ['round','green','noisy','wooden','happy'] if x!=answer],f'{word.capitalize()} and {answer} have opposite meanings.')
 rhymes=[('cat','hat'),('dog','log'),('sun','bun'),('pen','hen'),('bed','red'),('ball','tall'),('fish','dish'),('cake','lake'),('boat','coat'),('bee','tree'),('star','car'),('mouse','house'),('king','ring'),('chair','fair'),('blue','shoe'),('goat','float'),('light','night'),('rain','train'),('fox','box'),('bell','shell'),('duck','truck'),('moon','spoon'),('hop','top'),('book','cook')]
 for word,answer in rhymes:add('english','Rhyming',f'Which word rhymes with “{word}”?',answer,[x for x,y in rhymes if x!=word][:3],f'{word.capitalize()} and {answer} end with the same sound.')
 nouns=['teacher','garden','school','pencil','table','child','rabbit','river','tree','doctor','chair','village','flower','bus','book','mother','father','market','park','kitchen']
 for noun in nouns:add('english','Naming words',f'Find the naming word in “Look at the {noun}.”',noun,['look','at','the'],f'{noun.capitalize()} is a naming word (noun).','easier')
 verbs=[('birds','fly'),('fish','swim'),('children','play'),('dogs','bark'),('babies','cry'),('students','read'),('artists','paint'),('cooks','cook'),('runners','run'),('singers','sing'),('dancers','dance'),('writers','write')]
 for who,action in verbs:add('english','Action words',f'Find the action word: “The {who} {action}.”',action,['the',who,'small'],f'{action.capitalize()} tells what the {who} do.','easier')
 adjectives=[('red','apple'),('small','ant'),('big','elephant'),('soft','pillow'),('round','ball'),('green','leaf'),('cold','water'),('hot','soup'),('sweet','mango'),('blue','kite'),('long','rope'),('tall','tree'),('clean','shirt'),('happy','child'),('fast','train'),('bright','star')]
 for adj,noun in adjectives:add('english','Adjectives',f'Which word describes the {noun} in “a {adj} {noun}”?',adj,[noun,'a','is'],f'{adj.capitalize()} describes the {noun}.')
 for names,pronoun in [('Ravi is a boy','He'),('Rita is a girl','She'),('The puppy is an animal','It'),('Ravi and Rita are two children','They')]:
  for action in (['is sleeping','is eating','is running'] if pronoun=='It' else ['is playing' if pronoun!='They' else 'are playing','is reading' if pronoun!='They' else 'are reading','is happy' if pronoun!='They' else 'are happy']):
   add('english','Pronouns',f'{names}. Choose the pronoun: “___ {action}.”',pronoun,[p for p in ['He','She','It','They'] if p!=pronoun],f'{pronoun} can replace the named '+('children.' if pronoun=='They' else 'person or animal.'))
 for thing in ['ball','toy','pencil','book']:
  for position,word in [('inside','in'),('below','under'),('on top of','on'),('behind','behind')]:
   add('english','Prepositions',f'The {thing} is {position} the box. Choose the matching position word: the {thing} is ___ the box.',word,[p for p in ['in','under','on','behind'] if p!=word],f'{word.capitalize()} tells where the {thing} is.')
 for name,item,color,place in [('Asha','kite','red','park'),('Ravi','ball','blue','garden'),('Meera','book','green','library'),('Kabir','bag','yellow','school'),('Tara','hat','pink','market'),('Nila','cup','white','kitchen'),('Dev','toy','orange','room'),('Anu','pencil','purple','classroom'),('Sara','ribbon','brown','shop'),('Arun','umbrella','black','bus stop')]:
  story=f'{name} has a {color} {item}. {name} takes it to the {place}.'
  add('english','Reading',f'Read: “{story}” What does {name} have?',item,[x for x in ['sock','spoon','shoe','bell'] if x!=item],f'The first sentence says {name} has a {item}.')
  add('english','Reading',f'Read: “{story}” What colour is the {item}?',color,[x for x in ['red','blue','green','yellow'] if x!=color],f'The story describes the {item} as {color}.')
  add('english','Reading',f'Read: “{story}” Where does {name} take the {item}?',place,[x for x in ['beach','farm','zoo','station'] if x!=place],f'The second sentence says {name} takes it to the {place}.')
 # Everyday-world knowledge: authored facts rather than renamed duplicates.
 facts={
 'Animals':[
 ('Which animal has a trunk?','Elephant',['Cat','Goat','Dog'],'An elephant uses its long trunk to smell and pick things up.'),('Which animal has stripes?','Tiger',['Cow','Goat','Rabbit'],'Tigers have stripes on their bodies.'),('Which animal has a very long neck?','Giraffe',['Dog','Cat','Sheep'],'A giraffe has a long neck.'),('Which of these is a bird?','Sparrow',['Cat','Dog','Goat'],'A sparrow has feathers and is a bird.'),('Which of these lives in water and has fins?','Fish',['Hen','Dog','Goat'],'Fish use fins to move through water.'),('Which animal makes a web?','Spider',['Ant','Butterfly','Bee'],'A spider spins a web.'),('Which animal gives us wool?','Sheep',['Hen','Duck','Fish'],'Wool comes from the fleece of sheep.'),('Which animal carries its home-like shell on its back?','Snail',['Cat','Horse','Cow'],'A snail has a shell on its back.')],
 'Plants':[
 ('Which part of a plant usually grows below the soil?','Roots',['Leaves','Flowers','Fruits'],'Roots usually grow in soil.'),('Which plant part takes in water from the soil?','Roots',['Petals','Fruits','Seeds'],'Roots take in water from the soil.'),('Which part supports the leaves of a plant?','Stem',['Fruit','Petal','Seed'],'The stem supports the plant’s leaves.'),('Which of these is a seed we eat?','Pea',['Stone','Plastic','Sand'],'Peas are seeds.'),('What can a seed grow into?','A new plant',['A chair','A spoon','A stone'],'A seed can grow into a new plant when it has suitable conditions.'),('Which part of a plant may grow into a fruit?','Flower',['Root','Dry leaf','Branch tip'],'Many flowers develop into fruits.'),('Which of these helps a plant grow?','Water',['Plastic bags','Paint','Broken glass'],'Plants need water to grow.'),('Which of these is a root vegetable?','Carrot',['Apple','Mango','Grape'],'The carrot we eat is a root.')],
 'Healthy habits':[
 ('What should you do before eating?','Wash your hands',['Touch a dusty shoe','Play in mud','Skip washing'],'Washing hands removes dirt and germs.'),('What should you use to clean your teeth?','Toothbrush',['Comb','Spoon','Shoe'],'A toothbrush helps clean teeth.'),('What should you do when you cough or sneeze?','Cover your mouth and nose',['Cough into someone’s face','Share your used tissue','Leave tissues on the floor'],'Covering helps keep germs from spreading.'),('Which drink should be safe and clean before we drink it?','Water',['Paint','Glue','Ink'],'We should drink safe, clean water.'),('Which habit helps the body rest?','Getting enough sleep',['Staying awake every night','Skipping all rest','Watching a screen all night'],'Sleep helps the body rest.'),('What should you do after using the toilet?','Wash your hands with soap',['Wipe hands on food','Skip washing','Share a dirty towel'],'Soap and water help clean hands.'),('Where should you put used tissues?','In a waste bin',['On a plate','On the floor','Inside a water bottle'],'Used tissues belong in a bin.'),('Which is a healthy everyday activity?','Playing outdoors safely',['Sitting still all day','Skipping sleep','Eating only sweets'],'Safe active play helps us stay healthy.')],
 'Food':[
 ('Which of these is a fruit?','Mango',['Potato','Rice','Salt'],'A mango is a fruit.'),('Which of these is a vegetable?','Spinach',['Sugar','Milk','Rice'],'Spinach is a leafy vegetable.'),('Which of these is made from milk?','Curd',['Rice','Salt','Apple'],'Curd is made from milk.'),('Which of these is a grain?','Rice',['Mango','Milk','Water'],'Rice is a grain.'),('Which food is a pulse?','Lentils',['Sugar','Salt','Butter'],'Lentils are pulses.'),('What should you do with fruits before eating them?','Wash them with clean water',['Cover them with mud','Paint them','Put them on a dirty floor'],'Washing helps remove dirt.'),('Which meal is usually eaten in the morning?','Breakfast',['Dinner','Midnight snack','Evening tea'],'Breakfast is the morning meal.'),('Which food comes from a hen?','Egg',['Apple','Rice','Carrot'],'A hen lays eggs.')],
 'Community helpers':[
 ('Who helps treat people who are ill?','Doctor',['Tailor','Carpenter','Postman'],'A doctor treats people who are ill.'),('Who stitches clothes?','Tailor',['Doctor','Farmer','Driver'],'A tailor stitches clothes.'),('Who grows crops?','Farmer',['Pilot','Tailor','Dentist'],'A farmer grows crops.'),('Who teaches children at school?','Teacher',['Plumber','Pilot','Tailor'],'A teacher helps children learn.'),('Who repairs leaking water pipes?','Plumber',['Teacher','Doctor','Farmer'],'A plumber repairs water pipes.'),('Who helps put out fires?','Firefighter',['Tailor','Farmer','Dentist'],'Firefighters help put out fires.'),('Who takes care of teeth?','Dentist',['Pilot','Driver','Carpenter'],'A dentist cares for teeth.'),('Who makes things such as wooden tables?','Carpenter',['Doctor','Pilot','Plumber'],'A carpenter works with wood.')],
 'Safety':[
 ('What should you do at a red traffic light?','Stop',['Speed up','Run across blindly','Close your eyes'],'Red means stop.'),('Where should you cross a road when a marked crossing is available?','At the crossing with an adult',['Between fast-moving cars','Behind a parked bus without looking','Anywhere without looking'],'Use a safe marked crossing with an adult.'),('What should you do if you see a loose electrical wire?','Stay away and tell an adult',['Touch it','Pull it','Put water on it'],'Stay away from electrical wires and tell an adult.'),('Which should a child avoid touching without an adult?','A hot iron',['A soft pillow','A storybook','A pencil'],'A hot iron can burn.'),('What should you wear when riding a bicycle?','A properly fitted helmet',['A paper bag over your eyes','Loose string around your neck','Nothing on your head'],'A helmet helps protect your head.'),('What should you do if you get lost in a shop?','Ask a staff member for help finding your trusted adult',['Leave with an unknown person','Hide silently','Run into the road'],'A shop staff member can help find your trusted adult.'),('What should you do before taking medicine?','Ask your parent or caregiver',['Take any tablet you find','Share someone’s medicine','Guess the amount'],'An adult must check medicines.'),('What should you do if a toy breaks into sharp pieces?','Tell an adult and stay away from the sharp pieces',['Pick up the sharp pieces with bare hands','Put pieces in your mouth','Throw pieces at others'],'Sharp pieces can hurt; ask an adult for help.')],
 'Water':[
 ('Which action saves water while brushing teeth?','Turn off the tap when not using it',['Leave the tap running','Break the tap','Spill a bucket'],'Turning off an unused tap saves water.'),('Where does rain come from?','Clouds',['Roads','Chairs','Books'],'Rain falls from clouds.'),('Which of these needs water to live?','A plant',['A plastic toy','A chair','A stone'],'Living plants need water.'),('What should you do if a tap keeps dripping?','Tell an adult so it can be repaired',['Ignore it forever','Leave it fully open','Put dirt inside it'],'Repairing a dripping tap saves water.'),('What do we call water when it freezes?','Ice',['Sand','Oil','Smoke'],'Frozen water is ice.'),('Which container helps carry drinking water to school?','A clean water bottle',['An open dirty shoe','A paper notebook','A broken plate'],'A clean water bottle keeps water safely contained.')],
 'Transport':[
 ('Which vehicle travels on railway tracks?','Train',['Bus','Car','Bicycle'],'Trains travel on railway tracks.'),('Which vehicle flies in the sky?','Aeroplane',['Bus','Bicycle','Boat'],'An aeroplane travels through the air.'),('Which vehicle travels on water?','Boat',['Train','Bicycle','Bus'],'A boat travels on water.'),('Which vehicle has two wheels and pedals?','Bicycle',['Bus','Train','Boat'],'A bicycle has two wheels and pedals.'),('Which vehicle carries people who need urgent medical help?','Ambulance',['Tractor','Bicycle','Goods train'],'An ambulance carries people needing medical help.'),('Which of these is public transport?','City bus',['Your toy car','A dining chair','A school desk'],'A city bus carries members of the public.')],
 'Clothes':[
 ('What do we wear on our feet?','Shoes',['Hat','Gloves','Scarf'],'Shoes protect our feet.'),('What helps keep us dry when we walk in rain?','Raincoat',['Woollen blanket indoors','Cotton handkerchief alone','School notebook'],'A raincoat protects clothes from rain.'),('What do we wear on our hands in cold weather?','Gloves',['Shoes','Hat','Socks'],'Gloves keep hands warm.'),('Which clothing is useful in cold weather?','Woollen sweater',['Thin sleeveless vest','Wet shirt','Paper apron'],'A woollen sweater helps keep us warm.'),('What should you do with dirty clothes?','Put them aside for washing',['Wear them forever without washing','Hide food in them','Throw them into drinking water'],'Dirty clothes should be washed.'),('Which item covers the head?','Hat',['Socks','Shoes','Gloves'],'A hat is worn on the head.')],
 'Homes':[
 ('Which room is mainly used for cooking?','Kitchen',['Bathroom','Bedroom','Garage'],'Meals are cooked in a kitchen.'),('Which room is mainly used for bathing?','Bathroom',['Kitchen','Dining room','Garage'],'People bathe in a bathroom.'),('What lets light and air into a room?','Window',['Closed cupboard','Solid wall','Floor mat'],'A window can let in light and air.'),('What should you do after playing with toys at home?','Put them back in their place',['Leave them on stairs','Throw them out of a window','Hide them in the oven'],'Putting toys away keeps rooms tidy and paths safe.'),('Why do we need a home?','For shelter and safety',['To stop us breathing','To keep us from all learning','To store only stones'],'A home provides shelter and safety.'),('Where should waste go at home?','In a waste bin',['On the floor','On the bed','In a drinking cup'],'Use a waste bin to keep the home clean.')],
 'Time and seasons':[
 ('What usually comes after morning in a day?','Afternoon',['Yesterday','Last week','Midnight before morning'],'Morning is followed by afternoon.'),('What comes after Monday?','Tuesday',['Sunday','Friday','Saturday'],'Tuesday follows Monday.'),('How many days are in a week?','Seven',['Five','Eight','Ten'],'A week has seven days.'),('Which object tells us the time?','Clock',['Spoon','Comb','Plate'],'A clock shows the time.'),('Which weather is shown by water drops falling from clouds?','Rainy',['Sunny','Dry and cloudless','Snowy'],'Water drops falling from clouds are rain.'),('Which item helps on a sunny day outdoors?','A sun hat',['A hot iron','A heavy blanket over the face','A lit match'],'A sun hat can shade your head.')]
 }
 for topic,entries in facts.items():
  for prompt,answer,wrong,explanation in entries:add('evs',topic,prompt,answer,wrong,explanation,'easier')
 # Independent Olympiad-style application, not official competition papers.
 for n in range(8,38):
  num('olympiad_maths','Two-step problems',f'Nila has {n} beads. She gets 5 more and gives away 3. How many beads are left?',n+2,f'First add 5, then subtract 3: {n} + 5 − 3 = {n+2}.','challenging')
  num('olympiad_maths','Missing numbers',f'Fill the box: □ + 7 = {n+7}.',n,f'Take away 7 from {n+7}: {n+7} − 7 = {n}.')
  num('olympiad_maths','Money problems',f'A notebook costs ₹{n}. A pencil costs ₹4. How much do they cost together?',n+4,f'Add the prices: ₹{n} + ₹4 = ₹{n+4}.')
  num('olympiad_maths','Comparing differences',f'Asha reads {n+1+n%7} pages. Ravi reads {n} pages. How many more pages does Asha read?',1+n%7,f'{n+1+n%7} − {n} = {1+n%7} pages.')
 for groups in range(2,7):
  for each in range(2,6):
   num('olympiad_maths','Equal groups',f'{groups} bags hold {each} marbles each. One more marble is added. How many marbles are there?',groups*each+1,f'{groups} × {each} = {groups*each}; add 1 to get {groups*each+1}.','challenging')
   num('olympiad_reasoning','Number patterns',f'Find the missing number: {groups}, {groups+each}, □, {groups+3*each}.',groups+2*each,f'Add {each} at each step.')
 for start in range(1,21):
  num('olympiad_reasoning','Number patterns',f'Continue the pattern: {start}, {start+3}, {start+6}, {start+9}, __.',start+12,'The pattern adds 3 each time.')
  num('olympiad_reasoning','Reverse patterns',f'Continue the pattern: {start+12}, {start+10}, {start+8}, __.',start+6,'The pattern subtracts 2 each time.')
  num('olympiad_reasoning','Position in a line',f'There are {start+4} children in a line. Tara is at position {start} from the front. How many children stand in front of Tara?',start-1,f'{start-1} children come before position {start}.')
 for first in range(0,18):
  letters=[chr(65+first+2*i) for i in range(4)];answer=chr(65+first+6)
  add('olympiad_reasoning','Letter patterns',f'Which letter comes next: {letters[0]}, {letters[1]}, {letters[2]}, __?',answer,[chr(65+first+5),chr(65+first+4),chr(65+first+7)],'Skip one alphabet letter at each step.')
 for facing,right,left in [('north','east','west'),('east','south','north'),('south','west','east'),('west','north','south')]:
  for turn,answer in [('right',right),('left',left)]:add('olympiad_reasoning','Direction sense',f'You face {facing} and turn {turn} once. Which direction do you face now?',answer,[d for d in ['north','east','south','west'] if d!=answer],f'A {turn} turn from {facing} makes you face {answer}.')
 for path,bank in [(ROOT/'backend/data/curriculum.json',regular),(ROOT/'backend/data/olympiad.json',olympiad)]:
  path.write_text(json.dumps(bank,ensure_ascii=False,indent=2)+'\n')
 print('Class 2 additions:',added)
 print('Class 2 totals:',{sid:len(s['questions']) for sid,s in sets.items()},'+ 24 runtime borrowing questions')
 return added
if __name__=='__main__':expand()
