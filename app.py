#!/usr/bin/env python3

import http.server
import json
import os
import socketserver
import urllib.error

from groq_client import (
    GROQ_API_KEY,
    MODEL,
    call_groq,
    clean_job_text,
    extract_skills,
    parse_changes,
)
from job_fetcher import fetch_job_page
from page import PAGE

PORT = int(os.environ.get("PORT", "8765"))


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
        elif self.path == "/api/fetch_job":
            self.handle_fetch_job()
        else:
            self._json(404, {"error": "not found"})

    def handle_fetch_job(self):
        try:
            payload = self._read_body()
            url = payload.get("url", "")
        except (ValueError, TypeError) as exc:
            self._json(400, {"error": "Bad request: %s" % exc})
            return
        if not (url or "").strip():
            self._json(400, {"error": "Paste a link to the job posting first."})
            return
        try:
            text = fetch_job_page(url)
        except ValueError as exc:
            self._json(422, {"error": str(exc)})
            return
        except Exception as exc:
            self._json(502, {"error":
                "Fetching failed: %s. Please paste the posting text instead." % exc})
            return
        # Second pass: ask Groq to strip menus/footers so the later skills and
        # rewrite calls see only the posting. Any failure falls back to the raw
        # scrape - this step must never make fetching worse.
        if not GROQ_API_KEY:
            self._json(200, {"text": text, "cleaned": False,
                             "note": "GROQ_API_KEY not set, so no AI clean-up was done"})
            return
        try:
            cleaned = clean_job_text(text)
            self._json(200, {"text": cleaned, "cleaned": True,
                             "raw_chars": len(text), "clean_chars": len(cleaned)})
        except Exception as exc:
            self._json(200, {"text": text, "cleaned": False,
                             "note": "AI clean-up failed (%s)" % exc})

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


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print("Resume Adapter running at http://127.0.0.1:%d" % PORT)
        print("GROQ_API_KEY set:", bool(GROQ_API_KEY), "| model:", MODEL)
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
