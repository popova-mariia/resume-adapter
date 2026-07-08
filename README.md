# Resume Adapter

Local, privacy-first demo for an Agentic AI workshop.

## Try the deployed version

You can test the hosted Render version here:
https://resume-adapter-q3hg.onrender.com/

The hosted version is useful for quick testing, but remember: text you enter is sent from your browser to the Render server, and then the redacted resume/job text is sent to Groq.

## Demo assets

Use these to try the app end to end without hunting for your own inputs.

### Demo video (~3 min, no audio)

[Demo video](https://github.com/popova-mariia/resume-adapter/blob/main/assets/demo_video.mp4)

### Sample resume

[Sample resume](https://github.com/popova-mariia/resume-adapter/blob/main/assets/resume_sample.txt)

### Sample job posting


- **Live UI/UX search on InternSG:** https://www.internsg.com/jobs/?f_0=1&f_p=&f_i=&filter_s=ui+ux
  Pick any current listing and copy the description into the app.

*Example role (may be gone by the time you read this):* "UI UX Design and Product Assistant" — Mikomiko Pte. Ltd. (mikomiko.ai), Queenstown SG / work-from-home, intern.
Link: https://www.internsg.com/job/mikomiko-pte-ltd-ui-ux-design-and-product-assistant/?f_0=1&filter_s=ui+ux
If not outdated.

## Suggested demo flow

A short script for presenting this live. Adjust to taste.

1. **Start the app.** Run it locally (`python3 app.py`, then open http://127.0.0.1:8765) or open the hosted Render version. Local is the stronger privacy story, because the redaction step is easy to prove on your own machine.
2. **Load a job.** Paste a job description, or paste a job URL and let the app fetch it (the `/api/fetch_job` endpoint). Use a current UI/UX listing from the InternSG search link in *Demo assets*.
3. **Load the resume.** Paste the sample resume text (a fake identity — see the privacy warning in *Demo assets*).
4. **Redact.** Highlight or auto-detect the sensitive fields (name, phone, email). Point out that they are replaced with placeholder tokens like `[[RID_1]]` **in the browser, before any request is sent**.
5. **Adapt.** Send to Groq. Only the redacted text leaves the machine; Groq returns an adapted resume.
6. **Restore.** Show the placeholders swapped back to the real values locally.
7. **Prove it (the key moment).** Open your browser's DevTools → Network tab (before you send, or inspect the request that was already sent) and show that the outbound request body contains only redacted text — the real name/phone/email never left the machine.

> The DevTools step is what makes the privacy claim credible to an audience. I'd rehearse it once before presenting.

## What it does

Paste a job description and your resume. Highlight or auto-detect sensitive information like your name, phone, or email. Those details are replaced with placeholder tokens locally in your browser before anything is sent. Only the redacted text is sent to Groq. When Groq replies, the original values are put back in locally.

## Privacy model

- Redaction happens in the browser before any network call.
- The Groq call is made by this local proxy, not the browser, so your API key is never exposed to the page.
- The only data that leaves your machine is the redacted resume and the job text.
- This is still a cloud call: Groq sees the redacted resume. It does not see whatever you redacted. Redact carefully and verify Groq's current data policy.

## Setup

1. Get a free Groq API key at https://console.groq.com with no credit card.
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. In a terminal, set your API key:
   ```bash
   export GROQ_API_KEY="your_key_here"
   ```
   ```cmd
   set GROQ_API_KEY=your_key_here
   ```
   ```powershell
   $env:GROQ_API_KEY="your_key_here"
   ```
4. Run the app:
   ```bash
   python3 app.py
   ```
5. Open http://127.0.0.1:8765 in your browser.

## Notes and things to verify

- The model id in the code, `llama-3.3-70b-versatile`, was current in 2026 sources, but model availability changes. If you get a model error, pick a current one at https://console.groq.com/docs/models.
- Free-tier rate limits change; a single demo is fine. Verify limits at https://console.groq.com/settings/limits.
- Do not commit this file with your key in it, and do not deploy it publicly. The key lives only in your local environment variable; keep it that way.

## Tech stack

Verified from the repo (`requirements.txt`, `app.py`, `groq_client.py`, `page.py`).

- **Language:** Python 3, standard library only — `requirements.txt` declares no third-party packages.
- **Web server / API:** `http.server` + `socketserver` (`BaseHTTPRequestHandler`). Serves the page on `GET /`, and exposes `POST /api/skills`, `/api/rewrite`, and `/api/fetch_job`.
- **Outbound HTTP:** `urllib.request` (stdlib) for both the Groq call and server-side job fetching.
- **LLM:** Groq chat-completions API (OpenAI-compatible endpoint, `https://api.groq.com/openai/v1/chat/completions`). Default model `llama-3.3-70b-versatile`, overridable with the `GROQ_MODEL` environment variable.
- **Frontend:** a single HTML page served from Python (`page.py`) using plain HTML/CSS/JavaScript — no framework, no CDN, served as a string (no build step). Redaction runs in the browser.
- **Hosting:** runs locally on `127.0.0.1:8765`; the hosted demo is on Render (reads `PORT` from the environment).
- **Module layout:** `app.py` (server/routing), `groq_client.py` (Groq calls, skill/edit parsing), `job_fetcher.py` (fetch a posting by URL), `prompts.py` (system prompts), `page.py` (served HTML/JS).

## Implementation notes

- The browser keeps a placeholder map such as `[[RID_1]]` to the original sensitive value.
- The app checks that placeholders survived before restoring them.
- Placeholders that are present in the model response are restored locally.
- Console logging is intentionally quiet during a live demo.
