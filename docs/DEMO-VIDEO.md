# Demo video script — Duty of Care (2:45 target, hard stop 3:00)

Record on the **Replit URL** in a signed-out browser window at 1920x1080, light theme, Plain mode.
Screen capture plus your voice; no music, no logos, no third-party footage. Everything on
screen is this app, this repository, and Google Cloud or Replit consoles. English audio.

Before recording: open five tabs in this order and leave them ready.

1. `[REPLIT_URL]/` with the guidance case loaded (it loads by default)
2. `[REPLIT_URL]/presets`
3. `[REPLIT_URL]/developers`
4. `[REPLIT_URL]/stack`
5. https://github.com/usv240/duty-of-care

Say the words in the right column roughly as written; short sentences read better than
polished ones.

| Time | On screen | Say |
|---|---|---|
| 0:00–0:15 | Tab 1, hero. Point at the headline. | "Studios hire a consultant to check how a script depicts suicide. Everyone else guesses. There is published guidance from WHO, Samaritans, and national bodies, and most independent writers have never seen it. Duty of Care puts it beside the scene." |
| 0:15–0:35 | Scroll to the workbench. The three-scene draft *The Last Message* is in the box. Press **Review against published guidance**. Let the progress list tick. | "This is a self-authored draft. Watch the layers: code parses the scenes and finds candidates, Google Agent Search retrieves clauses, and a Gemini agent on Google's Agent Development Kit explains them, running on Vertex AI Agent Engine." |
| 0:35–1:10 | Results. Hover a red underline, then the note beside it. Click **Open source** on one clause. Show the "Guidance by jurisdiction" line. | "Every underline is the exact phrase code noticed. Every note shows the publisher, the clause, the version, and a link to the document. US and global guidance are shown side by side, never merged. Below is one alternative that keeps the drama; the agent had to pass our safety filter as a tool before answering, the API ran it again, and Google Cloud Model Armor screened the result." |
| 1:10–1:25 | Type a short reason in the note's reason box, press **Dismiss note**. Show the decision record. | "The writer decides. Dismiss it, and the reasoning stays visible. Nothing is blocked. There is no score, on purpose." |
| 1:25–1:45 | Preset dropdown → **Through This Minute**. Review. Show zero notes and the "not certification" card. | "Same subject, written the way the guidance describes: a friend stays, help is named, the resource card is on screen. Zero notes. And the tool still refuses to call it safe. That is the whole idea in twenty seconds: not a keyword filter, not a censor." |
| 1:45–2:05 | Tab 3, developers. Press **Get an API key now**, then **Run POST /v1/review**. Scroll to `meta.gate` in the response. | "The same review is a public API. One click for a key, run it live, and every response names which gates passed and failed. The disclaimer is a required field an integrator cannot strip." |
| 2:05–2:25 | Tab 4, stack. Scroll slowly through Google Cloud and Replit groups. | "Every service is listed with an earned status: Gemini, Agent Engine, Agent Search, Model Armor, Cloud Run, Secret Manager. Replit Agent built this product surface, and it runs on Replit Autoscale `[plus Auth, Database, App Storage, Scheduled re-check if verified]`." |
| 2:25–2:40 | Tab 2, presets briefly, then Tab 5, GitHub README with the measured results. | "Six downloadable demo drafts. Fifty-four cases run through the live pipeline, results published from the same endpoint. An independent reviewer pack is prepared and reported as pending; we do not label it ourselves." |
| 2:40–2:50 | Back to Tab 1, scroll to the crisis footer. Show the Replit URL in the address bar. | "Crisis resources stay on every page. Duty of Care: published guidance beside the scene, and the writer keeps the pen." |

## Checklist before upload

- [ ] Under 3:00. If over, cut the presets tab beat first.
- [ ] Recorded on the `replit.app` URL, not Cloud Run.
- [ ] No claim of clinical safety, certification, or expert validation. "Pending" is the word for the reviewer pack.
- [ ] Only Replit services that Agent actually enabled are named.
- [ ] Uploaded to YouTube as **Public**, English audio; title "Duty of Care — Agentic Cinema Hackathon demo".
- [ ] Link pasted into the Devpost **Video demo link** field.
