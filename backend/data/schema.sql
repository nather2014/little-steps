CREATE TABLE IF NOT EXISTS users (
 id text PRIMARY KEY, email text NOT NULL UNIQUE, password_hash text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS profiles (
 id text PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 display_name text NOT NULL CHECK(length(display_name) BETWEEN 1 AND 60),
 role text NOT NULL CHECK(role IN ('student','parent')),
 grade integer CHECK(grade BETWEEN 1 AND 10),
 CHECK((role='student' AND grade IS NOT NULL) OR (role='parent' AND grade IS NULL))
);
CREATE TABLE IF NOT EXISTS auth_sessions (
 token_hash text PRIMARY KEY, user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON auth_sessions(expires_at);
CREATE TABLE IF NOT EXISTS parent_children (
 parent_id text REFERENCES profiles(id) ON DELETE CASCADE,
 child_id text REFERENCES profiles(id) ON DELETE CASCADE,
 PRIMARY KEY(parent_id,child_id), CHECK(parent_id<>child_id)
);
CREATE TABLE IF NOT EXISTS link_codes (
 code_hash text PRIMARY KEY, child_id text NOT NULL UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,
 expires_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS exams (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 grade integer NOT NULL, subject text NOT NULL, title text NOT NULL, topic text NOT NULL,
 week_start date NOT NULL, questions jsonb NOT NULL,
 UNIQUE(grade,subject,week_start)
);
CREATE TABLE IF NOT EXISTS exam_sessions (
 id text PRIMARY KEY, student_id text NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
 exam_id bigint NOT NULL REFERENCES exams(id), mode text NOT NULL CHECK(mode IN ('weekly','practice')),
 started_at timestamptz NOT NULL DEFAULT now(), submitted boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS attempts (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 session_id text NOT NULL UNIQUE REFERENCES exam_sessions(id),
 student_id text NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
 exam_id bigint NOT NULL REFERENCES exams(id), grade integer NOT NULL, subject text NOT NULL,
 week_start date NOT NULL, mode text NOT NULL CHECK(mode IN ('weekly','practice')),
 correct integer NOT NULL, total integer NOT NULL, seconds integer NOT NULL,
 submitted_at timestamptz NOT NULL DEFAULT now(), review jsonb NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_weekly_submission ON attempts(student_id,exam_id) WHERE mode='weekly';
CREATE INDEX IF NOT EXISTS attempts_history ON attempts(student_id,submitted_at);
CREATE INDEX IF NOT EXISTS attempts_ranking ON attempts(grade,week_start,mode);
CREATE TABLE IF NOT EXISTS schema_versions(version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
INSERT INTO schema_versions(version) VALUES(1) ON CONFLICT DO NOTHING;

-- Guests have no contact details or password; existing accounts remain unchanged.
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_guest boolean NOT NULL DEFAULT false;
ALTER TABLE users ALTER COLUMN email DROP NOT NULL;
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
INSERT INTO schema_versions(version) VALUES(2) ON CONFLICT DO NOTHING;

ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_grade_check;
ALTER TABLE profiles ADD CONSTRAINT profiles_grade_check CHECK(grade BETWEEN -1 AND 10);
ALTER TABLE exam_sessions ADD COLUMN IF NOT EXISTS questions jsonb;
ALTER TABLE exam_sessions ADD COLUMN IF NOT EXISTS not_studied jsonb NOT NULL DEFAULT '[]'::jsonb;
-- Freeze existing questions before updating current curriculum pools.
UPDATE exam_sessions s SET questions=e.questions FROM exams e WHERE s.exam_id=e.id AND s.questions IS NULL;
ALTER TABLE attempts ADD COLUMN IF NOT EXISTS not_studied jsonb NOT NULL DEFAULT '[]'::jsonb;
INSERT INTO schema_versions(version) VALUES(3) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS xp_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 student_id text NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
 event_key text NOT NULL, kind text NOT NULL CHECK(kind IN ('quiz','daily','weekly')),
 title text NOT NULL, amount integer NOT NULL CHECK(amount>0),
 attempt_id bigint REFERENCES attempts(id) ON DELETE CASCADE,
 earned_at timestamptz NOT NULL DEFAULT now(), UNIQUE(student_id,event_key)
);
CREATE INDEX IF NOT EXISTS xp_student_time ON xp_events(student_id,earned_at);
ALTER TABLE attempts ADD COLUMN IF NOT EXISTS xp_earned integer NOT NULL DEFAULT 0;
DO $$ BEGIN
IF NOT EXISTS (SELECT 1 FROM schema_versions WHERE version=4) THEN
INSERT INTO xp_events(student_id,event_key,kind,title,amount,attempt_id,earned_at)
SELECT student_id,'attempt:'||id,'quiz',
 CASE WHEN mode='weekly' THEN 'Weekly exam' ELSE 'Practice quiz' END,
 CASE WHEN mode='weekly' THEN 100 ELSE 40 END + correct*10,id,submitted_at
FROM (
 SELECT a.*,row_number() OVER(PARTITION BY student_id,mode,(submitted_at AT TIME ZONE 'Asia/Kolkata')::date ORDER BY submitted_at,id) AS daily_order
 FROM attempts a
) credited WHERE mode='weekly' OR daily_order<=3
ON CONFLICT(student_id,event_key) DO NOTHING;

INSERT INTO xp_events(student_id,event_key,kind,title,amount,attempt_id,earned_at)
SELECT student_id,'daily:'||day_key||':'||m.id,'daily',m.title,m.xp,last_attempt,last_time
FROM (
 SELECT x.student_id,(x.earned_at AT TIME ZONE 'Asia/Kolkata')::date AS day_key,
 count(*) quizzes,sum((SELECT count(*) FROM jsonb_array_elements(a.review) r WHERE r->>'selected'<>'Not answered')) questions,sum(a.correct) correct,max(a.id) last_attempt,max(x.earned_at) last_time
 FROM xp_events x JOIN attempts a ON a.id=x.attempt_id WHERE x.kind='quiz'
 GROUP BY x.student_id,(x.earned_at AT TIME ZONE 'Asia/Kolkata')::date
) d CROSS JOIN LATERAL (
 VALUES ('first_quiz','Daily: Take a little step',50,quizzes>=1),
 ('answer_ten','Daily: Answer 10 questions',75,questions>=10),
 ('correct_five','Daily: Find 5 correct answers',100,correct>=5)
) m(id,title,xp,complete) WHERE m.complete
ON CONFLICT(student_id,event_key) DO NOTHING;

INSERT INTO xp_events(student_id,event_key,kind,title,amount,attempt_id,earned_at)
SELECT student_id,'weekly:'||week_key||':'||m.id,'weekly',m.title,m.xp,last_attempt,last_time
FROM (
 SELECT x.student_id,date_trunc('week',x.earned_at AT TIME ZONE 'Asia/Kolkata')::date AS week_key,
 count(DISTINCT (x.earned_at AT TIME ZONE 'Asia/Kolkata')::date) days,
 count(DISTINCT CASE WHEN a.mode='weekly' THEN a.exam_id END) weekly_exams,
 sum((SELECT count(*) FROM jsonb_array_elements(a.review) r WHERE r->>'selected'<>'Not answered')) questions,max(a.id) last_attempt,max(x.earned_at) last_time
 FROM xp_events x JOIN attempts a ON a.id=x.attempt_id WHERE x.kind='quiz'
 GROUP BY x.student_id,date_trunc('week',x.earned_at AT TIME ZONE 'Asia/Kolkata')::date
) w CROSS JOIN LATERAL (
 VALUES ('weekly_three','Weekly: Complete 3 weekly exams',200,weekly_exams>=3),
 ('learn_three_days','Weekly: Learn on 3 days',150,days>=3),
 ('answer_thirty','Weekly: Answer 30 questions',250,questions>=30)
) m(id,title,xp,complete) WHERE m.complete
ON CONFLICT(student_id,event_key) DO NOTHING;
UPDATE attempts a SET xp_earned=x.amount FROM
 (SELECT attempt_id,sum(amount)::int AS amount FROM xp_events GROUP BY attempt_id) x
WHERE a.id=x.attempt_id AND a.xp_earned<>x.amount;
INSERT INTO schema_versions(version) VALUES(4) ON CONFLICT DO NOTHING;
END IF; END $$;

CREATE TABLE IF NOT EXISTS rank_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 student_id text NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
 attempt_id bigint NOT NULL UNIQUE REFERENCES attempts(id) ON DELETE CASCADE,
 delta integer NOT NULL, before_points integer NOT NULL CHECK(before_points>=0),
 after_points integer NOT NULL CHECK(after_points>=0),
 awarded_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS rank_student_events ON rank_events(student_id,id DESC);
ALTER TABLE attempts ADD COLUMN IF NOT EXISTS rr_delta integer NOT NULL DEFAULT 0;
INSERT INTO schema_versions(version) VALUES(5) ON CONFLICT DO NOTHING;

-- Existing sessions keep their original two-hour expiry; new sessions receive a timer.
ALTER TABLE exam_sessions ADD COLUMN IF NOT EXISTS deadline_at timestamptz;
ALTER TABLE exam_sessions ADD COLUMN IF NOT EXISTS saved_answers jsonb NOT NULL DEFAULT '[]'::jsonb;
INSERT INTO schema_versions(version) VALUES(6) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS learning_skills (
 student_id text NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
 subject text NOT NULL, topic text NOT NULL,
 correct integer NOT NULL DEFAULT 0, total integer NOT NULL DEFAULT 0,
 last_accuracy integer NOT NULL DEFAULT 0, stage integer NOT NULL DEFAULT 0 CHECK(stage BETWEEN 0 AND 4),
 due_at timestamptz NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(student_id,subject,topic)
);
ALTER TABLE learning_skills ADD COLUMN IF NOT EXISTS needs_help boolean NOT NULL DEFAULT false;
CREATE TABLE IF NOT EXISTS mistake_notes (
 attempt_id bigint NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
 question_index integer NOT NULL, reason text NOT NULL CHECK(reason IN ('concept','calculation','reading','unsure','other')),
 note text NOT NULL DEFAULT '', updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(attempt_id,question_index)
);
-- Backfill the latest topic performance once, without rewriting later review schedules.
DO $$ BEGIN
IF NOT EXISTS(SELECT 1 FROM schema_versions WHERE version=7) THEN
INSERT INTO learning_skills(student_id,subject,topic,correct,total,last_accuracy,due_at)
SELECT student_id,subject,topic,sum(correct)::int,sum(total)::int,
 (array_agg(round(100.0*correct/total)::int ORDER BY submitted_at DESC,id DESC))[1],now()
FROM (
 SELECT a.student_id,a.subject,a.id,a.submitted_at,q->>'topic' topic,
 count(*) FILTER(WHERE (q->>'correct')::boolean) correct,count(*) total
 FROM attempts a CROSS JOIN LATERAL jsonb_array_elements(a.review) q
 GROUP BY a.student_id,a.subject,a.id,a.submitted_at,q->>'topic'
) results WHERE topic IS NOT NULL
GROUP BY student_id,subject,topic
ON CONFLICT DO NOTHING;
INSERT INTO schema_versions(version) VALUES(7) ON CONFLICT DO NOTHING;
END IF; END $$;

ALTER TABLE exam_sessions DROP CONSTRAINT IF EXISTS exam_sessions_mode_check;
ALTER TABLE exam_sessions ADD CONSTRAINT exam_sessions_mode_check CHECK(mode IN ('weekly','practice','ranked','time_trial'));
ALTER TABLE attempts DROP CONSTRAINT IF EXISTS attempts_mode_check;
ALTER TABLE attempts ADD CONSTRAINT attempts_mode_check CHECK(mode IN ('weekly','practice','ranked','time_trial'));
INSERT INTO schema_versions(version) VALUES(8) ON CONFLICT DO NOTHING;

ALTER TABLE exam_sessions DROP CONSTRAINT IF EXISTS exam_sessions_mode_check;
ALTER TABLE exam_sessions ADD CONSTRAINT exam_sessions_mode_check CHECK(mode IN ('weekly','practice','ranked','time_trial'));
ALTER TABLE attempts DROP CONSTRAINT IF EXISTS attempts_mode_check;
ALTER TABLE attempts ADD CONSTRAINT attempts_mode_check CHECK(mode IN ('weekly','practice','ranked','time_trial'));
CREATE TABLE IF NOT EXISTS time_trials (
 session_id text PRIMARY KEY REFERENCES exam_sessions(id) ON DELETE CASCADE,
 duration_seconds integer NOT NULL CHECK(duration_seconds IN (60,180,300)),
 answers jsonb NOT NULL DEFAULT '[]'::jsonb,
 points integer NOT NULL DEFAULT 0 CHECK(points>=0),
 streak integer NOT NULL DEFAULT 0 CHECK(streak>=0),
 best_streak integer NOT NULL DEFAULT 0 CHECK(best_streak>=0),
 finished_at timestamptz,
 attempt_id bigint REFERENCES attempts(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS time_trial_finished ON time_trials(finished_at);
INSERT INTO schema_versions(version) VALUES(9) ON CONFLICT DO NOTHING;

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin boolean NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_at timestamptz;
CREATE INDEX IF NOT EXISTS users_activity ON users(last_active_at);
CREATE INDEX IF NOT EXISTS active_exam_deadline ON exam_sessions(deadline_at) WHERE NOT submitted;
INSERT INTO schema_versions(version) VALUES(10) ON CONFLICT DO NOTHING;
