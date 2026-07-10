# PLAN-11: ODIN Voice Interface

Written 2026-07-10. Depends on: PLAN-03 (WebSocket event contract), PLAN-04 (Hermes streaming), PLAN-08 (frontend SPA and Hermes orb). Execute after PLAN-08 is working.

## Goal

Give ODIN a bidirectional voice interface:
- Hermes speaks responses sentence-by-sentence as they stream (Text-to-Speech via OpenAI TTS).
- User speaks to Odin (Speech-to-Text via browser Web Speech API with wake word detection).
- An always-listening toggle lets the user go hands-free; saying "Odin" activates the mic.
- The Hermes orb shows three distinct states: idle / listening / speaking.

The target experience is conversational and low-latency, like Jarvis from Iron Man.

## New .env keys

Add to `backend/.env` and `.env.example`:

```
# Voice
TTS_VOICE=onyx
TTS_MODEL=tts-1-hd
TTS_ENABLED=1
# OPENAI_API_KEY already present from PLAN-04 provider chain
```

`onyx` is a deep authoritative male voice. Alternatives: `echo` (neutral), `nova` (female).

## Backend: TTS endpoint

### Step 1: Create `backend/app/api/voice.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.config import settings
from app.api.deps import get_current_user

router = APIRouter(prefix="/voice", tags=["voice"])


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None


@router.post("/tts")
async def text_to_speech(
    body: TTSRequest,
    _user=Depends(get_current_user),
):
    if not settings.TTS_ENABLED:
        raise HTTPException(503, "TTS is disabled")
    if not settings.OPENAI_API_KEY:
        raise HTTPException(503, "No OpenAI API key configured")

    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Empty text")
    if len(text) > 4096:
        text = text[:4096]

    voice = body.voice or settings.TTS_VOICE
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def audio_stream():
        async with client.audio.speech.with_streaming_response.create(
            model=settings.TTS_MODEL,
            voice=voice,
            input=text,
            response_format="mp3",
        ) as response:
            async for chunk in response.iter_bytes(1024):
                yield chunk

    return StreamingResponse(
        audio_stream(),
        media_type="audio/mpeg",
        headers={"X-Accel-Buffering": "no"},
    )
```

### Step 2: Register the router in `backend/app/api/__init__.py`

Add alongside the existing routers:

```python
from app.api.voice import router as voice_router
app.include_router(voice_router, prefix="/api/v1")
```

### Step 3: Add config fields to `backend/app/config.py`

```python
TTS_ENABLED: bool = True
TTS_VOICE: str = "onyx"
TTS_MODEL: str = "tts-1-hd"
```

### Step 4: Add OpenAI to dependencies

```
pip install openai
```

Add `openai>=1.30.0` to `requirements.txt`. (OpenAI is already in the provider chain; this just pins it.)

### Step 5: Backend STT endpoint (Firefox fallback only)

Create `backend/app/api/stt.py` for browsers that lack `SpeechRecognition` (Firefox):

```python
from fastapi import APIRouter, Depends, File, UploadFile
from openai import AsyncOpenAI
from app.config import settings
from app.api.deps import get_current_user

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    _user=Depends(get_current_user),
):
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    content = await audio.read()
    transcript = await client.audio.transcriptions.create(
        model="whisper-1",
        file=(audio.filename or "audio.webm", content, audio.content_type or "audio/webm"),
    )
    return {"text": transcript.text}
```

Register this router the same way as voice.py (they share the `/voice` prefix so keep them in the same file or merge).

## Frontend: voice hook and components

### Step 6: Create `frontend/src/hooks/useVoice.ts`

This hook owns all voice state. One instance lives at the App root and is passed via context.

```typescript
import { useRef, useState, useCallback, useEffect } from "react";
import { useWs } from "./useWs"; // existing WebSocket hook

const WAKE_WORD = "odin";
const SILENCE_MS = 1500; // ms after last speech to auto-submit

export type VoiceState = "idle" | "listening" | "speaking";

export function useVoice(onTranscript: (text: string) => void) {
  const [state, setState] = useState<VoiceState>("idle");
  const [alwaysOn, setAlwaysOnRaw] = useState<boolean>(
    () => localStorage.getItem("odin_voice_always_on") === "1"
  );

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const ttsQueueRef = useRef<string[]>([]);
  const isSpeakingRef = useRef(false);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const captureBufferRef = useRef<string>("");
  const wakeFiredRef = useRef(false);

  // Toggle always-on and persist
  const toggleAlwaysOn = useCallback(() => {
    setAlwaysOnRaw((prev) => {
      const next = !prev;
      localStorage.setItem("odin_voice_always_on", next ? "1" : "0");
      return next;
    });
  }, []);

  // Stop any playing TTS
  const stopSpeaking = useCallback(() => {
    ttsQueueRef.current = [];
    isSpeakingRef.current = false;
    setState("idle");
  }, []);

  // Play one TTS sentence
  const playTts = useCallback(async (text: string) => {
    if (!text.trim()) return;
    const res = await fetch("/api/v1/voice/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      credentials: "include",
    });
    if (!res.ok || !res.body) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => {
      URL.revokeObjectURL(url);
      isSpeakingRef.current = false;
      const next = ttsQueueRef.current.shift();
      if (next) {
        isSpeakingRef.current = true;
        void playTts(next);
      } else {
        setState("idle");
      }
    };
    setState("speaking");
    await audio.play();
  }, []);

  // Enqueue a sentence for TTS
  const enqueueTts = useCallback(
    (sentence: string) => {
      if (!sentence.trim()) return;
      ttsQueueRef.current.push(sentence);
      if (!isSpeakingRef.current) {
        isSpeakingRef.current = true;
        void playTts(ttsQueueRef.current.shift()!);
      }
    },
    [playTts]
  );

  // Build and start SpeechRecognition
  const startRecognition = useCallback(() => {
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SR) return; // Firefox fallback handled separately

    const rec: SpeechRecognition = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";
    recognitionRef.current = rec;

    rec.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map((r) => r[0].transcript.toLowerCase())
        .join(" ");

      // Interrupt TTS when user speaks
      if (isSpeakingRef.current) stopSpeaking();

      if (!wakeFiredRef.current) {
        if (transcript.includes(WAKE_WORD)) {
          wakeFiredRef.current = true;
          captureBufferRef.current = "";
          setState("listening");
        }
        return;
      }

      // Capture command after wake word
      const afterWake = transcript.split(WAKE_WORD).slice(1).join(" ").trim();
      captureBufferRef.current = afterWake;

      // Reset silence timer
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = setTimeout(() => {
        const cmd = captureBufferRef.current.trim();
        if (cmd) {
          onTranscript(cmd);
          captureBufferRef.current = "";
          wakeFiredRef.current = false;
          setState("idle");
        }
      }, SILENCE_MS);
    };

    rec.onend = () => {
      // Restart automatically in always-on mode
      if (alwaysOn) {
        setTimeout(() => rec.start(), 200);
      }
    };

    rec.onerror = (e: SpeechRecognitionErrorEvent) => {
      if (e.error === "not-allowed") {
        console.warn("Microphone permission denied");
      }
      if (alwaysOn) setTimeout(() => rec.start(), 1000);
    };

    rec.start();
  }, [alwaysOn, onTranscript, stopSpeaking]);

  // Effect: start/stop recognition when alwaysOn changes
  useEffect(() => {
    if (alwaysOn) {
      startRecognition();
    } else {
      recognitionRef.current?.stop();
      recognitionRef.current = null;
      setState("idle");
    }
    return () => {
      recognitionRef.current?.stop();
    };
  }, [alwaysOn, startRecognition]);

  // Push-to-talk: hold mic button
  const startPushToTalk = useCallback(() => {
    wakeFiredRef.current = true;
    captureBufferRef.current = "";
    setState("listening");
    if (!alwaysOn) startRecognition();
  }, [alwaysOn, startRecognition]);

  const stopPushToTalk = useCallback(() => {
    const cmd = captureBufferRef.current.trim();
    if (cmd) onTranscript(cmd);
    captureBufferRef.current = "";
    wakeFiredRef.current = false;
    if (!alwaysOn) {
      recognitionRef.current?.stop();
      recognitionRef.current = null;
    }
    setState("idle");
  }, [alwaysOn, onTranscript]);

  return {
    state,
    alwaysOn,
    toggleAlwaysOn,
    enqueueTts,
    stopSpeaking,
    startPushToTalk,
    stopPushToTalk,
  };
}
```

### Step 7: Sentence splitter utility

Create `frontend/src/lib/ttsFilter.ts`:

```typescript
// Strip content that should not be spoken aloud.
// Code blocks, JSON, URLs, and markdown syntax are removed.
export function ttsFilter(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, "Code block omitted.")
    .replace(/`[^`]+`/g, "")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/[*_~>#]/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // [label](url) -> label
    .trim();
}

// Split assistant text into sentences for low-latency TTS.
// Splits on . ! ? followed by whitespace or end of string.
// Respects common abbreviations by requiring the sentence to be >20 chars.
export function splitSentences(text: string): string[] {
  const raw = text.match(/[^.!?]+[.!?]+(\s|$)/g) ?? [text];
  return raw.map((s) => s.trim()).filter((s) => s.length > 5);
}
```

### Step 8: Update Hermes orb with three voice states

In `frontend/src/components/HermesOrb.tsx`, extend the existing orb with a `voiceState` prop:

```tsx
import { VoiceState } from "../hooks/useVoice";

interface HermesOrbProps {
  voiceState: VoiceState;
  size?: number;
}

const stateStyles: Record<VoiceState, string> = {
  idle: "animate-breathe",
  listening: "animate-pulse-fast ring-2 ring-primary ring-offset-2 ring-offset-surface",
  speaking: "animate-pulse-amber",
};

export function HermesOrb({ voiceState, size = 48 }: HermesOrbProps) {
  return (
    <div
      className={`hermes-orb rounded-full ${stateStyles[voiceState]}`}
      style={{ width: size, height: size }}
      title={voiceState === "listening" ? "Listening..." : voiceState === "speaking" ? "Odin speaking" : "Odin"}
    />
  );
}
```

Add to `tailwind.config.ts` keyframes:

```js
"pulse-fast": {
  "0%, 100%": { transform: "scale(1)", boxShadow: "0 0 8px rgba(255,107,0,0.8)" },
  "50%": { transform: "scale(1.15)", boxShadow: "0 0 24px rgba(255,107,0,1)" },
},
"pulse-amber": {
  "0%, 100%": { transform: "scale(1)", boxShadow: "0 0 8px rgba(255,186,32,0.6)" },
  "50%": { transform: "scale(1.08)", boxShadow: "0 0 20px rgba(255,186,32,0.9)" },
},
```

And animation durations:

```js
"pulse-fast": "0.8s ease-in-out infinite",
"pulse-amber": "1.2s ease-in-out infinite",
```

### Step 9: Voice toggle UI in the top bar

In the top bar component, add two controls next to the Hermes orb:

```tsx
import { Mic, MicOff, Volume2, VolumeX } from "lucide-react";

// Always-listening toggle
<button
  onClick={voice.toggleAlwaysOn}
  title={voice.alwaysOn ? "Always-listening ON" : "Always-listening OFF"}
  className={`p-2 rounded transition-colors ${
    voice.alwaysOn
      ? "bg-primary text-on-primary"
      : "text-on-surface-variant hover:text-on-surface"
  }`}
>
  {voice.alwaysOn ? <Mic size={18} /> : <MicOff size={18} />}
</button>

// Push-to-talk (hold)
<button
  onMouseDown={voice.startPushToTalk}
  onMouseUp={voice.stopPushToTalk}
  onTouchStart={voice.startPushToTalk}
  onTouchEnd={voice.stopPushToTalk}
  title="Hold to speak"
  className="p-2 rounded text-on-surface-variant hover:text-primary active:text-primary active:bg-primary/10"
>
  <Mic size={18} />
</button>

// Mute TTS
<button
  onClick={voice.stopSpeaking}
  title="Stop speaking"
  className="p-2 rounded text-on-surface-variant hover:text-primary"
>
  <VolumeX size={18} />
</button>
```

### Step 10: Wire TTS into the chat streaming loop

In `frontend/src/components/Chat.tsx` (or wherever WebSocket messages are handled), intercept `message.token` and `message.done` to feed the TTS sentence splitter:

```typescript
const sentenceBufferRef = useRef("");

// On message.token
function onToken(delta: string) {
  appendToMessage(delta); // existing render logic

  // Accumulate and split into speakable sentences
  sentenceBufferRef.current += delta;
  const filtered = ttsFilter(sentenceBufferRef.current);
  const sentences = splitSentences(filtered);

  if (sentences.length > 1) {
    // All but the last sentence are complete; speak them
    sentences.slice(0, -1).forEach((s) => voice.enqueueTts(s));
    // Keep the incomplete final sentence in the buffer
    sentenceBufferRef.current = sentences[sentences.length - 1];
  }
}

// On message.done
function onDone() {
  const remaining = ttsFilter(sentenceBufferRef.current).trim();
  if (remaining) voice.enqueueTts(remaining);
  sentenceBufferRef.current = "";
  // existing logic (swap glass-panel, token count, etc.)
}
```

### Step 11: Wire transcript callback to send chat message

In `App.tsx` (or the root that owns chat state), pass the handler to `useVoice`:

```typescript
const { state: voiceState, ...voiceControls } = useVoice((transcript) => {
  // Same as the user hitting Enter in the chat input
  sendMessage(transcript);
});
```

### Step 12: Firefox fallback (MediaRecorder + Whisper)

Detect missing `SpeechRecognition` at startup and show a notice:

```typescript
const hasSpeechApi =
  typeof window !== "undefined" &&
  ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

if (!hasSpeechApi) {
  // Render a push-to-talk button only using MediaRecorder -> /api/v1/voice/stt
  // Steps:
  // 1. navigator.mediaDevices.getUserMedia({ audio: true })
  // 2. new MediaRecorder(stream, { mimeType: "audio/webm" })
  // 3. Collect chunks on dataavailable
  // 4. On stop: POST FormData with blob to /api/v1/voice/stt
  // 5. Use the returned text as the transcript
}
```

Implement this as `<FirefoxPushToTalk onTranscript={onTranscript} />`. Only renders when `!hasSpeechApi`.

## Edge cases a weaker model would miss

1. **`SpeechRecognition` needs the webkit prefix on some Chrome versions.** Always use `window.SpeechRecognition || window.webkitSpeechRecognition`. Assigning it to a variable before `new` avoids the "Illegal invocation" error.

2. **Continuous mode auto-ends after ~5s of silence.** The `onend` handler MUST restart the recognition in always-on mode or the listener dies silently. Add a 200ms delay before restart to avoid a CPU spin loop.

3. **`SpeechRecognition` is completely absent in Firefox** (as of 2026). Never call it there; fall through to the `MediaRecorder` path.

4. **TTS queue must be a ref, not state.** React state updates are async; a ref queue processes synchronously in the `onended` callback without stale closure issues.

5. **Never play two `Audio` objects simultaneously.** The `onended` handler checks the queue and only starts the next after the current finishes. Do not `Promise.all` TTS calls.

6. **OpenAI TTS does not support SSML.** Strip all HTML, markdown, and special characters before sending. The `ttsFilter` function handles this. Also strip `[Source: ...]` citation markers.

7. **Code blocks must be replaced, not stripped.** If you return an empty string for a code block, the sentence splitter may merge surrounding text. Replace with `"Code block omitted."` so TTS keeps correct sentence rhythm.

8. **`getUserMedia` requires HTTPS in production.** On localhost it works over HTTP. The `PLAN-10` nginx TLS setup handles this. Never tell the user voice works without TLS on the VPS.

9. **Interrupt on wake word fires too early.** The `onresult` event fires on interim results. Only interrupt TTS and start capturing when a FINAL result contains the wake word (`event.results[i].isFinal`). Update the handler to check `isFinal` before triggering wake word logic.

    Revised check:
    ```typescript
    const finalTranscript = Array.from(event.results)
      .filter((r) => r.isFinal)
      .map((r) => r[0].transcript.toLowerCase())
      .join(" ");
    if (finalTranscript.includes(WAKE_WORD)) { ... }
    ```

10. **Saying "Odin" in a response should not re-trigger wake word.** The wake word detector runs only while Odin is NOT speaking. Gate the check: `if (isSpeakingRef.current) return;` at the top of `onresult`.

11. **`AudioContext` autoplay policy.** Browsers require a user gesture before audio can play. The first TTS call after page load may be silently blocked. Resolve by calling `new AudioContext()` inside the first user click handler (the login button works). The `Audio` API (used here instead of `AudioContext`) has looser restrictions but still fails before any interaction. Mount the push-to-talk button on the login page so the user's first click primes autoplay.

12. **TTS on tool result blocks.** The `tool.result` WS event fires with a `summary` string. Do NOT pipe tool results to TTS by default; they are often structured data. Only speak the conversational assistant text from `message.token` events.

13. **Always-listening and privacy.** Show a persistent visual indicator (the active-state mic icon in the top bar) whenever always-on is active. Never hide this. Users must be able to see at a glance that the mic is open.

## Acceptance criteria

1. `POST /api/v1/voice/tts` with body `{"text": "Hello"}` returns 200 with `Content-Type: audio/mpeg` and playable audio.
2. Asking Hermes a question in the chat: the assistant response is spoken sentence-by-sentence as it streams. A response with 5 sentences does not wait for all 5 before speaking sentence 1.
3. Saying "Odin what time is it" in always-on mode sends the query to chat automatically within 2 seconds of finishing speech.
4. The Hermes orb shows the breathing animation when idle, fast orange pulse when listening, amber pulse when speaking.
5. Saying a new command while Hermes is speaking interrupts TTS and the orb returns to listening state.
6. Code blocks in Hermes responses are NOT spoken aloud (replaced with "Code block omitted").
7. The always-on toggle is persisted across page reloads (`localStorage.getItem("odin_voice_always_on")`).
8. In a Chrome DevTools network tab: TTS requests go to `/api/v1/voice/tts` (no external CDN calls; no ElevenLabs, no external OpenAI calls from the browser directly).
9. In Firefox: always-listening is not available (mic icon disabled), push-to-talk sends audio to `/api/v1/voice/stt` and result appears in chat.
10. `TTS_ENABLED=0` in `.env` causes `/api/v1/voice/tts` to return 503 and the frontend silently skips TTS (no error shown to user).

## Work log

- 2026-07-10: Plan written. Covers TTS endpoint, STT fallback, sentence-streaming queue, wake word detection, three-state orb, always-on toggle.
