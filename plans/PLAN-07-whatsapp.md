# PLAN-07: WhatsApp Gateway, Voice Notes, TTS Replies, Proactive Sends

Goal: the full SPEC 2.6 WA block and SPEC 12.1: webhook verification (GET challenge and POST HMAC), message dedup, per-user rate limit, routing inbound text into Hermes conversations, Whisper transcription of voice notes, TTS audio replies under 300 words, and the outbound client used for proactive notifications. Everything except the final go-live section is buildable and testable locally with simulated signed payloads.

Prerequisites: PLAN-04 (Hermes). PLAN-05 improves answers but is not required. The go-live section requires PLAN-10 (public HTTPS URL).

## Files to create or touch

```
backend\app\routers\whatsapp.py
backend\app\services\wa_client.py
backend\app\services\transcribe.py
backend\app\services\tts.py
backend\workers\wa_jobs.py
backend\scripts\simulate_wa.py
backend\tests\test_wa_signature.py
backend\app\main.py    (include router)
```

## Steps in order

### Step 1: webhook verification handshake (GET)

`GET /api/v1/integrations/whatsapp/webhook` with query params `hub.mode`, `hub.verify_token`, `hub.challenge`: if mode is `subscribe` and the token matches `settings.WHATSAPP_VERIFY_TOKEN` via `hmac.compare_digest`, return the raw challenge string as plain text 200. Anything else: 403. If `WHATSAPP_VERIFY_TOKEN` is blank: 503.

### Step 2: signature verification (POST, WA-02)

In `routers\whatsapp.py`:

```python
@router.post("/api/v1/integrations/whatsapp/webhook")
async def inbound(request: Request):
    if not settings.WHATSAPP_APP_SECRET:
        raise HTTPException(503)          # fail closed, never open
    raw = await request.body()            # RAW bytes, before any parsing
    header = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(), raw, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(header, expected):
        raise HTTPException(401)
    payload = json.loads(raw)
    ...
```

The HMAC is computed over the exact raw body bytes. Never `await request.json()` first and re-serialize; key order and whitespace differ and verification will fail intermittently.

### Step 3: dedup, binding, rate limit, fast ack

After signature passes, extract messages from `entry[].changes[].value.messages` (may be absent: status updates arrive on the same webhook; ack those with 200 and skip):

1. **Dedup (WA-06):** module-level `deque(maxlen=500)` plus a mirror `set` for O(1) lookup: on eviction from the deque, discard from the set. Key is the Meta message id (`wamid...`). Duplicate: return 200 immediately without processing.
2. **Binding:** if `msg["from"]` does not equal `settings.WHATSAPP_ALLOWED_NUMBER` (digits only, no plus, exactly as Meta sends it): log `unbound_wa_sender`, return 200, do nothing else. Never reply to strangers.
3. **Rate limit (WA-07):** Redis window `rl:wa:{from}`, 10 per minute. Over limit: send one "Slow down a little" text (only once per window), return 200.
4. **Fast ack:** all real processing happens in a background task (`asyncio.create_task` calling the handler in Step 4). The webhook itself must return 200 in well under a second; Meta retries slow acks, which is what makes dedup mandatory.

### Step 4: inbound handler

`handle_inbound(msg)`:

- Find or create the WhatsApp conversation: one rolling conversation titled "WhatsApp" per user (store its id in Redis `wa:conv:{user_id}`; recreate if archived/deleted).
- `type == "text"`: persist the user message (source whatsapp via the audit origin), run the PLAN-04 `run_turn` with a WhatsApp reply sink: instead of relying on WS delivery, collect the final assistant text and send it back via `wa_client.send_text`. Answers over 4000 chars: send the first 3900 plus "(continued on the dashboard)".
- `type == "audio"`: Step 5 pipeline, then treat the transcript as text input. If the transcript came from a voice note, mark the turn `voice_origin=True` for Step 6.
- Any other type (image, sticker, location): polite "I can handle text and voice notes for now."

### Step 5: voice notes (WA-04)

`transcribe.py`:

1. Media fetch is two-step: `GET https://graph.facebook.com/v20.0/{media_id}` with the bearer token returns a JSON containing `url`; then GET that url WITH the same bearer header (unauthenticated fetch returns an HTML error page, a classic trap).
2. Reject when Meta reports the audio duration over 300 seconds or the file exceeds 16 MB: reply "That voice note is too long for me (5 minute limit)."
3. Save the .ogg to the scratchpad-style temp dir inside the container, convert: `ffmpeg -i in.ogg out.mp3` (ffmpeg is in the PLAN-01 image), then OpenAI `client.audio.transcriptions.create(model="whisper-1", file=...)`.
4. Blank OPENAI_API_KEY: reply "Voice notes need the transcription service, which is not configured." and stop.

### Step 6: TTS replies (WA-08, CHAT-08)

`tts.py :: maybe_speak(answer_text) -> path or None`: only when the turn is `voice_origin` AND the word count is under 300. Use OpenAI `client.audio.speech.create(model="tts-1", voice="alloy", input=answer_text)` writing an mp3. `wa_client.send_audio`: upload via `POST /{phone_number_id}/media` multipart (type audio/mpeg), then send a message with the returned media id. Over 300 words: send text summary line "Long answer, full version on the dashboard" plus the text itself trimmed per Step 4.

### Step 7: wa_client.py (outbound, also used by PLAN-09)

- `send_text(to, body)`, `send_audio(to, media_path)`, `send_template(to, template_name, components)` hitting `https://graph.facebook.com/v20.0/{phone_number_id}/messages` with the bearer token, httpx, 15 s timeout, one retry on 5xx.
- `WA_DRY_RUN=1` (dev default): do not call Meta; log the full outbound payload at INFO and return a fake message id. Every acceptance test below runs in dry-run.
- **The 24-hour window rule:** free-form messages only work within 24 h of the user's last inbound message. Outside it, Meta returns error 131047. `send_text` catches that error and falls back to `send_template(to, "odin_alert", [title])` if a template name is configured (`WHATSAPP_ALERT_TEMPLATE` env var, empty means "store as in-app notification only and log a warning"). PLAN-09's proactive jobs rely on this fallback.

### Step 8: simulator and tests

- `scripts\simulate_wa.py`: builds a realistic Meta payload (text or audio message), signs it with `WHATSAPP_APP_SECRET` from `.env`, POSTs to `http://localhost:8000/api/v1/integrations/whatsapp/webhook`. Flags: `--text "..."`, `--wamid <id>` (for dedup tests), `--from-number <digits>`.
- `tests\test_wa_signature.py`: valid signature 200; tampered body 401; missing header 401; blank app secret 503; duplicate wamid processed once (assert the handler ran once via a counter monkeypatch); unbound sender acked but ignored; status-update payload (no messages key) acked 200.

### Step 9: GO-LIVE (only after PLAN-10, in this order)

1. In the Meta developer console create (or reuse) the WhatsApp Business app; note App Secret, permanent token, phone number id. Put them in the VPS `.env` (never in git) and restart the stack.
2. Set `WA_DRY_RUN=0` on the VPS.
3. Configure the webhook URL `https://odin.YOUR_DOMAIN/api/v1/integrations/whatsapp/webhook` with your `WHATSAPP_VERIFY_TOKEN`; Meta fires the GET handshake; it must turn green.
4. Subscribe the app to the `messages` webhook field.
5. Send "hello" from the allowed phone; confirm a Hermes reply arrives.
6. Send a short voice note; confirm a transcribed answer and, for a short answer, an audio reply.
7. Optional: submit an `odin_alert` utility template ("ODIN alert: {{1}}") for approval and set `WHATSAPP_ALERT_TEMPLATE=odin_alert` so proactive sends work outside the 24 h window.

## Edge cases a weaker model would miss

1. **Raw body or nothing.** Any middleware or code path that consumes/parses the body before HMAC computation breaks verification. Keep this route free of body-touching dependencies.
2. **Fail closed on missing secret (503, never skip verification).** SPEC WA-02 says it explicitly; a "temporarily skip in dev" branch WILL ship to prod.
3. **Ack fast, always 200.** Meta retries non-200 and slow responses; an exception mid-processing must still return 200 (log it), or you get a retry storm of duplicate messages. Never return 500 to Meta after the signature has passed.
4. **Status callbacks share the webhook.** Delivery receipts have no `messages` key; code that assumes it crashes on the very first sent message's receipt.
5. **Media URL needs the auth header on BOTH requests.** The second GET without the bearer returns 200 with an HTML page, which then "converts" to a garbage mp3; detect non-audio content types.
6. **The 24-hour window (error 131047)** makes template fallback a requirement for PLAN-09's morning agenda, not a nice-to-have.
7. **`from` numbers have no plus sign.** Store `WHATSAPP_ALLOWED_NUMBER` as digits only; a weaker model compares "+2637..." to "2637..." and locks the owner out.
8. **Dedup set needs bounded memory** (deque + set pair). A plain set grows forever; a plain deque makes lookups O(n).
9. **Voice notes from WhatsApp are .ogg opus;** Whisper accepts ogg directly but the spec pipeline converts to mp3 first (SPEC 12.1); keep the ffmpeg step, it also normalizes weird codecs.
10. **Do not store message bodies in logs.** Log wamids, types, and lengths; the bodies land in the conversation like any chat (that is the retention story; see the ThemisIQ bridge DPIA precedent).
11. **Answers must be trimmed for WhatsApp's 4096-char message cap** or the send silently fails.

## Acceptance criteria (verify each)

1. `pytest tests/test_wa_signature.py -q` passes.
2. `python scripts/simulate_wa.py --text "create a task called Pay rent, high priority"` (dry-run mode): a task row appears, and the log shows an outbound send_text payload with a confirmation sentence.
3. Same command repeated with the same `--wamid`: exactly one task exists (dedup proof).
4. `--from-number 15550000000` (not the allowed number): 200 ack, no task, `unbound_wa_sender` in logs.
5. Eleven simulated texts in one minute: the eleventh gets the rate-limit reply once, and processing stops.
6. Tampering one byte of the simulator's body after signing produces 401 (the simulator has a `--tamper` flag for this).
7. GO-LIVE checklist (post PLAN-10): webhook verified green in Meta console, real text answered on the phone, real voice note answered, audio reply received for a short question.
