# Judge path

## Stage-one viability

- Track: Replit.
- The Google Agent Search + ADK backend and the full product surface are live on Cloud Run; the agent also runs on Vertex AI Agent Engine, and Model Armor screens its output.
- Replit eligibility is **not complete**: Replit Agent must materially build part of the final repository and the final product must be deployed on `replit.app` or `replit.dev`. `/stack` reports both as `pending` until the owner records the evidence.
- Follow `replit.md`; do not upload a Google service-account key.

## Four equal judging criteria

| Criterion | Strongest proof | Remaining proof needed |
|---|---|---|
| Technological Implementation | Guidance case returns exact Agent Search clauses per scene and a document-level signpost note; one ADK agent definition runs on Vertex AI Agent Engine and in-process, calls the hard filter as a tool, and the API re-applies it; Model Armor screens the answer; stateless keys signed by Secret Manager; `meta.gate` on every response; a live-pipeline evaluation in `docs/EVAL-LIVE.json` | Genuine Replit Agent commit and deployment evidence |
| Design | Four pages, one shell; sponsor ribbon and crisis footer everywhere; light default, Plain/Technical, no overflow at phone width; presets state their expectation before you run them | Signed-out mobile/desktop QA on the Replit URL |
| Potential Impact | Published guidance becomes accessible during drafting, with downloads and an API so other tools can embed it, without removing writer agency | Qualified independent review of the blinded ten-fragment pack |
| Quality of Idea | No citation means no flag; no score or censor path; decisions kept without keeping scripts; a nightly re-check that says when guidance changed under a saved decision | Preserve the contested-evidence and human-escalation boundary in Replit changes |

## Ninety-second test

1. Open `/`. The guidance case is preloaded. Press Review and watch each layer report progress: parsed, Agent Search retrieving, Agent Engine explaining. Three notes appear, each with the phrase that fired, publisher-attributed clauses grouped by jurisdiction, the research behind them with DOI links (including the studies that disagree), and one alternative with its filter, self-check, runtime, and Model Armor chips.
2. Dismiss a note and type a reason: the reasoning stays visible in the decision record.
3. Load "Through This Minute" (responsible depiction): zero candidates, zero notes, and the page still says this is not certification.
4. Open `/developers`, press "Get an API key now", press "Run POST /v1/review": the live JSON with `meta.gate` appears; download the Markdown report.
5. Open `/evidence`: fourteen verified studies, grouped by mechanism, fiction, contested findings, guideline effectiveness, and reviews.
6. Open `/stack`: Google cards should be live or active, including Agent Engine, Model Armor, the Gen AI Evaluation Service, and Cloud Monitoring; Replit Agent is active once the owner's evidence exists, Autoscale until the public deployment exists.

Duty of Care is not clinical review, censorship, certification, or proof that a scene is safe.
