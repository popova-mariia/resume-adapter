import gzip
import urllib.request
import urllib.error
from html.parser import HTMLParser


# ---------- fetching a job posting from a URL (best-effort) ----------

MAX_FETCH_BYTES = 3_000_000      # don't slurp more than ~3 MB of HTML
MAX_JOB_CHARS = 20_000           # cap the text we hand back to the UI

BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "*/*;q=0.8"),
    "Accept-Language": "en;q=0.9",
    "Accept-Encoding": "gzip, identity",
}


class _TextExtractor(HTMLParser):
    """Very small HTML -> visible-text converter (no third-party deps)."""

    SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head",
                 "iframe", "nav", "form", "button"}
    BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer",
                  "main", "aside", "li", "ul", "ol", "table", "tr", "td",
                  "th", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
                  "blockquote", "pre", "dt", "dd"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(html_text):
    parser = _TextExtractor()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:
        pass  # keep whatever was extracted before the parser choked
    text = "".join(parser.parts)
    lines = [" ".join(ln.split()) for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def fetch_job_page(url):
    """Fetch a URL and return the page's visible text. Raises ValueError with a
    user-facing message when the page can't be fetched or yields no usable text."""
    url = (url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("The link must start with http:// or https://.")
    req = urllib.request.Request(url)
    for key, val in BROWSER_HEADERS.items():
        req.add_header(key, val)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read(MAX_FETCH_BYTES)
            encoding = (resp.headers.get("Content-Encoding") or "").lower()
            ctype = (resp.headers.get("Content-Type") or "").lower()
            final_url = resp.geturl().lower()  # where we landed after redirects
    except urllib.error.HTTPError as exc:
        raise ValueError(
            "The site answered with HTTP %s. Many job boards block automated "
            "fetches - please copy the posting text and paste it instead." % exc.code)
    except Exception as exc:
        raise ValueError(
            "Couldn't reach that link (%s). Check the URL, or copy the posting "
            "text and paste it instead." % exc)
    if "gzip" in encoding:
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    if ctype and ("html" not in ctype and "text" not in ctype):
        raise ValueError(
            "That link isn't an HTML page (server says '%s'). Please paste the "
            "posting text instead." % ctype.split(";")[0])
    charset = "utf-8"
    if "charset=" in ctype:
        charset = ctype.split("charset=")[-1].split(";")[0].strip() or "utf-8"
    try:
        html_text = raw.decode(charset, "replace")
    except LookupError:
        html_text = raw.decode("utf-8", "replace")
    text = html_to_text(html_text)
    # Detect login walls (e.g. LinkedIn's authwall): signal 1 is the URL we were
    # redirected to; signal 2 is a fallback requiring >=2 login-page phrases in
    # the text, so a job page that merely mentions "sign in" once isn't rejected.
    wall = any(k in final_url for k in ("authwall", "login", "signin", "checkpoint"))
    if not wall:
        markers = ("sign in", "join now", "forgot password", "keep me signed in")
        wall = sum(1 for m in markers if m in text.lower()) >= 2
    if wall:
        raise ValueError(
            "The site returned a login page instead of the posting (LinkedIn and "
            "similar boards require sign-in). Please copy the posting text and "
            "paste it instead.")
    if len(text) < 200:
        raise ValueError(
            "The page returned almost no readable text - it's probably rendered "
            "with JavaScript or behind a login (common on LinkedIn, Workday, "
            "etc.). Please copy the posting text and paste it instead.")
    if len(text) > MAX_JOB_CHARS:
        text = text[:MAX_JOB_CHARS] + "\n\n[... page text truncated ...]"
    return text
