# PLAN-07 Execution Log

## Status: COMPLETE (Steps 1-8; Step 9 GO-LIVE deferred to after PLAN-10)

## Steps

- [x] Step 1: GET webhook verification (hub.mode, hmac.compare_digest token check, 503 if unconfigured)
- [x] Step 2: POST HMAC signature verification (raw bytes, X-Hub-Signature-256, fail closed 503 on blank secret)
- [x] Step 3: dedup (deque+set pair, O(1) eviction), binding check, rate limit (Redis rl:wa:{from}, 10/min, one warn), fast ack via asyncio.create_task
- [x] Step 4: inbound handler in wa_jobs.py (find/create WA conv via Redis, route text/audio/other, run_turn, reply)
- [x] Step 5: transcribe.py (two-step Meta media fetch with auth header on both, duration+size checks, ffmpeg ogg->mp3, Whisper)
- [x] Step 6: tts.py (maybe_speak: voice_origin + word count < 300, openai tts-1-hd, temp mp3, caller deletes)
- [x] Step 7: wa_client.py (send_text, send_audio, send_template, 24h error 131047 -> template fallback, WA_DRY_RUN default, 1 retry on 5xx)
- [x] Step 8: scripts/simulate_wa.py (text/audio/status payloads, HMAC signing, --tamper flag), tests/test_wa_signature.py (9/9 pass)

## Changes made

- Created backend/app/services/wa_client.py
  - send_text, send_audio (upload then send media id), send_template
  - WA_DRY_RUN=True by default: logs payload, returns fake id
  - 24h window error (code 131047): falls back to send_template if WHATSAPP_ALERT_TEMPLATE set
  - 1 retry on 5xx, 15s timeout

- Created backend/app/services/transcribe.py
  - Two-step Meta media fetch: GET media metadata -> get URL -> GET URL with auth header
  - Content-type guard: rejects non-audio (auth-missing returns HTML page)
  - Duration and size checks (>300s or >16MB: returns None, caller sends reply)
  - ffmpeg ogg->mp3 in tempdir, OpenAI Whisper

- Created backend/app/services/tts.py
  - maybe_speak(answer_text, voice_origin): only when voice_origin and words < 300
  - OpenAI tts-1-hd, voice from settings.TTS_VOICE, writes temp mp3
  - Caller responsible for deleting the file

- Created backend/workers/wa_jobs.py
  - handle_inbound(msg, user_id): routes by type
  - _get_or_create_wa_conv: Redis key wa:conv:{user_id}, creates Conversation if missing/deleted
  - _process_text: append user msg, run_turn, read last assistant msg from DB, TTS or text reply
  - 4000-char trim: 3900 + "(continued on the dashboard)"
  - TTS path: send audio, clean temp file, fallback text summary for long answers

- Created backend/app/routers/whatsapp.py
  - GET /api/v1/integrations/whatsapp/webhook: verify token challenge, 503 if unconfigured
  - POST /api/v1/integrations/whatsapp/webhook: raw body HMAC, dedup deque+set (maxlen=500), binding, rate limit, asyncio.create_task
  - Status updates (no messages key): ack 200, skip
  - All exceptions after signature verification caught: always return 200 to Meta

- Created backend/scripts/simulate_wa.py
  - Builds Meta-style payload (text, audio, status receipt)
  - Signs with HMAC, reads secret from env or .env file
  - --tamper flag corrupts body after signing
  - --from-number, --wamid flags for binding and dedup tests

- Created backend/tests/test_wa_signature.py (9 tests, all pass)
  - valid signature 200, tampered body 401, missing header 401, blank secret 503
  - dedup: handler called exactly once on repeated wamid
  - unbound sender: 200 ack, handler not called
  - status update: 200 ack
  - GET verification: challenge echoed, wrong token 403

- Updated backend/app/config.py: added WHATSAPP_ALERT_TEMPLATE setting
- Updated backend/app/main.py: registered whatsapp_router
