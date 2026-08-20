# Duty of Care

Duty of Care is a guidance-grounded pre-review for independent screenwriters depicting suicide, self-harm, or addiction. It is not a censor, clinical tool, or professional certification. The writer can accept, dismiss, or request expert review; nothing is blocked.

The architecture has three layers: auditable deterministic trigger candidates, exact clauses retrieved from an approved Vertex AI Search guidance corpus, and a human writer decision. A trigger is never promoted to a guidance conflict without a citation. The API therefore returns zero grounded flags—not fabricated ones—until the data store exists.

Hard code prevents “your scene is safe” language and rejects any generated suggestion that increases method specificity. Crisis resources are always returned. Multi-jurisdiction clauses are represented separately and must not be silently reconciled.

Run `benchmark/generate.py` to produce 48 self-authored CC0 cases. This synthetic set is for engineering only; the required ten-scene qualified expert review has not yet occurred.

Track eligibility still requires actual Replit Agent evidence and a public Replit Autoscale deployment. See `replit.md`.
