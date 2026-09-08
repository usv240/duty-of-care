## Inspiration

Studios hire a consultant to check how a script depicts suicide, self-harm, or addiction. Everyone else guesses.

The guidance exists and is specific: the World Health Organization's resource for filmmakers, Samaritans' guidance for drama and film, the US National Recommendations for Depicting Suicide, Australia's Mindframe resource for stage and screen, Canada's Mindset recommendations. Most independent and student screenwriters have never seen a page of it. Samaritans runs a human script-advice service; it can never reach every short film.

The research behind that guidance is real, and it is contested in places, so we built the disagreement in rather than hiding it. A 2020 meta-analysis in the *BMJ* found that reporting a suicide method was associated with a 30% increase in deaths by that method (Niederkrotenthaler et al., doi:10.1136/bmj.m575). A 2021 meta-analysis of *fictional* portrayals found depictions of suicide death associated with an 18% increase in suicides (*EClinicalMedicine*, doi:10.1016/j.eclinm.2021.100922). On the protective side, the Papageno effect, first described in the *British Journal of Psychiatry* in 2010, shows coverage of people coming through a crisis associated with fewer deaths, and a 2026 analysis of American feature films found recovery-focused narratives predict lower suicide rates (*Crisis*, doi:10.1027/0227-5910/a001012). And the most-cited case, 13 Reasons Why, has two independent teams finding increases in youth suicides (Bridge et al., *JAACAP*; Niederkrotenthaler et al., *JAMA Psychiatry*) and a reanalysis in *PLOS ONE* arguing the effect cannot be attributed from aggregate rates. Fourteen such records, each verified against Europe PMC, are part of the product.

## What it does

A writer pastes a scene, uploads a draft (Fountain, plain text, Markdown, or Final Draft `.fdx`, converted in the browser), or loads one of six self-authored demo drafts. Then three layers run, and the page shows each one working:

1. **Code finds candidates.** Deterministic rules parse the screenplay into scenes and underline the exact phrase that fired: method detail, framing the act as a solution, no help-seeking nearby, romanticising language, repetition, and no support resource anywhere in the document.
2. **Google Agent Search retrieves the guidance, and the research behind it.** A 36-clause corpus built from the real WHO, Samaritans, National Action Alliance, Mindframe, and Mindset documents across five jurisdictions, each clause with publisher, version, and source link. A second data store holds the fourteen research records, retrieved beside every note so the writer sees *why* the guidance says what it says, including the studies that disagree. If no applicable clause is retrieved, no note is raised.
3. **A Gemini agent explains, and drafts one alternative.** A Google ADK agent, bound to that one scene, explains why each clause may apply and offers one rewrite that keeps the drama. It must run our hard safety filter as a tool before answering, the API runs the filter again, and Google Cloud Model Armor screens the final text. Afterwards, the Vertex AI Gen AI Evaluation Service judges every note for groundedness against the retrieved clauses and for safety, and we publish the scores.

The writer then **accepts, dismisses, or asks for expert review**. Dismissal keeps the reasoning visible. There is no overall score, nothing is blocked, and crisis resources are on every page before any interaction.

The same review is a **public API**: one-click keys, a `meta.gate` field naming which thresholds passed and failed, a streaming variant, Markdown reports, and a `disclaimer` field an integrator cannot strip. Everything a judge can click is on the site: a demo library with downloads, an evidence page, a developer page that mints a key and runs the API live, and a stack page where every Google Cloud and Replit service shows whether it answered just now.

## How we built it

**Google Cloud (the agent and its judges):** Gemini on Vertex AI through the Agent Development Kit, with explicit safety settings. The identical agent is deployed to Vertex AI Agent Engine and called over HTTP, with in-process ADK as the recorded fallback. Google Agent Search (Discovery Engine) runs two data stores, guidance and evidence, and is the only source of either. Model Armor screens the agent's answer. The Vertex AI Gen AI Evaluation Service scores groundedness and safety independently. Cloud Run hosts the backend, Artifact Registry holds its images, Secret Manager holds the key-signing secret, Cloud Build runs the checks, Cloud Logging keeps content-free traces, and a Cloud Monitoring uptime check watches the public endpoint.

**Replit (the product):** the writer-facing app is built with Replit Agent and deployed on Replit Autoscale at https://duty-of-care.replit.app. Agent built the fixed-origin backend proxy that lets the Replit surface call Cloud Run for exactly the allowlisted routes, with 2 MB request, 10 MB response, and 120 s limits, redirect rejection, typed errors on oversized or timed-out streams, and nine tests, plus the platform tests for Replit Database and App Storage selection. Replit Secrets hold only the backend URL and a signing secret; the Replit surface never holds a Google credential. Replit Auth, Database, and App Storage adapters are in the code with labelled fallbacks; we list them as active only where the deployment confirms it.

**Plain code where code belongs:** the candidate rules and the safety filter are regular expressions, not a model, so a writer can read exactly why something was underlined.

## What we measured

- The deterministic layer scores precision 1.0 and recall 1.0 on 48 self-authored engineering cases, computed live by the same endpoint that serves the number.
- The full live pipeline on 54 cases: every candidate scene received applicable clauses, zero clauses fell outside the chosen jurisdiction, every generated note kept its structure, none was withheld by the filter or by Model Armor, median latency under ten seconds. Under load, a share of notes fell back from Agent Engine to the in-process agent; each such note says so.
- An independent Google judge, the Vertex AI Gen AI Evaluation Service, scored every note the six presets produce: 9 of 9 explanations fully grounded in the retrieved clauses, the scene, and the triggers (mean 1.0), and 9 of 9 answers rated safe (mean 1.0). Published in `docs/EVAL-GROUNDEDNESS.json` and served from the API.
- A blinded ten-fragment pack for a qualified independent reviewer is prepared. Its labels are not ours to write, so the tool reports that review as pending.

## What we deliberately did not build

No overall score: a single rating invites optimising a script toward a number. No blocking path. No "your scene is safe": the wording is rejected in code. No model-recalled guidance or research: no citation, no flag, and no study is quoted that was not verified. No screenplay storage by default: exports and saved decisions are explicit and opt-in.

## Challenges

The hard part was restraint. The model must never be the reason a note exists, never rewrite a scene into something more specific than the writer wrote, and never certify. That meant a gate in code, a filter the agent has to pass as a tool and then pass again, a managed screen after both, an independent judge after that, and the discipline to show contested evidence as contested.

## What we learned

The useful role for AI here is contextual explanation after retrieval and deterministic applicability checks, not deciding whether art is acceptable. Preserving the writer's agency and stating uncertainty honestly are product features, not disclaimers.

## What's next

An independent reviewer's labels on the blinded pack, more jurisdictions and studies in the two corpora, and a saved-decision history on Replit so a writer sees what changed when the guidance corpus changes.

## Links

- Live app: https://duty-of-care.replit.app
- Google agent backend: https://duty-of-care-agent-backend-109051079423.us-central1.run.app
- Source (Apache-2.0): https://github.com/usv240/duty-of-care
