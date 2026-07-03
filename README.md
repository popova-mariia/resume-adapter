# Resume Adapter

Local, privacy-first demo for an Agentic AI workshop.

## Try the deployed version

You can test the hosted Render version here:

https://resume-adapter-q3hg.onrender.com/

The hosted version is useful for quick testing, but remember: text you enter is sent from your browser to the Render server, and then the redacted resume/job text is sent to Groq.

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

## Implementation notes

- The browser keeps a placeholder map such as `[[RID_1]]` to the original sensitive value.
- The app checks that placeholders survived before restoring them.
- Placeholders that are present in the model response are restored locally.
- Console logging is intentionally quiet during a live demo.