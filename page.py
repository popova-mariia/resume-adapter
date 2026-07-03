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
  input[type="url"] { flex:1 1 220px; min-width:0; background:#0c0f13; color:var(--ink);
                      border:1px solid var(--line); border-radius:8px; padding:9px 10px;
                      font:13px/1.5 ui-monospace,Menlo,Consolas,monospace; }
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

  /* --- confirm modal --- */
  .modal-back { position:fixed; inset:0; display:none; align-items:center;
                justify-content:center; background:rgba(5,8,12,.66);
                backdrop-filter:blur(2px); z-index:50; }
  .modal-back.open { display:flex; }
  .modal { background:var(--panel); border:1px solid var(--line);
           border-radius:12px; padding:18px;
           width:min(440px, calc(100vw - 40px));
           box-shadow:0 18px 50px rgba(0,0,0,.5); }
  .modal h3 { margin:0 0 8px; font-size:15px; }
  .modal p { margin:0 0 14px; color:var(--mut); font-size:13px; line-height:1.5; }
  .modal .row { justify-content:flex-end; margin-top:0; }
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
    <h2>1 &middot; Job description (paste text or fetch from a link)</h2>
    <div class="row" style="margin-top:0; margin-bottom:8px;">
      <input type="url" id="jobUrl" placeholder="https://... link to the job posting (optional)">
      <button id="fetchBtn" class="ghost">Fetch from link</button>
    </div>
    <div class="note" style="margin-top:0; margin-bottom:8px;">Fetching from a link is best-effort:
      many job boards (LinkedIn, Workday, sites that need login or JavaScript) will return an error
      or junk. If that happens, just copy the posting text and paste it below &mdash; pasting always works.
      Note: fetched page text is sent to Groq once for automatic clean-up (menus/footers stripped).</div>
    <textarea id="job" placeholder="Paste the job posting text here, or use the link fetcher above."></textarea>
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

<div class="modal-back" id="modalBack" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
  <div class="modal">
    <h3 id="modalTitle">Replace job description?</h3>
    <p id="modalMsg"></p>
    <div class="row">
      <button class="ghost" id="modalCancel">Cancel</button>
      <button id="modalOk">Replace text</button>
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

$("fetchBtn").onclick = async () => {
  hide("warnBanner"); hide("errBanner");
  const url = $("jobUrl").value.trim();
  if (!url) { flash("errBanner","Paste a link to the job posting first."); return; }
  if ($("job").value.trim() &&
      !(await askConfirm("Fetching will replace the text currently in the job description box. This can't be undone.",
                         "Replace job description?", "Replace text"))) {
    return;
  }
  $("fetchBtn").disabled = true; $("fetchBtn").textContent = "Fetching & cleaning...";
  try {
    const res = await fetch("/api/fetch_job", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    if (!res.ok) {
      flash("errBanner", (data.error || ("Error " + res.status)) +
        " Tip: paste the job text into the box instead.");
      return;
    }
    $("job").value = data.text || "";
    if (data.cleaned) {
      const stripped = Math.max(0, (data.raw_chars || 0) - (data.clean_chars || 0));
      flash("okBanner",
        "Fetched " + (data.raw_chars || "?") + " characters and stripped ~" + stripped +
        " characters of menus, footers and other page junk. Clean-up can occasionally drop parts " +
        "of the posting \u2014 please skim the box against the original page.", 10000);
    } else {
      flash("warnBanner",
        "Fetched " + ($("job").value.length) + " characters of raw page text" +
        (data.note ? " (" + data.note + ")" : "") + ". Scraped pages often include " +
        "menus/footers or miss parts of the posting \u2014 please skim the box and tidy it up before continuing.", 10000);
    }
  } catch (err) {
    flash("errBanner","Network/local-server error: " + err.message +
      " \u2014 paste the job text instead.");
  } finally {
    $("fetchBtn").disabled = false; $("fetchBtn").textContent = "Fetch from link";
  }
};

$("jobUrl").addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); $("fetchBtn").click(); }
});

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

function flash(id, msg, ms) {
  const b = $(id); b.textContent = msg; b.style.display = "block";
  setTimeout(() => { b.style.display = "none"; }, ms || 6000);
}
function hide(id){ $(id).style.display = "none"; }

/* Promise-based replacement for confirm(): resolves true (OK button) / false
   (Cancel, Escape, or backdrop click). title and okLabel are optional. */
function askConfirm(msg, title, okLabel) {
  return new Promise(resolve => {
    const back = $("modalBack");
    $("modalTitle").textContent = title || "Are you sure?";
    $("modalMsg").textContent = msg;
    $("modalOk").textContent = okLabel || "Continue";
    const done = val => {
      back.classList.remove("open");
      document.removeEventListener("keydown", onKey);
      back.onclick = null;
      resolve(val);
    };
    const onKey = e => { if (e.key === "Escape") done(false); };
    $("modalOk").onclick = () => done(true);
    $("modalCancel").onclick = () => done(false);
    back.onclick = e => { if (e.target === back) done(false); };
    document.addEventListener("keydown", onKey);
    back.classList.add("open");
    $("modalCancel").focus();
  });
}

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
  const nRed = Object.keys(map).length;
  const privacyMsg = nRed
    ? "Your resume (with " + nRed + " redaction" + (nRed === 1 ? "" : "s") +
      " applied), the job description, and your skill ratings are about to be sent to Groq. " +
      "Are you sure the remaining text contains no sensitive info you'd rather redact first? " +
      "Panel 3 shows exactly what will leave your browser."
    : "You haven't redacted anything. Your FULL resume, the job description, and your skill " +
      "ratings are about to be sent to Groq. Are you sure it contains no sensitive info " +
      "(name, email, phone, address)? You can select text in the resume box and click " +
      "\u201cRedact selected text\u201d first \u2014 panel 3 shows exactly what will leave your browser.";
  if (!(await askConfirm(privacyMsg, "Send to Groq?", "Send to Groq"))) return;
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
