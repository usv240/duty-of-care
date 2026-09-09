## Inspiration

A major studio can hire a consultant to check how a script depicts suicide. An independent screenwriter cannot.

The guidance those consultants use is public and specific — the World Health Organization's resource for filmmakers, Samaritans' guidance for drama, the US National Recommendations, Australia's Mindframe, Canada's Mindset. Most writers have never seen a page of it. It sits in long PDFs, split across countries, written for someone else.

The research under it is real. A 2020 meta-analysis in the *BMJ* found that reporting a suicide method was associated with a **30% increase** in deaths by that method (doi:10.1136/bmj.m575). A 2021 meta-analysis of *fictional* portrayals found depictions of suicide death associated with an **18% increase** in suicides (*EClinicalMedicine*, doi:10.1016/j.eclinm.2021.100922). And it runs both ways: an analysis of American feature films from 1950–2002 found recovery-focused stories predict **lower** suicide rates (*Crisis* 2026, doi:10.1027/0227-5910/a001012).

It is also contested. The most-cited case, *13 Reasons Why*, has two independent teams finding increases in youth suicides — and a reanalysis in *PLOS ONE* arguing the effect cannot be shown from aggregate rates (doi:10.1371/journal.pone.0227545). We put that disagreement **inside the product** rather than hiding it.

So the idea was simple: bring the guidance, and the evidence under it, next to the scene — while the writer is still writing.

## What it does

Paste a scene, upload a draft (Fountain, plain text, Markdown, or Final Draft `.fdx`), or load one of six demo screenplays we wrote. Then three layers run, and you watch each one work.

**1. Code finds the candidate.** Plain regular expressions — not a model — parse the screenplay and underline the exact phrase that fired: method detail, framing the act as a solution, no help-seeking nearby, romanticising language, repetition, or no support resource anywhere in the draft. A writer can read exactly why something was underlined.

**2. Google Agent Search retrieves the guidance, and the research under it.** A 36-clause corpus built from the real WHO, Samaritans, National Action Alliance, Mindframe and Mindset documents across five jurisdictions — each clause carrying its publisher, version and source link. A second data store holds 14 peer-reviewed research records, retrieved beside every note, including the ones that disagree. **If no applicable clause comes back, there is no note.** The model can never be the reason a note exists.

**3. A Gemini agent explains it, and offers one alternative.** A Google ADK agent, bound to that single scene, explains why each clause may apply and drafts one rewrite that keeps the dramatic intent. It has to run our hard safety filter as a tool before it is allowed to answer, the API runs that filter again on the result, and Google Cloud Model Armor screens the final text.

Then **the writer decides**: accept, dismiss, or request expert review. Dismissing keeps all the reasoning on screen. There is no overall score, nothing is ever blocked, and crisis resources sit on every page before any interaction.

**The same review is a public API.** Mint a key and run a live request from the browser. Every response carries a `meta.gate` field naming which checks passed and failed, and a `disclaimer` field an integrator cannot strip — so this can live inside the writing and production tools creators already use without losing its honesty. That is the difference between one website and guidance that reaches the writers who never visit it.

Everything is one click from the nav: a demo library with downloads, an evidence page listing all 14 studies, the API page, and a stack page where every service reports whether it actually answered your review.

## How we built it

**Google Cloud — the agent and its judges.** Gemini 2.5 Flash on Vertex AI through the Agent Development Kit. The identical agent is deployed to **Vertex AI Agent Engine** and called over HTTP, with in-process ADK as a recorded fallback — when it falls back, the note says so on screen. **Google Agent Search** (Discovery Engine) runs the two data stores and is the only source of any clause or study. **Model Armor** screens the agent's answer. The **Vertex AI Gen AI Evaluation Service** then judges every note independently. Cloud Run hosts the backend, Secret Manager holds the key-signing secret, and a Cloud Monitoring uptime check watches the public endpoint.

**Replit — the product.** The writer-facing app is built with **Replit Agent** and runs on **Replit Autoscale** at https://duty-of-care.replit.app. Agent wrote the fixed-origin backend proxy that lets the Replit surface call Cloud Run for a small allowlist of routes and nothing else. **Replit Auth**, **Database** and **Secrets** carry identity, saved decisions and configuration — and the Replit surface never holds a Google credential.

## Challenges we ran into

**The hard part was restraint, not capability.** A model that will happily explain guidance will just as happily invent it. Every architectural decision was about taking power away from it: a gate in code, a filter the agent must pass as a tool and then pass again at the API, a managed screen after both, and an independent judge after that. The rule that shaped everything — *no applicable citation, no flag* — meant accepting that the tool stays silent far more often than a detector would.

**Being honest about the evidence was harder than citing it.** It would have been easy to quote only the studies that support the premise. Carrying the *PLOS ONE* reanalysis, which argues against it, in the same panel as the studies it disputes, is the version we could actually defend.

**Our first independent judge scored everything zero** — because we handed it only the clauses as context, and asked it to grade the proposed rewrite as if it were a factual claim. Fixing that meant giving the judge the agent's real inputs and judging only the explanation. The lesson stuck: an evaluation you have not debugged is not evidence.

## Accomplishments that we're proud of

- **An independent Google judge scored our own agent.** The Vertex AI Gen AI Evaluation Service rated every note our six demo drafts produce: **9 of 9 explanations fully grounded** in the retrieved clauses, the scene and the triggers (mean 1.0), and **9 of 9 rated safe**. The scores ship in the repo and are served from the API — including a plain statement of what the judge does *not* measure.
- **Across 54 live cases, 279 clauses were retrieved and zero fell outside the chosen jurisdiction.** Every candidate scene received applicable guidance, and no note was withheld by our own filter or by Model Armor.
- **The stack page refuses to call a service working until a real call proves it.** Cards read live, active, applied or configured based on what answered *your* review. Two of them currently read `configured` rather than active, because we set them up and never got a live result back. We left that visible instead of quietly removing the cards.
- **A blinded ten-fragment pack is prepared for an independent qualified reviewer.** Those labels are not ours to write, so the tool reports that review as **pending** everywhere, rather than implying a clinical validation we do not have.

## What we learned

The useful job for AI here is **contextual explanation after retrieval and deterministic checks** — not deciding whether art is acceptable. Once we stopped asking the model to judge and started asking it to explain something already retrieved, the safety problem turned into an architecture problem, and architecture can be verified in a way that good intentions cannot.

We also learned that stating uncertainty is a product feature. Showing contested research, naming the checks that failed, and marking expert review as pending made the tool more credible, not less.

## What's next for Duty of Care

An independent reviewer's labels on the blinded pack. More jurisdictions and more studies in both corpora — the architecture takes new guidance as data, not as code. Depiction guidance beyond suicide, wherever published standards already exist: self-harm, eating disorders, addiction. And a saved decision history, so a writer can see what changed when the guidance itself changes.
