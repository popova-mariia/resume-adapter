#!/usr/bin/env python3
"""
Resume Adapter - local, privacy-first demo for an Agentic AI workshop.

WHAT IT DOES
  Paste a job description + your resume. Highlight (or auto-detect) sensitive
  info like your name/phone/email. Those are replaced with placeholder tokens
  LOCALLY, in your browser, before anything is sent. Only the redacted text is
  sent to Groq. When Groq replies, the original values are put back in, locally.

PRIVACY MODEL (read this)
  * Redaction happens in the browser BEFORE any network call.
  * The Groq call is made by THIS local proxy, not the browser, so your API key
    is never exposed to the page.
  * The ONLY data that leaves your machine is the redacted resume + the job text.
  * This is still a cloud call: Groq sees the redacted resume. It does NOT see
    whatever you redacted. Redact carefully; verify Groq's current data policy.

SETUP
  1) Get a free Groq API key at https://console.groq.com  (no credit card).
  2) In a terminal:
        export GROQ_API_KEY="your_key_here"     # macOS/Linux
        set    GROQ_API_KEY=your_key_here        # Windows cmd
        $env:GROQ_API_KEY="your_key_here"        # Windows PowerShell
  3) python3 resume_adapter.py
  4) Open http://127.0.0.1:8765 in your browser.

NOTES / THINGS TO VERIFY (I flagged these honestly):
  * Model id below ("llama-3.3-70b-versatile") was current in 2026 sources but
    model availability changes. If you get a model error, pick a current one at
    https://console.groq.com/docs/models
  * Free-tier rate limits change; a single demo is fine. Verify at
    https://console.groq.com/settings/limits
  * Do NOT commit this file with your key in it, and do NOT deploy it publicly:
    the key lives only in your local environment variable, keep it that way.
"""

import http.server
import socketserver
import json
import os
import urllib.request
import urllib.error

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
PORT = int(os.environ.get("PORT", "8765"))

SYSTEM_PROMPT = (
    "You are a resume-tailoring assistant. You receive a JOB DESCRIPTION and a "
    "candidate's RESUME. Some sensitive details in the resume have been replaced "
    "with placeholder tokens that look like [[RID_1]], [[RID_2]], and so on.\n\n"
    "PLACEHOLDER RULE (critical): Treat every [[RID_n]] token as an opaque, fixed "
    "string. Reproduce each one EXACTLY where it appears. Never modify, translate, "
    "remove, merge, or invent placeholder tokens.\n\n"
    "YOUR TASK: Rewrite the resume (or its most relevant sections) so the "
    "candidate's genuine, existing experience is expressed using the terminology "
    "and keywords found in the job description, to improve relevance and keyword "
    "match for applicant tracking systems.\n\n"
    "INTEGRITY RULES (do not break):\n"
    "- Do NOT invent skills, tools, employers, dates, certifications, degrees, or "
    "achievements that the resume does not already support. Only rephrase and "
    "surface what is genuinely present.\n"
    "- If the job wants something the resume lacks, do not fabricate it. You may "
    "note, in a short separate 'Gaps to consider' section at the very end, which "
    "required items appear to be missing so the candidate can address them "
    "honestly.\n"
    "- Keep all [[RID_n]] placeholders verbatim.\n"
    "- Keep the tone professional and the content truthful.\n\n"
    "Output the tailored resume text, followed by the optional 'Gaps to consider' "
    "section. Do not add commentary before or after."
)


def call_groq(redacted_resume, job_text):
    payload = {
        "model": MODEL,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                "JOB DESCRIPTION:\n" + job_text +
                "\n\n---\n\nRESUME (sensitive parts already redacted):\n" +
                redacted_resume},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(GROQ_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + GROQ_API_KEY)
    req.add_header("User-Agent",
                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, ctype, body_bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def _json(self, code, obj):
        self._send(code, "application/json", json.dumps(obj).encode("utf-8"))

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE.encode("utf-8"))
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/rewrite":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            resume = payload.get("resume", "")
            job = payload.get("job", "")
        except (ValueError, TypeError) as exc:
            self._json(400, {"error": "Bad request: %s" % exc})
            return
        if not resume.strip() or not job.strip():
            self._json(400, {"error": "Please provide both a job description and a resume."})
            return
        if not GROQ_API_KEY:
            self._json(500, {"error":
                "GROQ_API_KEY is not set. Set it in your terminal and restart. "
                "See the setup notes at the top of resume_adapter.py."})
            return
        try:
            result = call_groq(resume, job)
            self._json(200, {"result": result})
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            self._json(502, {"error": "Groq returned HTTP %s. %s" % (exc.code, detail)})
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self._json(502, {"error": "Call failed: %s" % exc})

    def log_message(self, *args):
        return  # keep the console quiet during a live demo


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Resume Adapter (local)</title>
<style>
  :root { --bg:#0f1216; --panel:#171b22; --line:#2a313c; --ink:#e7ecf3;
          --mut:#94a3b8; --accent:#5b9dff; --warn:#f6b93b; --bad:#ff6b6b; --ok:#4ade80; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:15px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
  header { padding:18px 22px; border-bottom:1px solid var(--line); }
  header h1 { margin:0 0 4px; font-size:18px; }
  header p { margin:0; color:var(--mut); font-size:13px; }
  .wrap { display:grid; grid-template-columns:1fr 1fr; gap:16px; padding:18px 22px; }
  @media (max-width:900px){ .wrap{ grid-template-columns:1fr; } }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; }
  .panel h2 { margin:0 0 8px; font-size:13px; text-transform:uppercase;
              letter-spacing:.04em; color:var(--mut); }
  textarea { width:100%; min-height:150px; resize:vertical; background:#0c0f13;
             color:var(--ink); border:1px solid var(--line); border-radius:8px;
             padding:10px; font:13px/1.5 ui-monospace,Menlo,Consolas,monospace; }
  .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
  button { background:var(--accent); color:#06101f; border:0; border-radius:8px;
           padding:9px 13px; font-weight:600; cursor:pointer; font-size:13px; }
  button.ghost { background:transparent; color:var(--ink); border:1px solid var(--line); }
  button:disabled { opacity:.5; cursor:not-allowed; }
  .chips { display:flex; gap:6px; flex-wrap:wrap; margin-top:10px; }
  .chip { background:#0c0f13; border:1px solid var(--line); border-radius:20px;
          padding:4px 10px; font-size:12px; display:flex; gap:8px; align-items:center; }
  .chip code { color:var(--accent); }
  .chip .orig { color:var(--mut); max-width:180px; overflow:hidden;
                text-overflow:ellipsis; white-space:nowrap; }
  .chip button { background:transparent; color:var(--bad); padding:0 2px; font-size:14px; }
  .note { font-size:12px; color:var(--mut); margin-top:8px; }
  .sent { white-space:pre-wrap; background:#0c0f13; border:1px dashed var(--line);
          border-radius:8px; padding:10px; font:12px/1.5 ui-monospace,monospace;
          max-height:220px; overflow:auto; }
  .result { white-space:pre-wrap; background:#0c0f13; border:1px solid var(--line);
            border-radius:8px; padding:12px; font:13px/1.6 ui-monospace,monospace;
            min-height:120px; }
  .banner { padding:9px 12px; border-radius:8px; font-size:13px; margin-top:10px; display:none; }
  .banner.warn { background:rgba(246,185,59,.12); border:1px solid var(--warn); color:var(--warn); }
  .banner.ok   { background:rgba(74,222,128,.10); border:1px solid var(--ok); color:var(--ok); }
  .banner.bad  { background:rgba(255,107,107,.10); border:1px solid var(--bad); color:var(--bad); }
  kbd { background:#0c0f13; border:1px solid var(--line); border-radius:4px; padding:0 5px; font-size:11px; }
</style>
</head>
<body>
<header>
  <h1>Resume Adapter &mdash; runs locally</h1>
  <p>Sensitive text you redact is replaced <b>in your browser</b> before anything is sent.
     Only the redacted resume + the job text reach Groq. Originals are restored locally.</p>
</header>

<div class="wrap">
  <div class="panel">
    <h2>1 &middot; Job description (paste text)</h2>
    <textarea id="job" placeholder="Paste the job posting text here. (Pasting text is far more reliable than scraping a link live.)"></textarea>
  </div>

  <div class="panel">
    <h2>2 &middot; Your resume</h2>
    <textarea id="resume" placeholder="Paste your resume text here."></textarea>
    <div class="row">
      <button id="redactBtn" class="ghost" title="Select text in the box above, then click">Redact selected text</button>
      <button id="autoBtn" class="ghost">Auto-detect email &amp; phone</button>
      <button id="clearBtn" class="ghost">Clear redactions</button>
    </div>
    <div class="note">Select your name (or any text) in the box, then <b>Redact selected text</b>.
      Names can&rsquo;t be auto-detected reliably, so highlight those by hand. Email/phone can be auto-detected.</div>
    <div class="chips" id="chips"></div>
  </div>

  <div class="panel">
    <h2>3 &middot; Exactly what will be sent to Groq</h2>
    <div class="sent" id="preview">(redact something to see the outgoing text)</div>
    <div class="row">
      <button id="goBtn">Tailor my resume</button>
    </div>
    <div class="banner warn" id="warnBanner"></div>
    <div class="banner bad" id="errBanner"></div>
  </div>

  <div class="panel">
    <h2>4 &middot; Tailored resume (originals restored)</h2>
    <div class="banner ok" id="okBanner"></div>
    <div class="result" id="result">(result appears here)</div>
    <div class="row">
      <button id="copyBtn" class="ghost">Copy</button>
    </div>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
let map = {};            // { "[[RID_1]]": "John Tan", ... }
let counter = 0;

function nextPh() { counter += 1; return "[[RID_" + counter + "]]"; }

function refreshPreview() {
  $("preview").textContent = $("resume").value || "(empty)";
}

function refreshChips() {
  const c = $("chips"); c.innerHTML = "";
  Object.entries(map).forEach(([ph, orig]) => {
    const el = document.createElement("div");
    el.className = "chip";
    el.innerHTML = '<code>' + ph + '</code> <span class="orig">' +
      orig.replace(/</g,"&lt;") + '</span>';
    const x = document.createElement("button");
    x.textContent = "\u00d7"; x.title = "undo this redaction";
    x.onclick = () => {
      $("resume").value = $("resume").value.split(ph).join(orig);
      delete map[ph]; refreshChips(); refreshPreview();
    };
    el.appendChild(x); c.appendChild(el);
  });
}

$("redactBtn").onclick = () => {
  const ta = $("resume");
  const s = ta.selectionStart, e = ta.selectionEnd;
  if (s === e) { flash("errBanner","Select some text in the resume box first."); return; }
  const orig = ta.value.slice(s, e);
  const ph = nextPh();
  map[ph] = orig;
  ta.value = ta.value.slice(0, s) + ph + ta.value.slice(e);
  refreshChips(); refreshPreview();
};

$("autoBtn").onclick = () => {
  let text = $("resume").value;
  const emailRe = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
  const phoneRe = /(\+65[\s-]?)?[89]\d{3}[\s-]?\d{4}/g;
  const found = [];
  (text.match(emailRe) || []).forEach(m => found.push(m));
  (text.match(phoneRe) || []).forEach(m => found.push(m));
  const uniq = [...new Set(found)].sort((a,b) => b.length - a.length);
  let added = 0;
  uniq.forEach(orig => {
    if (Object.values(map).includes(orig)) return;
    const ph = nextPh(); map[ph] = orig;
    text = text.split(orig).join(ph); added += 1;
  });
  $("resume").value = text;
  refreshChips(); refreshPreview();
  if (!added) flash("warnBanner","No new emails or phone numbers detected.");
};

$("clearBtn").onclick = () => {
  Object.entries(map).forEach(([ph, orig]) => {
    $("resume").value = $("resume").value.split(ph).join(orig);
  });
  map = {}; counter = 0; refreshChips(); refreshPreview();
};

$("resume").addEventListener("input", refreshPreview);

function flash(id, msg) {
  const b = $(id); b.textContent = msg; b.style.display = "block";
  setTimeout(() => { b.style.display = "none"; }, 6000);
}
function hide(id){ $(id).style.display = "none"; }

$("goBtn").onclick = async () => {
  hide("warnBanner"); hide("errBanner"); hide("okBanner");
  const job = $("job").value.trim();
  const resume = $("resume").value.trim();
  if (!job || !resume) { flash("errBanner","Fill in both the job description and the resume."); return; }
  $("goBtn").disabled = true; $("goBtn").textContent = "Contacting Groq...";
  try {
    const res = await fetch("/api/rewrite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job, resume })
    });
    const data = await res.json();
    if (!res.ok) { flash("errBanner", data.error || ("Error " + res.status)); return; }

    let out = data.result || "";
    // verify placeholders survived BEFORE restoring
    const missing = Object.keys(map).filter(ph => !out.includes(ph));
    if (missing.length) {
      const lostItems = missing.map(ph => map[ph]).join(", ");
      flash("warnBanner",
        "Heads up: the model did not return " + missing.length +
        " placeholder(s), so these were NOT auto-restored and may be lost from the "
        + "rewrite: " + lostItems + ". Check the output and add them back by hand.");
    } else {
      $("okBanner").textContent = "All " + Object.keys(map).length +
        " redaction(s) verified and restored locally.";
      $("okBanner").style.display = "block";
    }
    // restore whatever placeholders are present
    Object.entries(map).forEach(([ph, orig]) => { out = out.split(ph).join(orig); });
    $("result").textContent = out;
  } catch (err) {
    flash("errBanner", "Network/local-server error: " + err.message);
  } finally {
    $("goBtn").disabled = false; $("goBtn").textContent = "Tailor my resume";
  }
};

$("copyBtn").onclick = () => {
  navigator.clipboard.writeText($("result").textContent || "");
  flash("okBanner","Copied.");
};
</script>
</body>
</html>"""


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print("Resume Adapter running at http://127.0.0.1:%d" % PORT)
        print("GROQ_API_KEY set:", bool(GROQ_API_KEY), "| model:", MODEL)
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
