#!/usr/bin/env python3

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
    "with placeholder tokens that look like [[RID_1]], [[RID_2]], and so on. You "
    "may also receive a CANDIDATE SELF-ASSESSMENT.\n\n"
    "PLACEHOLDER RULE (critical): Treat every [[RID_n]] token as an opaque, fixed "
    "string. Reproduce each one EXACTLY where it appears. Never modify, translate, "
    "remove, merge, or invent placeholder tokens.\n\n"
    "YOUR TASK: Propose targeted edits so the candidate's genuine, existing "
    "experience is expressed using the terminology and keywords found in the job "
    "description. Do NOT output a full rewritten resume. Return a list of focused "
    "before/after changes the candidate will apply by hand.\n\n"
    "OUTPUT FORMAT (critical): Return ONLY a JSON object of exactly this form, "
    "with no commentary, markdown fences, or text outside the JSON:\n"
    '{"changes": [{"section": "Experience - Acme Corp", '
    '"original": "text copied verbatim from the resume", '
    '"suggested": "the rewritten replacement", '
    '"why": "one short sentence naming the JD keyword this targets"}], '
    '"gaps": ["requirement the job wants but the candidate lacks"]}\n\n'
    "RULES FOR EACH CHANGE:\n"
    "- \"original\" MUST be copied character-for-character from the resume "
    "(including any [[RID_n]] tokens, punctuation, and casing) so it can be "
    "located automatically. Never paraphrase or trim it.\n"
    "- Keep each change small and focused: one bullet point, one sentence, or one "
    "short block. Never more than about 3 lines of the resume per change.\n"
    "- \"suggested\" is the full replacement for that excerpt, keeping every "
    "[[RID_n]] token the excerpt contained.\n"
    "- \"section\" is a short human label for where the excerpt sits (e.g. "
    "'Summary', 'Experience - most recent role', 'Skills').\n"
    "- Propose the 5-15 highest-impact changes; skip parts that need no change.\n"
    "- \"gaps\" lists requirements from the job the candidate does not meet; use "
    "[] if there are none.\n\n"
    "USING THE CANDIDATE SELF-ASSESSMENT (if present): It lists skills the job asks "
    "for, each with the candidate's own rating of their experience. Treat each "
    "rating as a truthful first-person statement by the candidate, and let it guide "
    "emphasis and the gaps list:\n"
    "- 'Experienced / advanced' or 'Working knowledge': you may surface and "
    "emphasize this skill using the job's terminology, even if the resume mentions "
    "it only briefly.\n"
    "- 'Basic - some familiarity': you may mention it modestly and honestly (e.g. "
    "'exposure to'), never as a core strength.\n"
    "- 'No hands-on experience' (or a skill the candidate omitted from the "
    "assessment): do NOT present it as a strength. If the job requires it, put it "
    "in \"gaps\".\n"
    "- The self-assessment adjusts emphasis and the gaps list only. It never "
    "licenses inventing specific projects, employers, dates, tools, certifications, "
    "or metrics. Describe every skill only in the general terms the candidate's own "
    "materials and ratings support.\n\n"
    "INTEGRITY RULES (do not break):\n"
    "- Do NOT invent skills, tools, employers, dates, certifications, degrees, or "
    "achievements that neither the resume nor the self-assessment supports. Only "
    "rephrase and surface what is genuinely present or genuinely claimed.\n"
    "- If the job wants something the candidate lacks, do not fabricate it; put it "
    "in \"gaps\" so the candidate can address it honestly.\n"
    "- Keep all [[RID_n]] placeholders verbatim in both \"original\" and "
    "\"suggested\".\n"
    "- Keep the tone professional and the content truthful."
)

SKILLS_SYSTEM_PROMPT = (
    "You extract the concrete skills, tools, technologies, and qualifications that "
    "a job description asks for. Return ONLY a JSON object of exactly this form:\n"
    '{"skills": ["Python", "AWS", "Stakeholder management"]}\n'
    "Rules: each item is a short label of 1-4 words, not a full sentence; include "
    "the 8-15 most important; no duplicates; no explanations or text outside the "
    "JSON."
)


def groq_chat(messages, temperature=0.3):
    """Generic Groq chat-completions call. Returns the assistant message text."""
    payload = {
        "model": MODEL,
        "temperature": temperature,
        "messages": messages,
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


def format_assessment(skills):
    """Turn [{skill, level}, ...] into a plain-text block, or '' if empty."""
    if not skills:
        return ""
    lines = []
    for item in skills:
        if not isinstance(item, dict):
            continue
        name = (item.get("skill") or "").strip()
        level = (item.get("level") or "").strip()
        if name and level:
            lines.append("- %s: %s" % (name, level))
    if not lines:
        return ""
    return (
        "CANDIDATE SELF-ASSESSMENT (the candidate's own first-person ratings of "
        "their experience with skills this job asks for; treat each as a truthful "
        "statement by the candidate):\n" + "\n".join(lines)
    )


def call_groq(redacted_resume, job_text, skills=None):
    assessment = format_assessment(skills)
    user_parts = ["JOB DESCRIPTION:\n" + job_text]
    if assessment:
        user_parts.append(assessment)
    user_parts.append("RESUME (sensitive parts already redacted):\n" + redacted_resume)
    user_content = "\n\n---\n\n".join(user_parts)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    return groq_chat(messages, temperature=0.3)


def extract_json(text):
    """Best-effort: pull the first JSON object or array out of a text blob."""
    text = (text or "").strip()
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except ValueError:
                continue
    return None


def parse_changes(raw):
    """Turn the model's raw reply into ({changes, gaps}) or None on failure."""
    parsed = extract_json(raw)
    if not isinstance(parsed, dict):
        return None
    raw_changes = parsed.get("changes")
    if not isinstance(raw_changes, list):
        return None
    changes = []
    for ch in raw_changes:
        if not isinstance(ch, dict):
            continue
        original = ch.get("original")
        suggested = ch.get("suggested")
        if not isinstance(original, str) or not isinstance(suggested, str):
            continue
        original, suggested = original.strip("\n"), suggested.strip("\n")
        if not original.strip() or not suggested.strip():
            continue
        if original.strip() == suggested.strip():
            continue
        changes.append({
            "section": str(ch.get("section") or "").strip(),
            "original": original,
            "suggested": suggested,
            "why": str(ch.get("why") or "").strip(),
        })
    gaps_raw = parsed.get("gaps")
    gaps = []
    if isinstance(gaps_raw, list):
        gaps = [g.strip() for g in gaps_raw if isinstance(g, str) and g.strip()]
    if not changes and not gaps:
        return None
    return {"changes": changes, "gaps": gaps}


def extract_skills(job_text):
    messages = [
        {"role": "system", "content": SKILLS_SYSTEM_PROMPT},
        {"role": "user", "content": "JOB DESCRIPTION:\n" + job_text},
    ]
    raw = groq_chat(messages, temperature=0.1)
    parsed = extract_json(raw)
    if isinstance(parsed, dict):
        maybe = parsed.get("skills", [])
    elif isinstance(parsed, list):
        maybe = parsed
    else:
        maybe = []
    skills, seen = [], set()
    for s in maybe:
        if isinstance(s, str):
            label = s.strip()
        elif isinstance(s, dict):
            label = (s.get("skill") or s.get("name") or "").strip()
        else:
            label = ""
        key = label.lower()
        if label and key not in seen:
            seen.add(key)
            skills.append(label)
    return skills[:15]


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, ctype, body_bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def _json(self, code, obj):
        self._send(code, "application/json", json.dumps(obj).encode("utf-8"))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE.encode("utf-8"))
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/skills":
            self.handle_skills()
        elif self.path == "/api/rewrite":
            self.handle_rewrite()
        else:
            self._json(404, {"error": "not found"})

    def handle_skills(self):
        try:
            payload = self._read_body()
            job = payload.get("job", "")
        except (ValueError, TypeError) as exc:
            self._json(400, {"error": "Bad request: %s" % exc})
            return
        if not job.strip():
            self._json(400, {"error": "Please paste the job description first."})
            return
        if not GROQ_API_KEY:
            self._json(500, {"error":
                "GROQ_API_KEY is not set. Set it in your terminal and restart. "
                "See the setup notes at the top of resume_adapter.py."})
            return
        try:
            skills = extract_skills(job)
            self._json(200, {"skills": skills})
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            self._json(502, {"error": "Groq returned HTTP %s. %s" % (exc.code, detail)})
        except Exception as exc:
            self._json(502, {"error": "Call failed: %s" % exc})

    def handle_rewrite(self):
        try:
            payload = self._read_body()
            resume = payload.get("resume", "")
            job = payload.get("job", "")
            skills = payload.get("skills", [])
        except (ValueError, TypeError) as exc:
            self._json(400, {"error": "Bad request: %s" % exc})
            return
        if not resume.strip() or not job.strip():
            self._json(400, {"error": "Please provide both a job description and a resume."})
            return
        if not isinstance(skills, list):
            skills = []
        if not GROQ_API_KEY:
            self._json(500, {"error":
                "GROQ_API_KEY is not set. Set it in your terminal and restart. "
                "See the setup notes at the top of resume_adapter.py."})
            return
        try:
            raw = call_groq(resume, job, skills)
            structured = parse_changes(raw)
            if structured is None:
                # Model ignored the JSON format; let the UI show the raw text.
                self._json(200, {"raw": raw})
            else:
                self._json(200, structured)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            self._json(502, {"error": "Groq returned HTTP %s. %s" % (exc.code, detail)})
        except Exception as exc:
            self._json(502, {"error": "Call failed: %s" % exc})

    def log_message(self, *args):
        return


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
  .skill-row { display:flex; gap:10px; align-items:center; justify-content:space-between;
               background:#0c0f13; border:1px solid var(--line); border-radius:8px;
               padding:8px 10px; margin-top:8px; }
  .skill-row .name { font-size:13px; word-break:break-word; }
  .skill-row select { background:#0c0f13; color:var(--ink); border:1px solid var(--line);
                      border-radius:6px; padding:5px 6px; font-size:12px; min-width:190px; }
  kbd { background:#0c0f13; border:1px solid var(--line); border-radius:4px; padding:0 5px; font-size:11px; }

  /* --- suggestion diff cards --- */
  .change { background:#0c0f13; border:1px solid var(--line); border-radius:10px;
            padding:12px; margin-top:10px; }
  .chead { display:flex; justify-content:space-between; align-items:center;
           gap:10px; flex-wrap:wrap; margin-bottom:4px; }
  .csec { font-size:12px; color:var(--accent); text-transform:uppercase;
          letter-spacing:.04em; font-weight:600; }
  .dlabel { font-size:11px; color:var(--mut); margin:8px 0 3px;
            text-transform:uppercase; letter-spacing:.06em; }
  .dblock { white-space:pre-wrap; word-break:break-word;
            font:13px/1.65 ui-monospace,Menlo,Consolas,monospace;
            border:1px solid var(--line); border-radius:8px; padding:9px 10px; }
  .dblock.old { border-left:3px solid var(--bad); color:var(--mut); }
  .dblock.new { border-left:3px solid var(--ok); }
  .dblock .rm  { background:rgba(255,107,107,.22); color:var(--ink);
                 text-decoration:line-through; border-radius:3px; padding:0 2px; }
  .dblock .add { background:rgba(74,222,128,.18); border-radius:3px; padding:0 2px; }
  .cwhy { font-size:12px; color:var(--mut); margin-top:8px; }
  .cnote { font-size:12px; color:var(--warn); margin-top:8px; }
  .gaps { margin-top:14px; border-top:1px dashed var(--line); padding-top:10px; }
  .gaps h3 { margin:0 0 6px; font-size:12px; color:var(--warn);
             text-transform:uppercase; letter-spacing:.04em; }
  .gaps ul { margin:0; padding-left:18px; font-size:13px; color:var(--mut); }
  .empty { color:var(--mut); font-size:13px; padding:8px 0; }
  details.fullver { margin-top:14px; border:1px solid var(--line);
                    border-radius:10px; background:#0c0f13; }
  details.fullver summary { cursor:pointer; padding:10px 12px; font-size:13px;
                            font-weight:600; color:var(--accent);
                            list-style:none; user-select:none; }
  details.fullver summary::before { content:"\25b8"; display:inline-block;
                                    margin-right:8px; transition:transform .15s; }
  details.fullver[open] summary::before { transform:rotate(90deg); }
  details.fullver summary::-webkit-details-marker { display:none; }
  details.fullver .fbody { padding:0 12px 12px; }
  details.fullver .ftext { white-space:pre-wrap; word-break:break-word;
                           font:13px/1.6 ui-monospace,Menlo,Consolas,monospace;
                           border:1px solid var(--line); border-radius:8px;
                           padding:10px; max-height:420px; overflow:auto; }
</style>
</head>
<body>
<header>
  <h1>Resume Adapter &mdash; runs locally</h1>
  <p>Sensitive text you redact is replaced <b>in your browser</b> before anything is sent.
     Only the redacted resume, the job text, and your skill ratings reach Groq. Originals are restored locally.</p>
</header>

<div class="wrap">
  <div class="panel">
    <h2>1 &middot; Job description (paste text)</h2>
    <textarea id="job" placeholder="Paste the job posting text here. (Pasting text is far more reliable than scraping a link live.)"></textarea>
    <div class="row">
      <button id="skillsBtn" class="ghost">Find required skills &amp; rate yourself</button>
    </div>
    <div class="note">Optional but recommended: pull the skills this job asks for, then rate your
      <b>real</b> experience with each. Your honest ratings steer what gets emphasised and what lands in the gap list.
      Leave a skill on &ldquo;Skip&rdquo; to keep it out entirely.</div>
    <div id="skillsList"></div>
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
    <h2>3 &middot; What leaves your browser (ratings + redacted resume)</h2>
    <div class="sent" id="preview">(redact something to see the outgoing text)</div>
    <div class="note">The job description text is also sent, alongside what you see above.</div>
    <div class="row">
      <button id="goBtn">Suggest edits</button>
    </div>
    <div class="banner warn" id="warnBanner"></div>
    <div class="banner bad" id="errBanner"></div>
  </div>

  <div class="panel">
    <h2>4 &middot; Suggested edits (originals restored)</h2>
    <div class="banner ok" id="okBanner"></div>
    <div id="result"><div class="empty">(suggestions appear here as before/after cards; copy each new version and paste it into your CV yourself)</div></div>
    <div class="row">
      <button id="copyBtn" class="ghost">Copy all new versions</button>
    </div>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
let map = {};
let counter = 0;
let allSuggestions = [];   // restored "new" texts, for the copy-all button

const LEVELS = [
  "Skip - leave this out",
  "No hands-on experience",
  "Basic - some familiarity",
  "Working knowledge",
  "Experienced / advanced"
];
const SKIP = LEVELS[0];
const PH_RE = /\[\[RID_\d+\]\]/g;
const DIFF_WORD_LIMIT = 600;   // skip inline highlighting for huge excerpts

function nextPh() { counter += 1; return "[[RID_" + counter + "]]"; }

function collectSkills() {
  return [...document.querySelectorAll(".skill-row")].map(r => ({
    skill: r.dataset.skill,
    level: r.querySelector("select").value
  }));
}

function assessmentText() {
  const s = collectSkills().filter(x => x.level && x.level !== SKIP);
  if (!s.length) return "";
  return "CANDIDATE SELF-ASSESSMENT:\n" +
    s.map(x => "- " + x.skill + ": " + x.level).join("\n");
}

function refreshPreview() {
  const resume = $("resume").value || "(empty)";
  const a = assessmentText();
  $("preview").textContent = a ? (a + "\n\n---\n\n" + resume) : resume;
}

function renderSkills(skills) {
  const box = $("skillsList");
  box.innerHTML = "";
  skills.forEach(name => {
    const row = document.createElement("div");
    row.className = "skill-row";
    row.dataset.skill = name;
    const label = document.createElement("span");
    label.className = "name";
    label.textContent = name;
    const sel = document.createElement("select");
    LEVELS.forEach(lv => {
      const o = document.createElement("option");
      o.value = lv; o.textContent = lv;
      sel.appendChild(o);
    });
    sel.value = SKIP;
    sel.onchange = refreshPreview;
    row.appendChild(label);
    row.appendChild(sel);
    box.appendChild(row);
  });
  refreshPreview();
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

$("skillsBtn").onclick = async () => {
  hide("warnBanner"); hide("errBanner");
  const job = $("job").value.trim();
  if (!job) { flash("errBanner","Paste the job description first."); return; }
  $("skillsBtn").disabled = true; $("skillsBtn").textContent = "Finding...";
  try {
    const res = await fetch("/api/skills", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job })
    });
    const data = await res.json();
    if (!res.ok) { flash("errBanner", data.error || ("Error " + res.status)); return; }
    const skills = data.skills || [];
    renderSkills(skills);
    if (!skills.length) flash("warnBanner","No skills were detected. You can still tailor without ratings.");
  } catch (err) {
    flash("errBanner","Network/local-server error: " + err.message);
  } finally {
    $("skillsBtn").disabled = false; $("skillsBtn").textContent = "Find required skills & rate yourself";
  }
};

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

/* ---------- restoring placeholders locally ---------- */

function restore(text) {
  let out = text || "";
  Object.entries(map).forEach(([ph, orig]) => { out = out.split(ph).join(orig); });
  return out;
}

/* ---------- word-level diff (LCS) for highlighting ---------- */

function esc(s) {
  return (s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function wordDiff(a, b) {
  const A = a.split(/\s+/).filter(Boolean);
  const B = b.split(/\s+/).filter(Boolean);
  const n = A.length, m = B.length;
  if (n + m > DIFF_WORD_LIMIT) {
    // too big to diff cheaply: mark nothing
    return {
      oldParts: A.map(t => ({ t, changed: false })),
      newParts: B.map(t => ({ t, changed: false }))
    };
  }
  const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = A[i] === B[j] ? dp[i+1][j+1] + 1 : Math.max(dp[i+1][j], dp[i][j+1]);
  const oldParts = [], newParts = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (A[i] === B[j]) {
      oldParts.push({ t: A[i], changed: false });
      newParts.push({ t: B[j], changed: false });
      i++; j++;
    } else if (dp[i+1][j] >= dp[i][j+1]) {
      oldParts.push({ t: A[i], changed: true }); i++;
    } else {
      newParts.push({ t: B[j], changed: true }); j++;
    }
  }
  while (i < n) oldParts.push({ t: A[i++], changed: true });
  while (j < m) newParts.push({ t: B[j++], changed: true });
  return { oldParts, newParts };
}

function partsToHtml(parts, cls) {
  return parts.map(p =>
    p.changed ? '<span class="' + cls + '">' + esc(p.t) + '</span>' : esc(p.t)
  ).join(" ");
}

/* ---------- rendering the suggestion cards ---------- */

function copyButton(text, label) {
  const btn = document.createElement("button");
  btn.textContent = label || "Copy new text";
  btn.onclick = () => {
    navigator.clipboard.writeText(text);
    const prev = btn.textContent;
    btn.textContent = "Copied \u2713";
    setTimeout(() => { btn.textContent = prev; }, 1500);
  };
  return btn;
}

function renderOutput(data) {
  const box = $("result");
  box.innerHTML = "";
  allSuggestions = [];

  // Fallback: model ignored the JSON format, show restored raw text.
  if (data.raw !== undefined) {
    const missing = Object.keys(map).filter(ph => !(data.raw || "").includes(ph));
    if (missing.length) {
      flash("warnBanner",
        "Heads up: the model did not return " + missing.length +
        " placeholder(s), so these may be missing from the text: " +
        missing.map(ph => map[ph]).join(", "));
    }
    flash("warnBanner",
      "The model didn't return structured edits this time, so here's its raw reply. Try again for before/after cards.");
    const div = document.createElement("div");
    div.className = "result";
    div.textContent = restore(data.raw);
    box.appendChild(div);
    allSuggestions = [restore(data.raw)];
    return;
  }

  const changes = data.changes || [];
  const gaps = data.gaps || [];
  const resumeNow = $("resume").value;

  if (!changes.length) {
    const div = document.createElement("div");
    div.className = "empty";
    div.textContent = "No changes were suggested.";
    box.appendChild(div);
  }

  changes.forEach((ch, idx) => {
    const oldRestored = restore(ch.original);
    const newRestored = restore(ch.suggested);
    allSuggestions.push({
      section: ch.section || ("Change " + (idx + 1)),
      oldText: oldRestored,
      newText: newRestored
    });

    const card = document.createElement("div");
    card.className = "change";

    const head = document.createElement("div");
    head.className = "chead";
    const sec = document.createElement("span");
    sec.className = "csec";
    sec.textContent = ch.section || ("Change " + (idx + 1));
    head.appendChild(sec);
    head.appendChild(copyButton(newRestored));
    card.appendChild(head);

    const diff = wordDiff(oldRestored, newRestored);

    const lo = document.createElement("div");
    lo.className = "dlabel"; lo.textContent = "Current";
    card.appendChild(lo);
    const ob = document.createElement("div");
    ob.className = "dblock old";
    ob.innerHTML = partsToHtml(diff.oldParts, "rm");
    card.appendChild(ob);

    const ln = document.createElement("div");
    ln.className = "dlabel"; ln.textContent = "Suggested";
    card.appendChild(ln);
    const nb = document.createElement("div");
    nb.className = "dblock new";
    nb.innerHTML = partsToHtml(diff.newParts, "add");
    card.appendChild(nb);

    if (ch.why) {
      const why = document.createElement("div");
      why.className = "cwhy";
      why.textContent = "Why: " + ch.why;
      card.appendChild(why);
    }

    const notes = [];
    if (!resumeNow.includes(ch.original)) {
      notes.push("Couldn't find the \u201ccurrent\u201d text verbatim in your resume box \u2014 the model may have paraphrased it. Double-check before replacing.");
    }
    const dropped = (ch.original.match(PH_RE) || []).filter(ph => !ch.suggested.includes(ph));
    if (dropped.length) {
      notes.push("This suggestion dropped redacted detail(s): " +
        dropped.map(ph => map[ph] || ph).join(", ") + ". Add them back by hand if you use it.");
    }
    notes.forEach(msg => {
      const n = document.createElement("div");
      n.className = "cnote";
      n.textContent = "\u26a0 " + msg;
      card.appendChild(n);
    });

    box.appendChild(card);
  });

  // ----- complete tailored version (all locatable edits applied) -----
  if (changes.length) {
    let full = resumeNow;
    const unapplied = [];
    changes.forEach((ch, idx) => {
      const at = full.indexOf(ch.original);
      if (at === -1) {
        unapplied.push(ch.section || ("Change " + (idx + 1)));
        return;
      }
      full = full.slice(0, at) + ch.suggested + full.slice(at + ch.original.length);
    });
    const fullRestored = restore(full);

    const det = document.createElement("details");
    det.className = "fullver";
    const sum = document.createElement("summary");
    sum.textContent = "Complete tailored resume (all edits applied)";
    det.appendChild(sum);

    const body = document.createElement("div");
    body.className = "fbody";
    if (unapplied.length) {
      const n = document.createElement("div");
      n.className = "cnote";
      n.style.marginBottom = "8px";
      n.textContent = "\u26a0 " + unapplied.length +
        " edit(s) couldn't be applied automatically (their \u201ccurrent\u201d text wasn't found verbatim): " +
        unapplied.join(", ") + ". Apply those by hand from the cards above.";
      body.appendChild(n);
    }
    const txt = document.createElement("div");
    txt.className = "ftext";
    txt.textContent = fullRestored;
    body.appendChild(txt);
    const row = document.createElement("div");
    row.className = "row";
    row.appendChild(copyButton(fullRestored, "Copy complete version"));
    body.appendChild(row);
    det.appendChild(body);
    box.appendChild(det);
  }

  if (gaps.length) {
    const g = document.createElement("div");
    g.className = "gaps";
    const h = document.createElement("h3");
    h.textContent = "Gaps to consider";
    g.appendChild(h);
    const ul = document.createElement("ul");
    gaps.forEach(gap => {
      const li = document.createElement("li");
      li.textContent = gap;
      ul.appendChild(li);
    });
    g.appendChild(ul);
    box.appendChild(g);
  }

  if (changes.length) {
    $("okBanner").textContent = changes.length +
      " suggestion(s) ready. Redactions were restored locally \u2014 nothing sensitive left your browser.";
    $("okBanner").style.display = "block";
  }
}

$("goBtn").onclick = async () => {
  hide("warnBanner"); hide("errBanner"); hide("okBanner");
  const job = $("job").value.trim();
  const resume = $("resume").value.trim();
  if (!job || !resume) { flash("errBanner","Fill in both the job description and the resume."); return; }
  const skills = collectSkills().filter(x => x.level && x.level !== SKIP);
  $("goBtn").disabled = true; $("goBtn").textContent = "Contacting Groq...";
  try {
    const res = await fetch("/api/rewrite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job, resume, skills })
    });
    const data = await res.json();
    if (!res.ok) { flash("errBanner", data.error || ("Error " + res.status)); return; }
    renderOutput(data);
  } catch (err) {
    flash("errBanner", "Network/local-server error: " + err.message);
  } finally {
    $("goBtn").disabled = false; $("goBtn").textContent = "Suggest edits";
  }
};

$("copyBtn").onclick = () => {
  if (!allSuggestions.length) { flash("warnBanner","Nothing to copy yet."); return; }
  let text;
  if (typeof allSuggestions[0] === "string") {
    text = allSuggestions[0];
  } else {
    text = allSuggestions.map(s =>
      "## " + s.section + "\nOLD: " + s.oldText + "\nNEW: " + s.newText
    ).join("\n\n");
  }
  navigator.clipboard.writeText(text);
  flash("okBanner","Copied all suggestions.");
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