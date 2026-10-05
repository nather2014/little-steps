# Matches, ranks and progress

The student dashboard offers Normal, Ranked, Olympiad Ranked and Time Trials, with rank and RR in the header. Career provides newest-first match history, an oldest-first option, mode filters and clickable match stats/answer review. Learn, Analyze & correct and Missions & XP are absent from student navigation. Parent accounts retain private linked-child progress views. Logout clears the header and account state.

## Ranked and Normal

Ranked tests contain 10 questions with a 15-minute deadline. Original Olympiad-style maths/reasoning challenges contain 10 questions with a 20-minute deadline; these are independent of official organisers and do not cover the complete syllabus. Students can make unlimited ranked attempts. Normal uses practice scoring and does not change RR.

The server saves answers and enforces deadlines. Closing a test leaves its timer running. Reopening an unfinished exam within two hours resumes its questions, answers and deadline. An open test submits at expiry; the server rejects changes after the deadline and scores unanswered questions as incorrect. “Not studied yet” records and replaces a question before scoring its replacement.

Each new ranked result changes RR: 90–100% +30; 75–89% +20; 60–74% +10; 40–59% −10; below 40% −20. Everyone starts at Iron 1 with 50 RR. Divisions take 100 RR. Iron, Bronze, Silver, Gold, Platinum, Diamond, Ascendant and Immortal have three divisions; Radiant starts at 2,400 total points. RR has a zero floor. Retrying a submission returns its original result without duplicate rewards.

## Time Trials

Unlimited rounds offer 60-second Blitz, 3-minute Sprint and 5-minute Marathon. Each correct answer scores 10 points, plus 2 per consecutive correct answer up to 20 points per answer. Wrong or skipped answers reset the streak. Questions repeat only after the subject pool is exhausted. Each answer is saved immediately. Closing leaves the timer running; reopening resumes the round or finalizes it after expiry. An open round submits automatically at expiry. Empty rounds produce no exam attempt or XP. Results show accuracy, correct answers per minute, streaks and personal bests by subject/duration. Time Trials never change RR.

## XP and analytics

Ranked tests earn 100 XP + 10 per correct answer. The first three Normal quizzes each day earn 40 XP + 10 per correct answer. The first three scoring Time Trial rounds each day earn 5 XP per correct answer, with a separate allowance. Allowances reset at midnight in Asia/Kolkata. Later attempts still save results. Daily/weekly missions and new mission bonus XP are retired; API mission lists remain empty for compatibility. Historical XP remains intact. Level calculation and parent progress remain available; the student dashboard shows only rank and RR.

Comparisons use each other learner’s first result on the same exam/mode and require three other learners. Time Trials also match duration. Parents can read only linked children’s data. Leaderboards use each subject’s best percentage in the selected week; retakes cannot inflate scores beyond 100%.

Normal supports targeted weak-skill practice. Subtraction with borrowing has five easier followed by five normal questions and authored worked steps. Other topic sets disclose mixed review when fewer than ten focused questions exist. Wrong answers and uncertainty update skill tracking. Review intervals are 1/3/7/14/30 days; successful due reviews at 80% advance, mistakes reset to one day, and early success leaves the date unchanged. These are app reminders, without outgoing notifications.

## Verification

Go unit tests and vet; scripts/test-rewards.py, scripts/test-learning.py, scripts/test-trials.py; browser checks in scripts/test-learning-browser.cjs, scripts/test-trials-browser.cjs and scripts/test-career-browser.cjs. SQL fixtures and clock changes are local-only. Career filter fixtures stay in the browser and do not write fake scores. Live browser tests record guest IDs for precise cleanup.

## Class 2 expansion

Class 2 contains 939 entries: Maths 314 (including 24 runtime borrowing questions), English 248, The World Around Us 90, Olympiad Maths 164 and Olympiad Reasoning 123. The expansion adds 802 original questions with answer explanations across existing/core topics; it does not claim full textbook coverage. Regenerate either base bank and scripts/expand-class2.py retains the additional Class 2 questions. Other grades remain unchanged.
