# Daily & Weekly Practice Plan

> Consistency beats intensity. **60–90 minutes a day, 5 days a week** gets you further than a 10-hour weekend binge you can't sustain.

## The weekly template (~9 h)

| Day | Block | Duration | What exactly |
|---|---|---|---|
| **Mon** | Learn | 75 min | Read the phase section(s) for the week. Write a 5-line summary in `notes/week-XX.md` in your own words |
| **Tue** | Practice | 75 min | Exercises (SQL/PySpark/Databricks/migration) — commit solutions |
| **Wed** | Practice | 75 min | Exercises + **break something on purpose** and fix it |
| **Thu** | Apply | 75 min | Apply to your project: inspect real (dev) objects, read real code, ask one good question at work |
| **Fri** | Build | 120 min | Mini-project; commit + PR; update [PROGRESS.md](../PROGRESS.md) |
| **Weekend** | Optional | 0–2 h | Catch-up, capstone, or rest (rest is allowed!) |

## The daily micro-habits (at work, ~10–15 min total)

1. **Three-question habit** on every task: *What? Why this way? What could go wrong?*
2. **Error log**: every error goes into `notes/error-log.md` (template in [docs/00](../docs/00-how-to-learn-on-a-real-project.md)).
3. **One SQL a day**: write one query against real dev metadata (`information_schema`, `DESCRIBE DETAIL`, `SHOW GRANTS`, system tables).
4. **One "why"** asked to a senior per day (batch them if they're busy).
5. **End-of-day line**: "Today I learned ___" in your weekly notes.

## A 75-minute practice session structure

```
 0–10  min  Warm-up: redo yesterday's hardest exercise from memory
10–55  min  New exercises (stop at 45 min even if unfinished — note where you stopped)
55–70  min  Break/debug: introduce one failure, fix it, log it
70–75  min  Commit + 2-line note
```

## The monthly review (first weekend of each month, ~1 h)

- Rate yourself against the [skill matrix](../reference/skill-matrix.md). Commit the ratings, so you can see the trend.
- Re-read your error log. Which errors keep recurring? Make a checklist for them.
- Pick 10 random [interview questions](../reference/interview-questions.md) and answer them out loud (record yourself).
- Adjust the next month's plan: which weeks need stretching?

## Spaced repetition (keeps things from fading)

| When | Revisit |
|---|---|
| Week 4 | SQL windows (Week 3) |
| Week 6 | Python packaging & tests (Week 4) |
| Week 8 | Spark plans/UI (Week 5–6) |
| Week 10 | MERGE & SCD2 (Week 7) |
| Week 12 | Migration decision matrix (Week 8) |
| Week 14 | Validation suite (Week 9) |
| Week 16 | Everything via interview questions |

## Signs you're on track
- You can explain this week's topic to a non-expert in 2 minutes.
- Your error log has more "Prevention" entries filled in over time.
- You ask fewer "what" questions at work and more "why" and "what if" questions.
- Reviewers' comments on your PRs move from correctness to style and design.

## Signs you need to slow down
- You're copying code you can't explain → redo the exercise without looking.
- 3+ weeks behind → use the 12-week compression in the roadmap, but **don't skip weeks 7–9**.
- Burned out → take a week off. The roadmap will still be here.
