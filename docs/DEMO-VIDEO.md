# Demo video script — Duty of Care

**Target 2:45. Hard stop 3:00** (only the first three minutes are judged).
Record on **https://duty-of-care.replit.app** — the rules require footage of the
project functioning on the platform it was built for, and that is the Replit
deployment.

**The one idea a judge should remember afterwards:**

> It doesn't detect the topic. It detects when published guidance actually
> applies, and the writer still decides.

Everything below serves that sentence. The four judging criteria are equally
weighted, so each beat is aimed at one of them and labelled.

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
6. **Microphone on, system audio off.** No music. English.

Read at a normal pace, roughly 150 words a minute. The whole script is about
410 spoken words, which lands at 2:45 with breathing room.

---

## The script

Times are cumulative. **Bold text is what you say, out loud, as written.**

### 0:00–0:18 — Audience, problem, solution (criterion: Potential Impact)

**POINT AT:** the headline on the home page.

**SAY:** **"Major studios can hire specialists to review how a script depicts suicide. Independent screenwriters usually can't. The guidance already exists, but it's scattered across long documents and different countries. Duty of Care brings it beside the scene, while the writer is still writing."**

---

### 0:18–0:50 — Run it, and narrate the three layers while it computes (criterion: Technological Implementation)

**NAVIGATE:** scroll to the workbench. The draft *The Last Message* is already in
the box. **Press "Review against published guidance".**

The progress list ticks for about fifteen seconds. Point at each line as it
appears; it is your visual aid, so you are never waiting in silence.

**SAY:** **"This is a three-scene draft I wrote. Watch three layers work."**

**POINT AT:** the first progress line.
**SAY:** **"First, code finds the exact phrase worth checking. Nothing has judged anything yet."**

**POINT AT:** the "Agent Search" line.
**SAY:** **"Second, Agent Search retrieves only the published guidance that applies, for this jurisdiction, plus the research behind it."**

**POINT AT:** the "Agent Engine, explaining" line.
**SAY:** **"Third, Gemini, running on Vertex AI Agent Engine, explains that guidance in context. And critically: no applicable source means no note."**

---

### 0:50–1:30 — Anatomy of one note (criteria: Technological Implementation + Potential Impact)

**Use the second note, headed `INT. MARA'S APARTMENT - LATER`.** The first note
on the page is the whole-document one; it has no underline to point at, so skip
past it.

**Map of that note, top to bottom.** Everything you point at is in this order,
so you can find each item without hunting:

| Order | What you see on screen |
|---|---|
| 1 | Heading `INT. MARA'S APARTMENT - LATER`, and on its right `Open · writer decides` |
| 2 | Four coloured chips: Method specificity, Framed as solution, No help-seeking, Repetition |
| 3 | Four grey rule lines, each ending `Matched: "…"` |
| 4 | Heading **`Retrieved by Google Agent Search · 6 clauses`**, then six clause rows, each with a square publisher badge (NAA or WHO), the clause text in italics, a jurisdiction tag, the version, and `Open source ↗` |
| 5 | Heading **`Why the guidance says this · research retrieved by Google Agent Search`**, then three studies, each with a `doi:` link, its finding, and a line starting `For the writer:` |
| 6 | The link `All records and the studies that disagree →` |
| 7 | A dashed box beginning `Guidance by jurisdiction: US (5) · GLOBAL (1)` |
| 8 | The teal box headed `GOOGLE ADK REVIEWER · SUGGESTED ALTERNATIVE, PRESERVES DRAMATIC INTENT`, with five chips underneath it |
| 9 | Three buttons: Accept note, Dismiss note, Request expert review, and a reason field |

On the **left** of all this sits the screenplay page with the coloured
underlines.

---

**POINT AT:** the words `exact amount` in the screenplay on the left. They carry
a red underline and a small triangle.
**SAY:** **"Here is one note. The underline is what code noticed: an exact amount."**

**POINT AT:** item 4, the first clause row, sweeping across to `Open source ↗`.
**SAY:** **"Beside it, the clause it cites. National Action Alliance, twenty nineteen, with a link to the document."**

**POINT AT:** item 5, the third study, `EClinicalMedicine 2021`, and its finding.
**SAY:** **"Under that, the research behind the guidance. A meta-analysis of fictional portrayals found an eighteen percent increase in suicides."**

**POINT AT:** item 6, the link reading `All records and the studies that disagree →`.
**SAY:** **"And we include the studies that disagree."**

**POINT AT:** item 8, the teal box, then run across its five chips.
**SAY:** **"Then one alternative that keeps the drama. The agent had to pass our own safety filter before it could answer, and Model Armor screened the result."**

The chips read `gemini-2.5-flash`, `filter: passed`, `self-checks: 1`,
`Agent Engine`, `Model Armor: clear`. Do not read them out; the camera does that
work for you.

---

### 1:30–1:45 — The writer decides (criterion: Quality of the Idea)

Do this **while the first result is still on screen**, so the take needs only
one long review.

**NAVIGATE:** in the same note, click the reason field at the bottom, type
**the ambiguity is the point**, and press **Dismiss note**.

**POINT AT:** the state line now reading "dismissed, reasoning stays visible",
then the clauses and research still sitting below it.
**SAY:** **"The writer decides. I dismiss this and give my reason. The clauses and the research stay on screen. Nothing is blocked, and there is no overall score, on purpose."**

---

### 1:45–2:07 — The contrast, and the sentence that lands the whole demo (criterion: Quality of the Idea)

**SAY (before you click, as the transition):** **"Now watch what happens when I change the writing, not the topic."**

**NAVIGATE:** in the preset dropdown, choose **"Through This Minute"**, then
press **Review against published guidance**. It returns in under a second.

**SAY:** **"Same sensitive subject. But here a friend stays, help is named, and resources appear. Zero notes."**

**POINT AT:** the "No guidance flag raised" card. Slow down for this line and
leave a beat of silence after it.

**SAY:** **"So Duty of Care isn't detecting suicide. It's detecting when published guidance actually applies. And the writer still decides."**

---

### 2:07–2:22 — Where this can live (criteria: Potential Impact + Design)

**NAVIGATE:** Tab 2, the Developers page. Press **"Get an API key now"**, then
**"Run POST /v1/review"**.

**SAY:** **"And because the same review is an API, this doesn't have to live only here. It can sit inside the writing and production tools creators already use."**

**POINT AT:** `meta.gate` in the JSON response.
**SAY:** **"Every response names the checks that passed and failed."**

---

### 2:22–2:36 — Not a mockup (criterion: Technological Implementation)

**NAVIGATE:** click **Stack** in the top navigation. One slow scroll through the
Google group into the Replit group. Do not read the cards aloud.

**SAY:** **"And this isn't a mockup. Every service here reports whether it actually answered this review: Agent Search, Agent Engine, Gemini, Model Armor, and the Replit deployment. One card admits a failure, because we don't paint anything green."**

---

### 2:36–2:45 — Close (criterion: Potential Impact)

**NAVIGATE:** scroll to the bottom so the fixed crisis footer is unmistakable.

**POINT AT:** the footer.
**SAY:** **"Crisis resources on every page, before anything else. Published guidance beside the scene, and the writer keeps the pen."**

Stop recording.

---

## If you run over three minutes

Cut in this order, and only in this order:

1. The last clause of the stack beat: **"One card admits a failure, because we don't paint anything green."** Worth about four seconds.
2. The two research lines in the note anatomy (0:50–1:30). The panel stays on
   screen, so a judge reads it without narration.
3. The `meta.gate` line at 2:07.

**Never cut the contrast beat at 1:45**, and never cut the sentence
*"It's detecting when published guidance actually applies."* That sentence is
the whole demo.

## If something is slow while recording

Keep talking; the progress list gives you something true to describe. If a
review takes longer than about twenty-five seconds, stop, reload, and restart
that take. A warm instance answers in ten to fifteen.

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
| 0:00 | Audience, problem, solution in one breath | Potential Impact |
| 0:18 | Three layers, narrated as they run | Technological Implementation |
| 0:50 | Trigger, clause, research, filtered alternative | Technological Implementation, Potential Impact |
| 1:30 | Dismissal keeps the reasoning; no score | Quality of the Idea |
| 1:45 | Conforming draft returns zero notes, then the hero sentence | Quality of the Idea |
| 2:07 | An API, so it can live in existing tools | Potential Impact, Design |
| 2:22 | Services report whether they actually answered | Technological Implementation |
| 2:36 | Crisis resources, writer keeps the pen | Potential Impact |
