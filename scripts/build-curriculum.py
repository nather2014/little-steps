"""Build original practice questions. Topic references are documented in CURRICULUM.md."""
import json
from pathlib import Path
from fractions import Fraction
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
BANK={str(g):[] for g in range(-1,11)}
NAMES={'maths':'Mathematics','english':'English','evs':'The World Around Us','science':'Science','social':'Social Science'}
NCERT='https://ncert.nic.in/textbook.php'
FOUNDATION='https://ncert.nic.in/flipbook/NCF/National_Curriculum_Framework_for_Foundational_Stage_2022/files/basic-html/page37.html'
CBSE='https://cbseacademic.nic.in/curriculum_2027.html'
def subject(g,s):
    for item in BANK[str(g)]:
        if item['id']==s:return item
    item={'id':s,'name':NAMES[s],'topic':'','sources':[FOUNDATION if g<=0 else (CBSE if g>=9 else NCERT)],'questions':[]}
    BANK[str(g)].append(item)
    return item
def q(g,s,t,p,a,*wrong):
    options=[str(a),*[str(x) for x in wrong]]
    assert len(options)>=2 and len(options)==len(set(options)),(g,p,options)
    shift=sum(ord(c) for c in p)%len(options)
    options=options[shift:]+options[:shift]
    subject(g,s)['questions'].append([p,options,options.index(str(a)),t])
def num(g,t,p,a):
    q(g,'maths',t,p,a,a+1,a+2,a-1)
def rows(g,s,text):
    for line in text.strip().splitlines():
        t,p,a,*wrong=line.split('|');q(g,s,t,p,a,*wrong)

for g in [-1,0]:
    for n in range(1,6 if g==-1 else 11):
        num(g,'Counting',f'Count the stars: {"★ " * n}',n)
        if g==0:num(g,'Number order',f'Which number comes after {n}?',n+1)
    rows(g,'maths',"""
Shapes|Which shape is round?|Circle|Square|Triangle
Shapes|Which shape has three corners?|Triangle|Circle|Square
Size|An elephant and an ant: which is bigger?|Elephant|Ant|Both are the same size
Position|A bird is above a tree. Where is the bird?|Above|Below|Inside
Patterns|Finish the pattern: ● ▲ ● ▲ ...|●|▲|■
Sorting|Which item is different: ball, orange, book?|Book|Ball|Orange
Comparison|Which group has more: ★★ or ★★★★?|★★★★|★★|Both have the same number
Measurement|Which is usually longer: a pencil or a bus?|Bus|Pencil|Both have the same length
""")
    rows(g,'english',"""
Letters|Which is the letter A?|A|B|C
Letters|Which letter starts the word ball?|B|D|M
Sounds|Which word starts with the same sound as sun?|Sock|Cat|Dog
Rhyming|Which word rhymes with cat?|Hat|Sun|Dog
Vocabulary|What do we wear on our feet?|Shoes|Hat|Gloves
Listening|A grown-up says 'sit down'. What should you do?|Sit on a chair|Run away|Jump up
Opposites|What is the opposite of big?|Small|Tall|Fast
Speaking|What can you say when someone helps you?|Thank you|Go away|Stop helping
Stories|Mia feeds a hungry puppy. Who gets the food?|The puppy|A tree|A toy
Colours|Which colour word matches a ripe red tomato?|Red|Blue|Purple
""")
    if g==0:
        rows(g,'english',"""
Letters|Which letter comes after D?|E|B|C
Sounds|Complete the word: d_g.|o|a|i
Rhyming|Which word rhymes with pen?|Hen|Cup|Box
Vocabulary|Choose the name of a fruit.|Mango|Chair|Shoe
Stories|Ravi puts on a raincoat because it is raining. What keeps him dry?|Raincoat|Ball|Spoon
""")
    rows(g,'evs',"""
My body|What do you use to see?|Eyes|Ears|Feet
My body|What do you use to hear?|Ears|Eyes|Knees
Healthy habits|What should we do before eating?|Wash our hands|Touch dirty shoes|Play in mud
Healthy habits|What do we use to clean our teeth?|Toothbrush|Comb|Shoe
Safety|Who should help you cross a busy road?|A trusted grown-up|A toy|A pet
Feelings|Your friend is sad. What is a kind thing to do?|Ask if they need help|Laugh at them|Hide their bag
Plants|What does a plant need to grow?|Water|Plastic|Shoes
Animals|Which animal says 'moo'?|Cow|Dog|Cat
Our home|Where do we usually sleep?|Bed|Sink|Cupboard shelf
Weather|What can protect us from rain outside?|Umbrella|Comb|Plate
Sharing|Two children want the same toy. What is fair?|Take turns|Push each other|Hide it forever
Our surroundings|Where should we put waste?|In a bin|On the road|In a pond
""")
    if g==0:
        rows(g,'evs',"""
Food|Which is a fruit we can eat?|Banana|Stone|Chalk
Transport|Which vehicle travels on railway tracks?|Train|Boat|Bicycle
Community|Who helps put out fires?|Firefighter|Baker|Tailor
Seasons|What do we wear to keep warm in cold weather?|Sweater|Raincoat only|Swimming costume
Family|How can we help at home?|Put toys away|Leave taps running|Throw food on the floor
""")

# Number problems are varied, but each carries a specific topic for feedback.
for g in range(1,6):
    scale=1 if g==1 else 10**(g-1)
    for n in range(2,10):
        a=n*scale+3;b=n+2
        num(g,'Addition',f'What is {a} + {b}?',a+b)
        num(g,'Subtraction',f'What is {a+b} − {b}?',a)
        if g>=2:
            num(g,'Equal groups',f'{n} baskets have {b} apples each. How many apples altogether?',n*b)
            num(g,'Sharing equally',f'Share {n*b} beads equally among {b} children. How many does each get?',n)
        if g>=3:
            num(g,'Measurement',f'How many centimetres are there in {n} metres?',100*n)
            num(g,'Money',f'A notebook costs ₹{n*10}. What do {b} notebooks cost?',n*10*b)
    rows(g,'maths',"""
Shapes|Which shape has four equal sides and four square corners?|Square|Triangle|Circle|Pentagon
Patterns|What comes next: 2, 4, 6, 8, ...?|10|9|11|12
Time|How many days are in one week?|7|5|6|8
Comparing numbers|Which is the greatest number: 18, 12, 15, 9?|18|12|15|9
Data|Three children choose mango and two choose apple. Which fruit gets more votes?|Mango|Apple|Both get equal votes
Position|In a line, Sam is before Neha. Who comes earlier?|Sam|Neha|Both are last
""")
    if g>=2:
        rows(g,'maths',"""
Place value|What is the value of 4 in 246?|40|4|400|4000
Fractions|A cake is cut into four equal parts. One part is what fraction?|1/4|1/2|3/4|4/1
Time|How many minutes make one hour?|60|30|100|24
Measurement|Which unit would you use for the mass of a school bag?|Kilograms|Litres|Hours|Metres
""")
    if g>=3:
        rows(g,'maths',"""
Fractions|Which fraction is equal to one half?|2/4|1/4|3/4|4/2
Data|Find the number that appears most often: 2, 3, 2, 4, 2.|2|3|4|5
""")
    if g>=4:
        rows(g,'maths',"""
Perimeter|A square has side 6 cm. What is its perimeter?|24 cm|12 cm|36 cm|6 cm
Area|A rectangle is 5 cm long and 3 cm wide. What is its area?|15 square cm|8 square cm|16 square cm|30 square cm
Decimals|Write 3 tenths as a decimal.|0.3|3.0|0.03|30.0
Symmetry|Which shape has no straight sides?|Circle|Square|Rectangle|Triangle
""")
    if g==5:
        rows(g,'maths',"""
Factors|Which number is a factor of 24?|6|5|7|9
Multiples|Which number is a multiple of 8?|32|30|34|36
Volume|How many unit cubes fill a box 2 units by 3 units by 4 units?|24|9|12|18
Fractions|What is 1/4 + 2/4?|3/4|3/8|1/4|1/2
Decimals|What is 1.25 + 0.50?|1.75|1.30|1.50|2.25
Angles|An angle smaller than a right angle is called what?|Acute|Obtuse|Straight|Reflex
""")
for g in range(6,11):
    for n in range(2,10):
        if g<=8:
            num(g,'Integers',f'What is {n} + (−{n+4})?',-4)
            num(g,'Fractions',f'What is {n}/3 + {2*n}/3?',n)
            num(g,'Number patterns',f'What comes next: {n}, {2*n}, {3*n}, ...?',4*n)
        if g>=7:
            num(g,'Expressions',f'If x = {n}, what is 3x + 2?',3*n+2)
            num(g,'Equations',f'Solve x + {n} = {3*n}.',2*n)
        if g>=8:
            num(g,'Squares and cubes',f'What is {n}²?',n*n)
            num(g,'Exponents',f'What is 2^{n}?',2**n)
        if g>=9:
            num(g,'Polynomials',f'For p(x) = x² + 2, find p({n}).',n*n+2)
            num(g,'Statistics',f'Find the mean of {n}, {n+2}, {n+4}.',n+2)
        if g==10:
            num(g,'Arithmetic progressions',f'The sequence starts {n}, {n+3}, {n+6}. Find its fifth term.',n+12)
            num(g,'Coordinate geometry',f'Find the distance between (0, 0) and ({3*n}, {4*n}).',5*n)
    rows(g,'maths',"""
Angles|What is the size of a right angle?|90°|45°|180°|360°
Fractions|Which is greater: 2/3 or 1/3?|2/3|1/3|They are equal
Perimeter and area|A rectangle is 8 cm by 3 cm. Find its area.|24 square cm|22 square cm|11 square cm|48 square cm
Number play|Which number is prime?|13|15|21|27
Symmetry|How many lines of symmetry does a square have?|4|1|2|3
Data handling|Which value occurs most often in 3, 5, 3, 8, 3, 5?|3|5|8|6
""")
    if g>=7:
        rows(g,'maths',"""
Decimals|What is 0.4 × 0.2?|0.08|0.8|0.008|8
Triangles|Two angles of a triangle are 50° and 60°. Find the third.|70°|80°|90°|110°
Parallel lines|Corresponding angles between parallel lines are what?|Equal|Always 90°|Always 180°|Unequal
Rational numbers|What is the additive inverse of −3/5?|3/5|−5/3|5/3|−3/5
""")
    if g>=8:
        rows(g,'maths',"""
Comparing quantities|A ₹200 book has a 10% discount. What is the discount?|₹20|₹10|₹180|₹190
Algebraic identities|Expand (x + 2)².|x² + 4x + 4|x² + 4|x² + 2x + 4|x² + 2
Mensuration|A cube has edge 3 cm. Find its volume.|27 cubic cm|9 cubic cm|18 cubic cm|81 cubic cm
Probability|A fair coin is tossed. What is the chance of heads?|1/2|1|0|1/4
""")
    if g>=9:
        rows(g,'maths',"""
Number systems|Which number is irrational?|√2|1/2|0.25|−3
Coordinate geometry|The point (0, 5) lies on which axis?|y-axis|x-axis|Both axes|Neither axis
Polynomials|What is the degree of 4x³ + x + 1?|3|4|1|0
Linear equations|Which point satisfies x + y = 5?|(2, 3)|(1, 1)|(5, 5)|(0, 0)
Geometry|The sum of angles in a quadrilateral is what?|360°|180°|90°|270°
Circles|A radius is 4 cm. What is the diameter?|8 cm|4 cm|2 cm|16 cm
""")
    if g==9:
        rows(g,'maths',"""
Sequences and progressions|What follows 3, 7, 11, 15 in this arithmetic sequence?|19|18|20|21
Euclidean geometry|How many distinct straight lines pass through two different points?|One|Two|Three|Infinitely many
Surface area and volume|A cuboid measures 2 cm by 4 cm by 5 cm. Find its volume.|40 cubic cm|11 cubic cm|20 cubic cm|80 cubic cm
Statistics|Find the median of 2, 4, 7, 9, 10.|7|4|9|6
""")
    if g==10:
        rows(g,'maths',"""
Real numbers|Find the HCF of 18 and 24.|6|3|12|72
Quadratic equations|The roots of x² − 5x + 6 = 0 are what?|2 and 3|1 and 6|−2 and −3|0 and 5
Trigonometry|In a right triangle, sin θ equals which ratio?|Opposite / hypotenuse|Adjacent / hypotenuse|Opposite / adjacent|Hypotenuse / opposite
Trigonometry|What is sin 30°?|1/2|1|0|√3/2
Triangles|If corresponding sides of similar triangles are in ratio 2:3, their areas are in what ratio?|4:9|2:3|8:27|3:2
Circles|A tangent at a circle's point of contact is perpendicular to what?|The radius to that point|Every chord|Every tangent|The diameter elsewhere
Surface area and volume|A cylinder has radius 2 cm and height 5 cm. What is its volume?|20π cubic cm|10π cubic cm|4π cubic cm|40π cubic cm
Probability|A fair die is rolled. What is the chance of an even number?|1/2|1/6|1/3|2/3
""")

ENGLISH={
1:"""
Letters|Which letter comes after F?|G|E|H|D
Vowels|Which letter is a vowel?|E|B|D|T
Sounds|Which word starts with the sound /m/?|Mat|Cat|Sun|Dog
Rhyming|Which word rhymes with bed?|Red|Cat|Sun|Cup
Vocabulary|Which word names something we read?|Book|Shoe|Plate|Ball
Opposites|What is the opposite of up?|Down|Fast|Big|Hot
Naming words|Which word names an animal?|Rabbit|Jump|Blue|Slow
Action words|Which word is an action?|Run|Chair|Green|Pencil
Reading|Asha has a blue kite. What colour is the kite?|Blue|Red|Green|Yellow
Sentences|Choose the complete sentence.|The cat sleeps.|Cat the.|Sleeps cat the.|The.
""",
2:"""
Nouns|Which word names a place?|School|Jump|Quickly|Happy
Pronouns|Replace 'Ria' in 'Ria is reading'.|She|He|It|They
Verbs|Complete: Birds ___ in the sky.|fly|swim|crawl|write
Articles|Choose: ___ orange.|An|A|The a|An a
Plurals|What is the plural of box?|Boxes|Boxs|Boxies|Boxen
Opposites|What is the opposite of empty?|Full|Slow|Short|Cold
Adjectives|In 'a soft pillow', which word describes the pillow?|Soft|A|Pillow|None
Prepositions|The ball is ___ the table when it is below it.|under|over|inside|through
Punctuation|Which mark ends a question?|?|.|,|!
Reading|Dev waters a plant every morning. What does Dev water?|A plant|A car|A chair|A kite
""",
3:"""
Nouns|Which is a proper noun?|Delhi|City|River|Book
Pronouns|Ravi and I are friends. ___ play together.|We|He|It|She
Tenses|Yesterday I ___ to the park.|walked|walk|walking|walks
Adjectives|Choose the describing word in 'The tall tree gives shade'.|Tall|Tree|Gives|Shade
Adverbs|Which word tells how in 'She sang softly'?|Softly|She|Sang|None
Prepositions|Choose: The bird flew ___ the wall to the other side.|over|under|inside|below
Conjunctions|Complete: I like apples ___ bananas.|and|because|but only|so that
Vocabulary|Choose a word with a similar meaning to happy.|Glad|Angry|Tired|Sad
Punctuation|Which sentence is punctuated correctly?|Where is my bag?|Where is my bag.|Where is my bag,|where is my bag
Reading|A boy shares lunch with a friend who forgot theirs. What quality does he show?|Kindness|Carelessness|Greed|Anger
""",
4:"""
Nouns|Which is a collective noun?|Team|Player|Ball|Run
Pronouns|Choose: This book belongs to Meera. It is ___.|hers|her|she|him
Tenses|Choose the past tense of bring.|Brought|Brang|Bringed|Brung
Adjectives|Choose: This rope is ___ than that one.|longer|longest|long|most long
Adverbs|Which word modifies the verb in 'They arrived early'?|Early|They|Arrived|None
Articles|Choose: We saw ___ eagle in the sky.|an|a|a an|an a
Conjunctions|Complete: I stayed indoors ___ it was raining.|because|but|or|although only
Subject and predicate|In 'The little bird sings', what is the subject?|The little bird|Sings|Bird sings|Little
Vocabulary|Which word means the opposite of brave?|Cowardly|Bold|Fearless|Courageous
Reading|A sign says 'Keep the gate closed'. What should visitors do?|Close the gate after entering|Leave it open|Remove the gate|Paint the gate
""",
5:"""
Kinds of nouns|Which is an abstract noun?|Honesty|Chair|Delhi|Team
Tenses|Choose: She ___ her homework already.|has finished|finish|finishing|will finished
Subject–verb agreement|Choose: The children ___ in the garden.|are|is|was|has
Adjectives|Choose: Of the three boxes, this is the ___.|heaviest|heavier|heavy|more heavy
Adverbs|Choose the adverb of frequency.|Often|Bright|Under|Book
Conjunctions|Complete: Work carefully ___ you may make a mistake.|or|and because|because and|so because
Prepositions|Complete: The train arrived ___ noon.|at|in|on|through
Sentence types|Which sentence is a request?|Please open the window.|The window is open.|Is the window open?|What a window!
Vocabulary|Which word is a synonym of silent?|Quiet|Noisy|Bright|Large
Reading|Lata checks a source before sharing a story. What does this help her do?|Avoid spreading false information|Make the story longer|Hide the source|Read less carefully
""",
6:"""
Reading comprehension|A poster asks students to bring reusable bottles. Its main purpose is to reduce what?|Single-use waste|Reading time|Exercise|Homework
Nouns|Which is an abstract noun?|Courage|Mountain|Bottle|Committee
Pronouns|Choose: The two friends helped ___.|each other|himself|ourselves|itself
Tenses|Choose: I ___ a book when the lights went out.|was reading|am read|readed|will reading
Subject–verb agreement|Choose: Each student ___ a notebook.|has|have|are|were
Adverbs|Which word modifies the verb in 'He answered politely'?|Politely|He|Answered|None
Prepositions|Choose: The cat jumped ___ the box from outside.|into|in|of|beside only
Conjunctions|Choose: ___ it was late, we finished the task.|Although|Because of|During|Unless not
Writing skills|What should an invitation clearly state?|Date, time and place|Only jokes|Only the colour of paper|Unrelated details
Vocabulary|What does 'scarce' mean?|In short supply|Very plentiful|Extremely noisy|Always free
""",
7:"""
Reading inference|A traveller carries an umbrella after seeing dark clouds. What does she expect?|Rain|Snow for certain|An earthquake|A clear sky for certain
Tenses|Choose: By the time we arrived, the bus ___.|had left|has leave|leaving|will leaving
Subject–verb agreement|Choose: Neither of the answers ___ correct.|is|are|have|were being
Modals|Choose: You ___ wear a helmet for safety.|should|might not always|would have|can to
Active and passive voice|Choose the passive form of 'Ria wrote the letter'.|The letter was written by Ria.|The letter wrote Ria.|Ria was wrote the letter.|The letter is writing Ria.
Reported speech|Choose: He said, 'I am tired.'|He said that he was tired.|He said that I am tired.|He said he tired.|He said that he tired is.
Clauses|Which word introduces a reason in 'I left because it was late'?|Because|I|Left|Late
Vocabulary|Which word means 'to look at carefully'?|Examine|Ignore|Forget|Scatter
Writing skills|Which opening best suits a formal letter?|Dear Principal,|Hey buddy!|Yo!|What's up?
Punctuation|Which sentence uses an apostrophe correctly?|The girl's bag is blue.|The girls bag's is blue.|The girl's bag's is blue.|The girls' is bag blue.
""",
8:"""
Reading comprehension|A report gives facts from two reliable sources. What strengthens the report?|Evidence|Rumour|Exaggeration|Guesswork
Tenses|Choose: This time tomorrow, we ___ to Jaipur.|will be travelling|travel yesterday|are travelled|has travelled
Modals|Choose: You ___ enter without permission; it is prohibited.|must not|might|could|would
Subject–verb agreement|Choose: The quality of these apples ___ good.|is|are|were|have
Active and passive voice|Choose the passive form of 'They clean the room'.|The room is cleaned by them.|The room cleaned them.|They are cleaned the room.|The room is cleaning them.
Reported speech|Change 'She said, "I can swim."'|She said that she could swim.|She said that I can swim.|She said she can swam.|She says she could swam.
Clauses|Which part is the relative clause in 'The book that I borrowed is useful'?|That I borrowed|The book|Is useful|Book that
Conjunctions|Choose: ___ you practise, you will improve.|If|Unless not|Although of|Because of
Vocabulary|What does 'reluctant' mean?|Unwilling|Eager|Certain|Careless
Writing skills|What belongs in a summary?|The main ideas in fewer words|Every original sentence|Unrelated opinions|Only the title
""",
9:"""
Determiners|Choose: There isn't ___ milk left.|much|many|a few|several
Tenses|Choose: She ___ here since 2022.|has lived|lives yesterday|is live|have lived
Modals|Which modal expresses obligation in 'You ___ submit the form today'?|must|might|could|would sometimes
Subject–verb concord|Choose: One of the players ___ injured.|is|are|have|were
Reported speech|Change: He said, 'I will return tomorrow.'|He said that he would return the next day.|He said that he will return yesterday.|He said I would returned tomorrow.|He says that he return next day.
Conditional clauses|Choose: If it rains, we ___ indoors.|will stay|would stayed|had stayed|will stayed
Relative clauses|Choose: The person ___ called is my teacher.|who|which|where|when
Noun clauses|Which part is a noun clause in 'I know what you mean'?|What you mean|I know|You mean what|Know what
Reading inference|A writer cites measured rainfall instead of a guess. What is the writer using?|Evidence|A metaphor|A rumour|A slogan
Writing skills|A formal complaint should describe what?|The problem and the requested action|Only personal insults|Unrelated events|Only decorative language
""",
10:"""
Determiners|Choose: ___ of the two roads leads to the station; both do.|Either|Neither|Every|Much
Tenses|Choose: By next month, they ___ the project.|will have completed|will completed|have completing|had complete
Modals|Choose: You ___ have informed us earlier; that was the right thing to do.|should|can to|will to|must to
Subject–verb concord|Choose: The news ___ encouraging.|is|are|have|were
Reported statements|Change: She said, 'I have finished.'|She said that she had finished.|She said that I have finished.|She said that she has finish.|She says she finished had.
Reported questions|Change: He asked, 'Where do you live?'|He asked where I lived.|He asked where did I live.|He asked where do I live?|He asked that where I lives.
Reported commands|Change: The teacher said, 'Please sit down.'|The teacher requested us to sit down.|The teacher asked that please sit down.|The teacher said we sitting down.|The teacher said to sat down.
Reading analysis|A passage presents both benefits and drawbacks of a proposal. Its approach is what?|Balanced|One-sided|Purely fictional|Unrelated
Vocabulary in context|In 'a practical solution', practical most nearly means what?|Useful and workable|Impossible|Decorative|Temporary in every case
Writing skills|An analytical paragraph based on a chart should focus on what?|Key patterns and comparisons in the data|Invented numbers|Unrelated anecdotes|Only personal feelings
"""
}
for g,text in ENGLISH.items():rows(g,'english',text)
WORLD={
1:"""
Our senses|Which sense helps us notice the sound of a bell?|Hearing|Taste|Smell|Touch
Our body|Which body part helps us bend our arm?|Elbow|Ear|Nose|Hair
Healthy habits|When should we wash our hands?|Before eating|Only once a week|Never|Only after sleeping
Food|Which food is a fruit?|Papaya|Rice|Bread|Salt
Family and friends|What is a kind way to help a classmate?|Share when appropriate|Hide their bag|Push them|Laugh at mistakes
Plants|Which part of a plant is usually green?|Leaf|Root|Seed coat|Soil
Animals|Which animal has feathers?|Hen|Cat|Dog|Cow
Water|Which action saves water?|Close a running tap|Leave a tap open|Spill drinking water|Ignore a leaking tap
Shelter|A home protects us from what?|Rain and heat|Reading|Kindness|Learning
Travel|Which vehicle moves on water?|Boat|Bus|Train|Bicycle
Safety|What should we do before crossing a road?|Cross with a trusted adult at a safe crossing|Run without looking|Play on the road|Follow any stranger
Clean surroundings|Where should a banana peel go?|In the appropriate waste bin|On a footpath|Into a pond|Under a desk
""",
2:"""
Food|Which food group includes beans and lentils?|Pulses|Fruits|Oils|Sweets
Water|Which source is a natural water body?|River|Cup|Bucket|Bottle
Plants|What do roots usually take in from soil?|Water|Plastic|Sunlight directly|Smoke
Animals|Which animal lays eggs?|Duck|Cow|Goat|Dog
Homes|A house raised on stilts can help in areas with what?|Flooding|No people|No trees|No sunlight
Clothes|Cotton clothes are often comfortable in which weather?|Hot weather|Heavy snow only|Freezing weather only|All weather equally
Community helpers|Who delivers letters?|Postal worker|Farmer|Pilot|Carpenter
Transport|Which vehicle travels on tracks?|Train|Car|Boat|Bicycle
Directions|The Sun appears to rise in which direction?|East|West|North|South
Time and seasons|What commonly falls from clouds during rain?|Water drops|Sand|Plastic|Smoke
Safety|What should you do if you find an unknown medicine?|Tell a trusted adult|Taste it|Share it|Hide it in food
Healthy habits|What helps keep teeth clean?|Brushing regularly|Eating only sweets|Never rinsing|Using a dirty cloth
""",
3:"""
Family and community|Why do families share household tasks?|To help each other|To create more waste|To avoid talking|To stop learning
Plants around us|Which plant part carries seeds in many flowering plants?|Fruit|Root|Stem only|Leaf only
Animals around us|What helps a fish breathe in water?|Gills|Fur|Wings|A beak
Food and health|A varied meal helps us get what?|Different nutrients|Only sugar|Only water|No energy
Water use|Which action reduces water waste?|Repair a leaking tap|Leave taps open|Overfill buckets|Throw water away
Shelter|Why do roofs slope in many rainy places?|To let rainwater run off|To store smoke|To stop all sunlight|To make walls invisible
Travel and maps|What does a map show?|Places and their positions|Only songs|Only tastes|Only time
Work and materials|Which worker makes wooden furniture?|Carpenter|Baker|Pilot|Weaver only
Air and surroundings|What helps reduce smoke on a short trip?|Walking when safe|Burning waste|Leaving engines running|Using more fuel
Waste|Which item can be reused for storage after cleaning?|A glass jar|A used tissue|Rotten food|A dirty bandage
Observation|To compare leaf shapes, what should you do first?|Observe the leaves carefully|Guess with eyes closed|Tear all the leaves|Ignore differences
Safety and inclusion|A friend needs a ramp to enter a building. What helps?|An accessible ramp|More stairs only|Locking the door|Removing handrails
""",
4:"""
Plants|Why do many plants produce seeds?|To grow new plants|To make plastic|To stop all growth|To turn into stones
Animals|Which animal is well adapted to living in a desert?|Camel|Penguin|Dolphin|Polar bear
Food journey|Who grows many of the grains we eat?|Farmers|Pilots|Postal workers|Tailors
Water|What can help collect rainwater for later use?|Rainwater harvesting|Leaving taps open|Throwing waste in rivers|Draining all ponds
Maps and directions|On a map with north at the top, which side is east?|Right|Left|Top|Bottom
Shelter and climate|Thick walls can help keep a home cooler by reducing what?|Heat entering quickly|All air permanently|All sounds everywhere|Gravity
Transport|Why should we follow traffic signals?|To travel safely|To make roads dirty|To block ambulances|To use more fuel
Materials|Which material usually comes from cotton plants?|Cotton cloth|Glass|Steel|Plastic
Community|Why are public parks useful?|They provide shared spaces|They belong only to one family|They stop all rain|They replace all schools
Health|Why should drinking water be clean?|To reduce the risk of illness|To change its colour|To add dust|To remove all taste
Conservation|What helps protect local birds?|Keep their habitat clean|Destroy all nests|Throw plastic in ponds|Cut every tree
Data and observation|You record rainfall each day. What can the record help compare?|Rainfall across days|People's shoe sizes|Book colours|Bird names only
""",
5:"""
Animal senses|Why can a strong sense of smell help an animal?|To find food or notice danger|To read books|To make rain|To stop hearing
Seeds and plants|Why do some seeds have wings or light fibres?|To spread by wind|To walk|To make stones|To stop growing
Food preservation|Why do we dry some foods before storing them?|To reduce moisture|To add germs|To make them wetter|To add soil
Water conservation|Which practice can recharge groundwater?|Allowing rainwater to soak into the ground|Covering all soil with concrete|Wasting tap water|Dumping chemicals
Adaptation|Why do desert plants often have reduced leaves or spines?|To reduce water loss|To produce snow|To take in more plastic|To stop all photosynthesis
Resources|Why should we use fuel carefully?|Many fuels take a very long time to form|All fuels are unlimited|Fuel has no uses|Fuel is always free
Maps|What does a map's scale help us estimate?|Actual distances|The weather next year|Everyone's height|The colour of a place
Livelihoods|Why might a farmer depend on rainfall?|Crops need water|Rain makes tools disappear|Plants need no soil|Rain replaces all labour
Heritage|Why should historical places be protected?|They help us understand our past|They have no value|They stop all development|They replace schools
Healthy communities|Why are shared clean-water facilities important?|They support public health|They increase litter|They stop all farming|They remove all air
Environment|What can happen when waste blocks a drain?|Water may collect and flood|Rain stops forever|Roads become wider|All water becomes clean
Science observation|To compare how seeds grow, what should be recorded?|Changes over time under known conditions|Only the pot colour|Only someone's guess|Nothing
"""
}
for g,text in WORLD.items():rows(g,'evs',text)
SCIENCE={
6:"""
Scientific inquiry|Why should an experiment be repeated?|To check whether results are reliable|To make up data|To avoid observation|To guarantee a chosen answer
Living world|Which is a living organism?|A growing seedling|A stone|A plastic bottle|A glass
Diversity|Why do we classify living things?|To understand similarities and differences|To make them identical|To stop their growth|To remove names
Food and nutrients|Which nutrient mainly helps build and repair the body?|Protein|Water only|Salt only|Fibre only
Magnets|Which material is strongly attracted by a magnet?|Iron|Wood|Glass|Rubber
Measurement|Which instrument measures temperature?|Thermometer|Ruler|Balance|Stopwatch
Motion|A bus moving along a straight road mainly shows what motion?|Linear motion|Only circular motion|No motion|Only oscillation
Materials|Which material is transparent?|Clear glass|Wood|Cardboard|Brick
Water states|Water changing from liquid to vapour is called what?|Evaporation|Freezing|Melting|Condensation
Separation|How can sand be separated from water?|Filtration|Adding sugar|Melting sand|Using a magnet
Living plants|Which part of a plant usually absorbs water from soil?|Roots|Flowers|Fruit|Petals
Natural resources|Which is a renewable energy source?|Sunlight|Coal|Petroleum|Natural gas
The night sky|Which object produces its own light?|A star|The Moon|Earth|A comet reflecting sunlight
""",
7:"""
Scientific inquiry|A fair comparison should usually change how many test variables at a time?|One|Every variable|None ever|All measurements
Acids and bases|What does an acid do to blue litmus?|Turns it red|Turns it green|Turns it white|Makes it magnetic
Electricity|For a bulb to glow, its circuit must be what?|Closed|Broken|Open|Without an energy source
Metals and non-metals|Which is usually a good conductor of electricity?|Copper|Rubber|Plastic|Dry wood
Physical changes|Which is mainly a physical change?|Melting ice|Burning paper|Rusting iron|Cooking an egg
Chemical changes|Which change forms a new substance?|Rusting iron|Cutting paper|Melting wax|Breaking glass
Adolescence|What is a sensible response to normal body changes while growing up?|Seek reliable guidance from a trusted adult|Believe every rumour|Stop all exercise|Avoid hygiene
Heat transfer|How does heat mainly travel along a metal spoon?|Conduction|Only evaporation|Only freezing|Only reflection
Measurement of time|A clock measures what?|Time|Mass|Length|Temperature
Respiration|Why do living cells respire?|To release energy from food|To make plastic|To stop all growth|To remove all water
Plant nutrition|Green plants make food using sunlight through what process?|Photosynthesis|Rusting|Freezing|Filtration
Earth and space|Which planet is our home?|Earth|Mars|Jupiter|Venus
Light|Light reflected by a smooth mirror helps form what?|An image|Electric current|A new element|Sound
""",
8:"""
Microorganisms|Which tool helps us see many microorganisms?|Microscope|Telescope|Ruler|Balance
Health|Why is vaccination useful?|It helps the immune system prepare against specific diseases|It replaces all food|It makes every illness impossible|It removes the need for clean water
Electricity and magnetism|An electric current in a coil can produce what?|A magnetic field|Only a shadow|Only ice|A vacuum
Heating effect|Which appliance uses the heating effect of electric current?|Electric iron|A wooden spoon|A paper kite|A glass jar
Forces|Friction acts in which direction relative to slipping motion?|Opposite to it|Always upward|Always east|Always along it
Pressure|For the same force, smaller contact area gives what pressure?|Greater pressure|Less pressure|Zero pressure always|The same pressure always
Particles of matter|Why can a gas fill a container?|Its particles move and spread out|Its particles never move|It has a fixed shape|It is always solid
Elements and compounds|Which is a compound?|Water|Iron|Copper|Oxygen
Solutions|In salt water, water is usually the what?|Solvent|Solute|Sediment|Residue only
Light and lenses|Which lens can bring parallel light rays together?|Convex lens|Concave lens|A flat opaque board|A wooden block
Earth and time|Day and night mainly result from what?|Earth's rotation|The Moon making light|The Sun switching off|Earth stopping
Ecosystems|Which organisms make their own food using sunlight?|Green plants|All animals|All fungi|All rocks
Environment|Which action can reduce air pollution?|Using cleaner transport and fuels|Burning more waste|Removing every tree|Leaving engines idling
""",
9:"""
Cells|Which structure controls many activities of a cell?|Nucleus|Cell wall only|Soil|Air
Cells|Which organelle is a major site of energy release during respiration?|Mitochondrion|Cell wall|Chloroplast only|Vacuole only
Tissues|Which plant tissue transports water?|Xylem|Phloem|Epidermis only|Muscle
Matter|At ordinary room conditions, which state has no fixed shape but a fixed volume?|Liquid|Solid|Gas|All three
Atoms and molecules|What is the chemical symbol for sodium?|Na|S|N|So
Atomic structure|Which subatomic particle has a negative charge?|Electron|Proton|Neutron|Nucleus
Motion|Speed is distance divided by what?|Time|Mass|Force|Area
Force and motion|Newton's second law relates force to mass and what?|Acceleration|Volume|Temperature|Colour
Work and energy|What is the SI unit of work?|Joule|Newton|Pascal|Metre
Sound|Sound in air travels mainly as what?|Longitudinal waves|Only transverse waves|Light rays|Electric current
Gravitation|What pulls objects towards Earth?|Gravity|Friction alone|Magnetism for all objects|Sound
Living systems|Osmosis is the movement of water through what?|A selectively permeable membrane|Any solid wall|A vacuum without a membrane|Only metal
Earth systems|Which gas contributes to the greenhouse effect?|Carbon dioxide|Helium only|Neon only|Argon only
""",
10:"""
Chemical reactions|A balanced equation has equal numbers of what on both sides?|Atoms of each element|Molecules of every substance|Products only|Reactants only
Acids bases and salts|A solution with pH 2 is what?|Acidic|Neutral|Basic|Always pure water
Metals and non-metals|Which metal reacts vigorously with cold water?|Sodium|Gold|Silver|Copper
Carbon compounds|Why can carbon form many long chains?|It bonds with other carbon atoms|It has no electrons|It cannot form bonds|It is always ionic
Life processes|Where does most absorption of digested food occur in humans?|Small intestine|Mouth|Food pipe|Large intestine
Control and coordination|Which cells carry nerve impulses?|Neurons|Red blood cells|Bone cells only|Skin cells only
Reproduction|Fertilisation is the fusion of what?|Male and female gametes|Two roots|Two leaves|Two organs of any kind
Heredity|Genes are located on what?|Chromosomes|Ribosomes only|Cell walls|Soil
Light|A concave mirror can converge parallel rays at its what?|Focus|Pole only|Edge|Back surface
Human eye|Which part of the eye controls how much light enters?|Iris|Retina|Optic nerve|Cornea alone
Electricity|If V = 12 V and R = 4 Ω, what is the current?|3 A|48 A|8 A|16 A
Electricity|Resistors of 2 Ω and 3 Ω are in series. Their total resistance is what?|5 Ω|1 Ω|6 Ω|1.2 Ω
Magnetic effects|The field around a straight current-carrying wire forms what?|Concentric circles|Only straight parallel lines|Only triangles|No field
Our environment|Which organisms break down dead organic matter?|Decomposers|Only large mammals|Only herbivores|All non-living objects
"""
}
for g,text in SCIENCE.items():rows(g,'science',text)
SOCIAL={
6:"""
Maps and globes|What does a globe represent?|Earth|Only one city|Only the Sun|Only a street
Directions|What is opposite to north?|South|East|West|Northeast
Oceans and continents|Which is an ocean?|Indian Ocean|Asia|Africa|Europe
Landforms|Which landform is usually high with steep slopes?|Mountain|Plain|Beach|Delta only
Historical sources|Which can provide evidence about the past?|An inscription|An unverified rumour|An invented date|A guess alone
Early settlements|Why did many early settlements develop near rivers?|Water supported farming and daily life|Rivers removed all work|Rivers stopped all travel|Rivers made every place cold
Civilisation|Which feature is associated with many Harappan cities?|Planned streets and drainage|Modern cars|Electric traffic lights|Airports
Cultural diversity|Why should we respect different languages?|They are part of people's identities and cultures|Only one language has value|They prevent all cooperation|They are all identical
Family and community|A community works together to clean a park. This is an example of what?|Cooperation|Pollution|Isolation|Competition only
Local government|Which body helps govern a village locally?|Gram Panchayat|An airline|A private shop|A sports club
Work and livelihoods|Growing crops is an example of which activity?|Farming|Manufacturing phones|Banking|Air travel
Economic activities|Making furniture from wood is mainly what kind of activity?|Manufacturing|Farming|Fishing|Weather forecasting
""",
7:"""
Earth and landforms|Slow breaking down of rocks in place is called what?|Weathering|Migration|Voting|Trade
Atmosphere|Which gas makes up the largest part of Earth's air?|Nitrogen|Oxygen|Carbon dioxide|Hydrogen
Water and climate|What moves water from the surface into the air as vapour?|Evaporation|Freezing|Sedimentation|Erosion alone
Maps|A map key or legend explains what?|Symbols on the map|Only the map's price|Everyone's name|The age of the paper
History and evidence|Why should historians compare different sources?|To check and understand evidence|To remove every disagreement|To choose only rumours|To avoid reading
Trade|Why did people trade goods between regions?|Different regions produced different goods|Every place produced exactly the same goods|No one needed anything|Trade stops all travel
Cultural exchange|Trade routes can help spread what besides goods?|Ideas and customs|Only storms|Only rocks|Nothing else
Equality|Equal treatment under the law means what?|The law should apply fairly to everyone|Only wealthy people obey laws|Some people have no rights|Rules never apply
Government|Why are public services important?|They meet shared needs|They serve only one household|They replace all communities|They stop learning
Markets|A person selling goods is a what?|Seller|Buyer only|Passenger|Voter only
Community resources|Which is an example of a shared public facility?|Public library|One person's private diary|A personal toothbrush|A locked private cupboard
Environment|Planting suitable local trees can help reduce what?|Soil erosion|All rainfall|Earth's rotation|All seasons
""",
8:"""
Natural resources|Why should resources be used sustainably?|So present use does not unnecessarily harm future needs|So everything is used up quickly|So waste increases|So conservation stops
Agriculture|Which factor directly affects crop growth?|Availability of water|The colour of a bus|A shop's sign|A phone's ringtone
Industry|Turning cotton into cloth is an example of what?|Manufacturing|Mining only|Fishing|Banking
Population|Population density compares population with what?|Area|Only rainfall|Only temperature|Only age
Historical evidence|Which is a primary source for studying a past event?|A contemporary letter|A made-up story|A modern rumour|An unsupported guess
Colonialism|Colonial rule means what?|A foreign power controls a territory|All people always rule equally|Every village is independent|There are no taxes
Social reform|A movement opposing discrimination seeks what?|More equal treatment|Less dignity|More exclusion|Fewer rights
Constitution|What is a constitution?|A framework of fundamental rules for governance|Only a shopping list|Only a map|A private diary
Secularism|A secular state should treat religions how?|Without unfair discrimination|By giving all rights to one religion only|By banning every belief|By removing all equality
Judiciary|What is a main role of courts?|Resolve disputes according to law|Sell crops|Predict weather|Print all newspapers
Public facilities|Clean drinking-water systems support what?|Public health|Only decoration|Only private trade|Only sports rankings
Social justice|Why may extra support be needed for disadvantaged groups?|To improve fair access to opportunities|To remove their rights|To prevent education|To increase exclusion
""",
9:"""
Understanding social science|Which field studies production and exchange?|Economics|Botany|Geometry|Astronomy
Earth's surface|Earthquakes often occur where what moves?|Tectonic plates|Only clouds|Only tree roots|Only ocean fish
Atmosphere and climate|Weather describes conditions over what timescale?|A short period|Only thousands of years|Only a century|All time without change
Climate|Climate describes typical weather over what?|Many years|One minute|One thunderstorm|One afternoon only
Early humans|The development of farming helped people do what?|Form more settled communities|Stop needing food|Stop using tools|Live only on ships
Civilisations|Why were rivers important for many early civilisations?|They supported water supply and farming|They stopped all trade|They removed every flood|They replaced houses
Historical sources|Archaeology mainly studies what?|Material remains of the past|Only future events|Only weather reports|Only fictional stories
State and society|An empire generally governs what?|Many territories under a central authority|Only one classroom|Only one household|No territory
Government and constitution|Why limit government powers through rules?|To protect rights and prevent misuse|To remove accountability|To stop all services|To remove all courts
Citizenship|Citizens participating in decisions can strengthen what?|Democratic accountability|Secret rule without scrutiny|All forms of discrimination|The absence of debate
Economy|What is an opportunity cost?|The value of the next best alternative given up|All money in the world|Only a product's colour|A cost that never exists
Markets|If supply is unchanged and demand rises, prices often do what?|Rise|Always fall to zero|Never change under any conditions|Become negative in every market
Public goods|Which is commonly a public good provided for shared use?|Street lighting|One person's lunch|A private toothbrush|A personal notebook
Environment and economy|Pollution harming neighbours is an example of what?|A negative external effect|A guaranteed benefit to everyone|No economic effect|Only private savings
""",
10:"""
Nationalism in Europe|The idea of a nation-state links political authority with what?|A shared national identity|Only one private company|Only one household|Only a sports score
Nationalism in India|The Salt March challenged a colonial tax on what?|Salt|Tea|Cotton|Wheat
Global connections|Trade between distant societies creates what?|Economic connections|Complete isolation|No exchange of ideas|Identical climates
Print culture|Printing helped spread ideas mainly by doing what?|Making texts available to more people|Preventing all reading|Removing all languages|Ending all debate
Resources and development|Sustainable development considers whose needs?|Present and future generations|Only one person today|Only past rulers|Only large firms
Agriculture|Growing more than one crop on the same land at different times is called what?|Multiple cropping|Mining|Urbanisation|Deforestation
Water resources|Rainwater harvesting helps with what?|Conserving and collecting water|Creating plastic|Removing all rainfall|Increasing fuel use
Manufacturing|Which activity belongs mainly to manufacturing?|Making steel from raw materials|Growing rice|Fishing|Collecting wild fruit
Power sharing|Sharing power can help reduce what?|Conflict and misuse of power|All public participation|All accountability|Every discussion
Federalism|Federalism divides powers mainly between what?|Different levels of government|Only two private shops|Only one ruler and a friend|Only sports clubs
Democracy|A key feature of democratic government is what?|Accountability to people|No elections or public voice|Unlimited unreviewable power|No rights
Political parties|Political parties usually seek to do what?|Contest elections and influence government policy|Replace all courts|Stop every public service|End all citizenship
Development|Per capita income is calculated by dividing total income by what?|Population|Area|Rainfall|Number of rivers
Economic sectors|Farming belongs mainly to which sector?|Primary|Secondary|Tertiary|Banking
Money and credit|Collateral is an asset used as what?|Security for a loan|A free gift from every bank|A tax on rainfall|An election symbol
Globalisation|Globalisation increases what?|Connections between economies|Complete isolation of economies|The end of all trade|Identical incomes everywhere
"""
}
for g,text in SOCIAL.items():rows(g,'social',text)
# Specific source documents supplement the official catalogue reference.
# Extra questions preserve topic replacement when sessions use ten questions.
for g in range(-1,11):
    if g<=0:
        rows(g,'english',"""
Letters|Which letter starts the word fish?|F|B|S
Sounds|Which word begins like dog?|Duck|Sun|Hat
Rhyming|Which word rhymes with top?|Hop|Cat|Pen
Vocabulary|What do we use to brush our teeth?|Toothbrush|Spoon|Shoe
Listening|A grown-up says 'clap your hands'. What should you do?|Clap|Sleep|Sit silently
Opposites|What is the opposite of hot?|Cold|Big|Fast
Speaking|What can you say when you ask for help politely?|Please help me.|Go away.|Stop it.
Stories|Nina puts a flower in a vase. What goes into the vase?|A flower|A shoe|A book
""")
    elif g<=2:
        rows(g,'english',"""
Naming words|Which word names a person?|Teacher|Run|Blue|Soft
Action words|Complete: Fish ___ in water.|swim|fly|read|write
Reading|Amit keeps his lunch in a red box. What colour is his lunch box?|Red|Blue|Green|Yellow
Opposites|What is the opposite of day?|Night|Morning|Light|Today
Plurals|One cup, two ___.|cups|cup|cuppes|cupes
Vocabulary|Which word names a vehicle?|Bus|Apple|Tree|Shoe
Sentences|Choose the complete sentence about a dog.|The dog runs.|Runs the.|Dog the.|The runs.
Rhyming|Which word rhymes with light?|Night|Late|Log|Leaf
""")
    elif g<=5:
        rows(g,'english',"""
Reading|A notice says the library closes at four. When must readers leave?|By four o'clock|After midnight|At six o'clock|Any time they wish
Tenses|Complete: Last week, we ___ a museum.|visited|visit|visiting|visits
Pronouns|Choose: Arun and I finished the work. ___ were pleased.|We|He|They|It
Adjectives|Which word describes the noun in 'a bright lamp'?|Bright|Lamp|A|None
Adverbs|In 'The turtle moved slowly', which word tells how it moved?|Slowly|Turtle|The|Moved
Prepositions|Complete: We sat ___ the shade of a tree.|in|onto|through|out
Vocabulary|Which word has the opposite meaning to careful?|Careless|Cautious|Thoughtful|Alert
Conjunctions|Complete: I wanted to play, ___ I had to finish my work.|but|because|if|while because
""")
    else:
        rows(g,'english',"""
Reading inference|A student revises a draft after feedback. What does this suggest?|A willingness to improve|A refusal to learn|A wish to avoid all work|A dislike of all writing
Tenses|Complete: She ___ in this town since 2020.|has lived|live|will lived|living
Subject–verb agreement|Complete: The quality of these apples ___ excellent.|is|are|have|were being
Modals|Which sentence expresses a possibility?|It may rain tomorrow.|It must rain yesterday.|It can to rain.|It raining tomorrow.
Clauses|In 'We stayed inside because it rained', which clause gives the reason?|Because it rained|We stayed inside|Stayed inside because|We because
Writing skills|Which detail is essential in a notice about a school event?|The event date and venue|An unrelated joke|A private password|A random shopping list
Vocabulary|Which word is closest in meaning to 'reluctant'?|Unwilling|Eager|Certain|Joyful
Active and passive voice|Choose the passive form of 'They cleaned the room'.|The room was cleaned by them.|The room cleaned them.|They were clean the room.|The room has cleaning them.
""")

DOCS={
(3,'maths'):'https://ncert.nic.in/textbook/pdf/cemm1ps.pdf',
(4,'maths'):'https://ncert.nic.in/textbook/pdf/demm1ps.pdf',
(6,'maths'):'https://ncert.nic.in/textbook/pdf/fegp1ps.pdf',
(7,'maths'):'https://ncert.nic.in/textbook/pdf/gegp1ps.pdf',
(8,'maths'):'https://www.ncert.nic.in/pdf/Bridge_Programme/Grade8/Bridge_Programme-Mathematics-Grade_8.pdf',
(7,'science'):'https://ncert.nic.in/textbook/pdf/gecu1ps.pdf',
(8,'science'):'https://ncert.nic.in/textbook/pdf/hecu1ps.pdf',
(9,'maths'):'https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/Maths_SecP1IX_2026-27.pdf',
(10,'maths'):'https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/Maths_SecP1X_2026-27.pdf',
(9,'science'):'https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/ScienceSt_SecP1_2026-27.pdf',
(10,'science'):'https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/Science_SecP1_2026-27.pdf',
(9,'social'):'https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/SocialScience_SecP1IX_2026-27.pdf',
(10,'social'):'https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/SocialScience_SecP1X_2026-27.pdf',
(9,'english'):'https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/English_LL_SecP1IX_2026-27.pdf',
(10,'english'):'https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/English_LL_SecP1_2026-27.pdf',
}
for gs,subjects in BANK.items():
    g=int(gs)
    for item in subjects:
        qs=item['questions'];assert len(qs)>=10
        assert len({x[0] for x in qs})==len(qs),(g,item['id'],'duplicate')
        topics=list(dict.fromkeys(x[3] for x in qs))
        item['topic']=' · '.join(topics[:3])+' & more'
        if (g,item['id']) in DOCS:item['sources'].append(DOCS[g,item['id']])
        if g<=0:
            item['name']={'maths':'Numbers & Shapes','english':'Language & Sounds','evs':'Me & My World'}[item['id']]
(ROOT/'backend/data/curriculum.json').write_text(json.dumps(BANK,ensure_ascii=False,indent=2)+'\n')
total=sum(len(s['questions']) for ss in BANK.values() for s in ss)
print(f'{total} original questions across {len(BANK)} levels.')
for g,ss in BANK.items():print(g,', '.join(f"{s['id']}: {len(s['questions'])}" for s in ss))

import runpy
expand_class2 = runpy.run_path(str(Path(__file__).resolve().parent / "expand-class2.py"))["expand"]
expand_class2()
