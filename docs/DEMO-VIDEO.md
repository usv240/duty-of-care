# Demo video script — Duty of Care

**Target 2:45. Hard stop 3:00** (only the first three minutes are judged).
Record on **https://duty-of-care.replit.app** — the rules require footage of the
project functioning on the platform it was built for, and that is the Replit
deployment.

Every beat below is aimed at one judging criterion, so a judge scoring on a
rubric sees each one demonstrated rather than claimed.

---

## Before you press record

1. **Warm the app.** Open the site, load the guidance case, press Review once,
   and let it finish. The first review after idle is slower. Then reload.
2. **Clean browser window.** No bookmarks bar, no extensions, no other tabs
   visible. The rules forbid third-party logos and trademarks on screen, and a
   bookmarks bar is the usual way they sneak in.
3. **Light theme, Plain mode.** Both are the default. Do not touch the toggles.
4. **1920x1080, browser zoom 100%.** Full-screen the window (F11) so only the
   product is visible.
5. **Two tabs only**, in this order:
   - Tab 1: `https://duty-of-care.replit.app/` (guidance case loads by default)
   - Tab 2: `https://duty-of-care.replit.app/developers`
6. **Record system audio off, microphone on.** No music. English.

---

## The script

Times are cumulative. **Bold text is what you say, out loud, as written.**

### 0:00–0:16 — The problem (criterion: Potential Impact)

**POINT AT:** the headline on the home page, then the sponsor ribbon underneath it.

**SAY:** **"Studios hire a consultant to check how a script depicts suicide. Everyone else guesses. The World Health Organization, Samaritans, and national bodies publish exactly what to do. Most independent screenwriters have never seen a page of it."**

---

### 0:16–0:52 — Run it, and narrate the layers while it computes (criterion: Technological Implementation)

**NAVIGATE:** scroll to the workbench. The draft *The Last Message* is already in
the box. **Press "Review against published guidance".**

The progress list ticks for about fifteen seconds. Do not wait in silence — the
list is your visual aid. Point at each line as it appears.

**SAY:** **"This is a three-scene draft I wrote. Watch the layers work."**

**POINT AT:** the first progress line as it appears.
**SAY:** **"First, plain code parses the scenes and underlines the exact phrase that worries it. Nothing has decided anything yet."**

**POINT AT:** the "Agent Search, retrieving clauses" line.
**SAY:** **"Second, Google Agent Search retrieves the guidance clauses that actually apply to those phrases, in this jurisdiction, plus the research behind them."**

**POINT AT:** the "Agent Engine, explaining" line.
**SAY:** **"Third, a Gemini agent on Vertex AI Agent Engine explains only what was retrieved. If nothing applicable comes back, no note is raised. That rule is the whole design."**

---

### 0:52–1:32 — Anatomy of one note (criteria: Technological Implementation + Potential Impact)

**NAVIGATE:** the results appear. Scroll so one full note is on screen next to
the screenplay page.

**POINT AT:** a red underline in the screenplay, then the note beside it.
**SAY:** **"Here is one note. The underline is what code noticed: an exact amount."**

**POINT AT:** the clause card with the publisher and the "Open source" link.
**SAY:** **"Beside it, the clause it actually cites. National Action Alliance, twenty nineteen, with a link to the document."**

**POINT AT:** the research panel under the clauses (headed "Why the guidance says this").
**SAY:** **"Under that, the research. A BMJ meta-analysis: reporting a method was associated with thirty percent more deaths by that method. We include the studies that disagree, too."**

**POINT AT:** the teal alternative box and its chips (filter passed, self-checks, Model Armor clear).
**SAY:** **"Then one alternative that keeps the drama. The agent had to pass our own safety filter as a tool before it could answer, the API ran that filter again, and Google Model Armor screened the result."**

---

### 1:32–1:47 — The writer decides (criterion: Quality of the Idea)

Do this **while the first result is still on screen**, so you never wait for a
second review.

**NAVIGATE:** in any note, click the reason box and type **the ambiguity is the
point**. Press **Dismiss note**.

**POINT AT:** the note's state line, which now reads "dismissed, reasoning stays
visible", then the clauses and research still sitting below it.
**SAY:** **"The writer decides. I dismiss this and give my reason. The clauses and the research stay on screen. Nothing is blocked, and there is no overall score, on purpose."**

---

### 1:47–2:07 — The contrast (criterion: Quality of the Idea) — the moment that wins

**NAVIGATE:** in the preset dropdown on the right, choose **"Through This
Minute"**, then press **Review against published guidance**. It returns in under
a second.

**SAY:** **"Same subject, written the way the guidance describes. A friend stays, help is named, the resource card is on screen."**

**POINT AT:** the "No guidance flag raised" card.
**SAY:** **"Zero notes, instantly. This is not a keyword filter. And it still refuses to say the scene is safe, because a pre-review cannot certify anything."**

---

### 2:07–2:24 — It is also an API (criteria: Technological Implementation + Design)

**NAVIGATE:** Tab 2, the Developers page. Press **"Get an API key now"**, then
**"Run POST /v1/review"**.

**SAY:** **"The same review is a public API. One click for a key. Run it live."**

**POINT AT:** `meta.gate` in the JSON response.
**SAY:** **"Every response names the gates that passed and failed, so anything integrating this can see why a note exists."**

---

### 2:24–2:42 — Every service, earned (criterion: Technological Implementation)

**NAVIGATE:** click **Stack** in the top navigation. Scroll slowly through the
Google group, then the Replit group.

**POINT AT:** the Google cards.
**SAY:** **"Every service reports whether it actually answered. Gemini, Agent Engine, Agent Search, Model Armor, and the evaluation service that scored these notes."**

**POINT AT:** the Replit cards, ending on App Storage.
**SAY:** **"On Replit: Agent built this surface, Autoscale serves it, Auth and Database are live. App Storage says configured, because a real write failed. We do not paint anything green."**

---

### 2:42–2:52 — Close (criterion: Potential Impact)

**NAVIGATE:** scroll to the bottom so the fixed crisis footer is unmistakable.

**POINT AT:** the footer.
**SAY:** **"Crisis resources on every page, before anything else. Published guidance beside the scene, and the writer keeps the pen."**

Stop recording.

---

## If you run over three minutes

Cut in this order, and only in this order:

1. The API beat (2:07–2:24). It is on the site for judges to click themselves.
2. The second half of the stack beat, keeping the Google cards.
3. Shorten the opening to: **"Studios hire a consultant to check how a script depicts suicide. Everyone else guesses. The guidance exists. Most writers have never seen it."**

Never cut the contrast beat at 1:47. It is the strongest twenty seconds in the video.

## If something is slow while recording

Keep talking; the progress list gives you something true to describe. If a
review takes longer than about twenty-five seconds, stop, reload the page, and
start that take again — a warm instance answers in ten to fifteen.

## Upload checklist

- [ ] Under 3:00
- [ ] Recorded on `duty-of-care.replit.app`, not the Cloud Run URL
- [ ] No bookmarks bar, no extensions, no third-party logos anywhere on screen
- [ ] English audio
- [ ] No music, no third-party footage
- [ ] Uploaded to YouTube as **Public** (not Unlisted)
- [ ] Title: `Duty of Care — Agentic Cinema Hackathon`
- [ ] Link pasted into the Devpost "Video demo link" field

## What each beat is scored on

| Time | Beat | Criterion it answers |
|---|---|---|
| 0:00 | The access gap, named audience | Potential Impact |
| 0:16 | Three layers, narrated as they run | Technological Implementation |
| 0:52 | Trigger, clause, research, filtered alternative | Technological Implementation, Potential Impact |
| 1:32 | Dismissal keeps the reasoning; no score | Quality of the Idea |
| 1:47 | Conforming draft returns zero notes | Quality of the Idea |
| 2:07 | Public API with gate metadata | Technological Implementation, Design |
| 2:24 | Every sponsor service with an earned status | Technological Implementation |
| 2:42 | Crisis resources, writer keeps the pen | Potential Impact |
