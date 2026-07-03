import json
import os
import urllib.request
import urllib.error

from prompts import SYSTEM_PROMPT, SKILLS_SYSTEM_PROMPT, CLEAN_SYSTEM_PROMPT

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


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

def clean_job_text(raw_text):
    """Second-pass Groq call: strip scraped-page clutter (menus, footers, cookie
    banners) so only the posting remains. Returns the cleaned text, or raises
    ValueError when the reply is unusable; the caller falls back to raw_text."""
    messages = [
        {"role": "system", "content": CLEAN_SYSTEM_PROMPT},
        {"role": "user", "content": "SCRAPED PAGE TEXT:\n" + raw_text},
    ]
    cleaned = (groq_chat(messages, temperature=0.0) or "").strip()
    if cleaned.startswith("```"):          # tolerate accidental markdown fences
        first_nl = cleaned.find("\n")
        if first_nl != -1:
            cleaned = cleaned[first_nl + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    if "NO_JOB_POSTING_FOUND" in cleaned[:80]:
        raise ValueError("the model found no job posting in the page text")
    if len(cleaned) < 200:
        raise ValueError("the cleaned text came back suspiciously short")
    if len(cleaned) > len(raw_text):
        raise ValueError("the cleaned text grew - the model may have added "
                         "content, so it can't be trusted")
    return cleaned
