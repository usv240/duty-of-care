# Security and privacy

## Data boundaries

- Anonymous screenplay text is processed only when the writer presses Review. Files chosen in the browser are parsed there and never uploaded on their own.
- The service does not persist screenplay text, results, or user identity by default.
- Logs contain one structured line per review: request id, caller tier and key id, region, scene count, trigger classes, note and clause counts, model, latency, surface. They never include request bodies, scene excerpts, model prompts, or generated alternatives.
- Exports (`POST /v1/exports`) happen only when the writer presses Export. On Replit they go to App Storage; elsewhere to a temporary local file that does not survive an instance restart.
- Saved decisions (`/v1/decisions`) require a signed-in Replit Auth writer, are scoped to that writer, are deletable, and store a hash of the scene, never its text. The `X-Replit-User-*` headers are trusted only when the process runs on Replit.
- The approved guidance corpus contains public source metadata and short attributed clauses only.
- No Google service-account key belongs in this repository or in Replit. Replit holds only the backend URL and its own signing secret as Replit Secrets.
- When the agent runs on Vertex AI Agent Engine, the session state carries the scene text and retrieved clauses for the duration of that review; Agent Engine sessions are created per review and are not reused. When the managed runtime fails, the identical agent runs in-process and the response records `runtime: adk_in_process_fallback`.

## API keys and limits

- Keys are stateless HMAC tokens (`doc_<id>_<issued>_<signature>`) signed with `DUTY_OF_CARE_API_KEY_SECRET`, mounted on Cloud Run from Secret Manager (`duty-of-care-api-key-secret`). No plaintext key is stored anywhere.
- A key cannot be revoked individually; rotate the secret to invalidate all keys. Keys expire after 90 days.
- Per-caller sliding-window limits per minute: review 6, keys 10, exports 10, decisions 30; keyed callers get 5x. Limits are enforced per instance.
- The API limits a screenplay to 250,000 characters. Replit's proxy must also enforce body and timeout limits, use a fixed upstream allowlist, and prevent open redirects or arbitrary URL fetching.

## Safety boundary

Duty of Care is not a clinical, emergency, censorship, compliance, or certification system. It does not assess a person's risk. Four layers sit between the model and the writer:

1. The agent only sees clauses that Google Agent Search returned and code accepted; it cannot cite from memory.
2. Gemini runs with explicit safety settings (hate speech, harassment, sexually explicit content at medium-and-above; dangerous content at high only, because the scenes legitimately discuss suicide).
3. The project's hard filter rejects certification phrases anywhere in generated text and any alternative more method-specific than the writer's own text. The agent must run it as a tool before answering; the API applies it again to the alternative section of the final answer.
4. Google Cloud Model Armor (`duty-of-care-agent-output` template) screens the final text for hate, harassment, sexual and dangerous content, prompt-injection patterns, malicious URIs, and sensitive data. A match, or a screening error, withholds the text and fails the `model_armor_clear` gate; the clauses stay.

The absence of a flag is never described as safe.

In the U.S., call or text 988. In immediate danger, contact local emergency services. Outside the U.S., use a verified local service such as Find A Helpline.

## Reporting

Do not open a public issue containing screenplay content, personal information, credentials, or a vulnerability exploit. Use GitHub's private vulnerability reporting for `usv240/duty-of-care`. Include the affected commit, route, reproduction steps with synthetic data, and impact. Do not include real sensitive narratives.
