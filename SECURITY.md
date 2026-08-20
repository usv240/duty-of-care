# Security and privacy

## Data boundaries

- Anonymous screenplay text is processed only when the writer presses Review.
- The Cloud Run service does not intentionally persist screenplay text, results, or user identity.
- Logs must not include request bodies, scene excerpts, model prompts, or generated alternatives.
- The approved guidance corpus contains public source metadata and short attributed clauses only.
- No Google service-account key belongs in this repository or in Replit. Replit should call the fixed Cloud Run backend URL.
- Future saved decisions must be opt-in, authenticated, scoped to the owner, deletable, and documented with a retention period.

The API limits a screenplay to 250,000 characters. Replit's proxy must also enforce body and timeout limits, use a fixed upstream allowlist, and prevent open redirects or arbitrary URL fetching.

## Safety boundary

Duty of Care is not a clinical, emergency, censorship, compliance, or certification system. It does not assess a person's risk. Hard filters reject prohibited certification phrases and any generated alternative that increases detected method specificity. The absence of a flag is never described as safe.

In the U.S., call or text 988. In immediate danger, contact local emergency services. Outside the U.S., use a verified local service such as Find A Helpline.

## Reporting

Do not open a public issue containing screenplay content, personal information, credentials, or a vulnerability exploit. Use GitHub's private vulnerability reporting for `usv240/duty-of-care`. Include the affected commit, route, reproduction steps with synthetic data, and impact. Do not include real sensitive narratives.
