#!/usr/bin/env python3
"""cited: a local knowledge base you learn from (claims → tags → packets → brief).

Transcripts stay the source. Cards feed the claim index. You accept tags.
Packets and brief are how you sit back down with one question.
Rebuild the index with `cited.py reindex`.

  cited.py corpus [--drift]
  cited.py claims "question" [--kind claim]
  cited.py mine propose|walk|stats
  cited.py packet list|refresh|show
  cited.py brief PACKET
  cited.py grow [--episode ID]
  cited.py search|show|cards|pod|add …
"""
from __future__ import annotations

import argparse
import html
import json
import email.utils
import hashlib
import os
import random
import re
import shutil
import ssl
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import sqlite3
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(os.environ.get("CITED_HOME") or Path(__file__).resolve().parent)
TDIR = ROOT / "transcripts"
CDIR = ROOT / "cards"
FIXTURE = ROOT / "examples" / "fixture"
DB_PATH = ROOT / "cited.sqlite"
CHUNK_SEC = 60  # one paragraph (= one search hit) per ~minute of talk

# ---------------------------------------------------------------- helpers

def fmt_ts(sec) -> str:
    sec = int(float(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_ts(ts: str) -> int:
    sec = 0.0
    for part in ts.strip().split(":"):
        sec = sec * 60 + float(part)
    return int(sec)


def slug(s: str, n: int) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:n].strip("-") or "x"


YT_ID = re.compile(r"(?:v=|youtu\.be/|shorts/|live/|embed/)([A-Za-z0-9_-]{11})")
NOISE = re.compile(r"\[(?:music|applause|laughter|musik|applaus|gelächter|lachen)\]", re.I)

# ---------------------------------------------------------------- captions

def parse_json3(raw: str):
    """YouTube json3 captions -> [(start_sec, text)]. No rolling duplicates."""
    out = []
    for ev in json.loads(raw).get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        t = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if t:
            out.append((ev.get("tStartMs", 0) / 1000, t))
    return out


_TAG = re.compile(r"<[^>]+>")


def parse_vtt(raw: str):
    """WebVTT -> [(start_sec, text)], dropping the repeated lines of rolling auto-captions."""
    out, last = [], None
    for block in re.split(r"\n\s*\n", raw.replace("\r", "")):
        lines = block.strip().split("\n")
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            continue
        start = parse_ts(lines[idx].split("-->")[0].strip().replace(",", "."))
        for l in lines[idx + 1:]:
            l = html.unescape(_TAG.sub("", l)).strip()
            if l and l != last:
                out.append((start, l))
                last = l
    return out


def chunk(segs, size=CHUNK_SEC):
    """Merge caption segments into ~size-second paragraphs, preferring sentence ends."""
    chunks, cur, start = [], [], None
    for t, txt in segs:
        txt = NOISE.sub("", txt).strip()
        if not txt:
            continue
        if start is None:
            start = t
        cur.append(txt)
        span = t - start
        if span >= size and (re.search(r"[.!?…][\"')]?$", txt) or span >= size * 1.5):
            chunks.append((start, " ".join(cur)))
            cur, start = [], None
    if cur:
        chunks.append((start, " ".join(cur)))
    return [(s, re.sub(r"\s+", " ", x).strip()) for s, x in chunks]


def pick_track(info, langs):
    """Prefer human captions in a preferred language, else the auto captions in the
    video's original language (not a machine translation)."""
    manual = {k: v for k, v in (info.get("subtitles") or {}).items() if k != "live_chat"}
    auto = info.get("automatic_captions") or {}

    def find(d, want):
        for w in want:
            for k in d:
                if k == w or k.startswith(w + "-"):
                    return k

    k = find(manual, langs)
    if k:
        return k, manual[k], "manual"
    # Auto captions: "<lang>-orig" is speech recognition in that language. Channels with
    # multi-language audio can carry several "-orig" tracks, so match preferred languages
    # first and never just take the first track in the dict.
    for w in langs + ([info["language"]] if info.get("language") else []):
        if f"{w}-orig" in auto:
            return w, auto[f"{w}-orig"], "auto"
    lang = info.get("language")
    if lang and lang in auto:
        return lang, auto[lang], "auto"
    k = find(auto, langs)  # last resort: may be a machine translation
    if k:
        return k, auto[k], "auto"
    orig = sorted(k for k in auto if k.endswith("-orig"))
    if orig:
        return orig[0][:-5], auto[orig[0]], "auto"
    return None


class Blocked(RuntimeError):
    """YouTube is rate-limiting / blocking this IP."""


BLOCK_MARKERS = ("429", "Too Many Requests", "blocking requests from your IP",
                 "IpBlocked", "RequestBlocked", "not a bot")


def is_block(msg: str) -> bool:
    return any(m in msg for m in BLOCK_MARKERS)


def first_line(e) -> str:
    return next((l.strip() for l in str(e).splitlines() if l.strip()), repr(e))[:160]


def fetch_fallback(vid, langs, cookiejar=None):
    """Second route via youtube-transcript-api (optional dependency)."""
    from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
    session = None
    if cookiejar is not None:
        import requests  # installed with youtube-transcript-api
        session = requests.Session()
        for ck in cookiejar:
            session.cookies.set_cookie(ck)
    api = YouTubeTranscriptApi(http_client=session) if session else YouTubeTranscriptApi()
    t = api.fetch(vid, languages=list(dict.fromkeys(langs + ["en"])))
    segs = [(s.start, s.text.replace("\n", " ")) for s in t]
    return t.language_code, segs, "auto" if t.is_generated else "manual"

# ---------------------------------------------------------------- storage

META_KEYS = ("guest", "role", "company")


def db():
    TDIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)  # timeout: a parallel `cited pod` run may hold the lock
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS videos(
          id TEXT PRIMARY KEY, title TEXT, channel TEXT, date TEXT, duration TEXT,
          url TEXT, lang TEXT, captions TEXT, tags TEXT, path TEXT, words INT);
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
          text, video_id UNINDEXED, start UNINDEXED,
          tokenize='porter unicode61 remove_diacritics 2');
        CREATE TABLE IF NOT EXISTS cards(
          id TEXT PRIMARY KEY, format TEXT, sponsored TEXT, vendor_guest TEXT,
          ai_stance TEXT, topics TEXT, summary TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS cardtext USING fts5(
          text, video_id UNINDEXED, tokenize='porter unicode61 remove_diacritics 2');
        CREATE TABLE IF NOT EXISTS claims(
          id TEXT PRIMARY KEY, video_id TEXT, kind TEXT, at TEXT, start INT,
          text TEXT, speaker TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS claimtext USING fts5(
          text, claim_id UNINDEXED, video_id UNINDEXED,
          tokenize='porter unicode61 remove_diacritics 2');
        """
    )
    cols = {r[1] for r in c.execute("PRAGMA table_info(videos)")}
    for k in META_KEYS:  # migrate indexes created by earlier versions
        if k not in cols:
            c.execute(f"ALTER TABLE videos ADD COLUMN {k} TEXT")
    return c

# ---------------------------------------------------------------- guest metadata

_TRIG = re.compile(r"(?:sits? down with|sat down with|conversation with|spoke with|speaks? with|speak with|"
                   r"joined by|we welcome|welcomed|welcome|\bjoin|chat(?:ted)? with|talk(?:ed|s)? (?:with|to)|"
                   r"my guest(?: on this episode)? is|interview(?:ed)?|podcast(?: on the road)?,)\s+"
                   r"(?:the\s+)?(?:(?:returning|special|guest)\s+)*(?:guest\s+)?", re.I)
_CRED = re.compile(r"^(?:\s*,?\s*(?:MBA|PhD|Ph\.D\.|MSc|MA|BA|CPA|Jr\.|Sr\.)"
                   r"|\s*\([^)]*\))+")
_END = re.compile(r",\s*(?:to|about|who|where|on|as|in|around)\b"
                  r"|,\s*(?:discuss|share|explore|explain|join|reveal|unpack|talk|open|break|walk|reflect|dive)\w*\b"
                  r"|\.(?:\s|$)|\s+about\b|\s+to\s+(?:discuss|explore|unpack|talk|share)")
_NAME = re.compile(r"((?:Dr\.|Prof\.)?\s*[A-Z][\w'’\-]*"
                   r"(?:\s+(?:[A-Z][\w'’\-]*\.?|de|van|von|da|di|del|la|le))*)")


_JOINS = re.compile(r"([A-Z][\w.'’\-]*(?:\s+(?:[A-Z][\w.'’\-]*|de|van|von|da|di|del|la|le)){1,4})"
                    r"((?:,(?:[^.]|\.(?=\S))*?)?)\s+(?:joins?|sits? down with)\s+(?:guest host|host|us|the show)")


def _split_role(seg: str):
    """'VP of Product at Amazon' -> (VP of Product, Amazon); 'founder of X' -> (founder, X)."""
    seg = seg.strip(" ,")
    pos = re.match(r"^([A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*)*)[’']s\s+(.+)$", seg)
    if " at " not in seg and pos:  # "Acme's chief transformation officer"
        return pos.group(2).strip(" ,")[:120], pos.group(1)[:80]
    seg = re.split(r"\s+(?:During our conversation|In this episode|In our conversation)\b", seg)[0].strip(" ,")
    if re.match(r"(?i)(?:best-?selling\s+)?(?:co-)?author of\b", seg):
        return seg[:120], ""
    if " at " in seg:
        role, company = seg.rsplit(" at ", 1)
    else:
        m = re.search(r"\s(?:of|for|to)\s", seg)
        left = seg[:m.start()] if m else ""
        if m and re.search(r"(?i)\b(?:founder|ceo|cpo|chro|cto|coo|director|head|vp|svp|evp|chief|management|president|officer|"
                           r"advisor|partner|lead|manager|consultant|professor|lecturer|chair|member|"
                           r"executive|principal|dean)\b", left):
            role, company = left, seg[m.end():]
        else:
            role, company = seg, ""
    company = re.split(r"\s+and\s+(?=[a-z])", company)[0].strip(" ,")
    return role.strip(" ,")[:120], company[:80]


def _after_name(name: str, rest: str) -> dict:
    rest = _CRED.sub("", rest)
    m = re.match(r"\s+(?:of|from)\s+([A-Z][^,.]*?)(?=\s+(?:to|about|on|in|as|who)\b|[,.]|$)", rest)
    if m:  # "Amy Schultz of DTE Energy to explore ..."
        return {"guest": name, "role": "", "company": m.group(1).strip()}
    if not rest.startswith(","):
        return {"guest": name}
    seg = rest[1:]
    e = _END.search(seg)
    role, company = _split_role(seg[:e.start()] if e else seg)
    return {"guest": name, "role": role, "company": company}


_NOT_A_GUEST = re.compile(r"Community|Podcast|Leaders|Episode", re.I)
_ROLE_WORDS = {"People", "Consultant", "Coach", "Founder", "CEO", "Author", "Director", "Officer",
               "Advisor", "Expert", "Leader", "Manager", "Partner", "President", "VP", "Head"}
_ARTICLES = {"The", "A", "An", "This", "Our", "My", "In", "When", "How", "Why", "What"}
_SENT_NAME = (r"(?:^|[.?!]\s+)((?:Dr\.\s+)?[A-Z][\w.'’\-]+(?:\s+[A-Z][\w.'’\-]+){1,3})")


def _clean_name(name: str) -> str:
    toks = name.split()
    idx = [i for i, t in enumerate(toks) if t in _ROLE_WORDS]
    if idx and len(toks) - (idx[-1] + 1) >= 2:  # "People Consultant Charlotte Goulding"
        toks = toks[idx[-1] + 1:]
    return " ".join(toks)


def _ok_name(name: str) -> bool:
    toks = name.split()
    return len(toks) >= 2 and toks[0] not in _ARTICLES and not _NOT_A_GUEST.search(name)


def extract_guest(text: str) -> dict:
    """Guest, role and company from show notes. Handles 'we sit down with Jane Doe, CPO at
    Acme, to ...', 'Jane Doe, CPO at Acme, joins the host / sits down with the host ...',
    'My guest on this episode is Jane Doe, ...', 'Jane Doe, CPO at Acme, discusses ...',
    'Jane Doe is CPO at Acme', 'Jane Doe of Acme', "Acme's CPO", solo episodes, panels."""
    text = re.sub(r"\s*[—–]\s*", ", ", text or "")
    if re.search(r"\bsolo episode\b", text, re.I):
        return {"guest": "Host (solo)"}
    g = {}
    m = _JOINS.search(text)
    if m and _ok_name(_clean_name(m.group(1).strip())):
        g = _after_name(_clean_name(m.group(1).strip()), m.group(2))
    if not g:
        for t in _TRIG.finditer(text):
            nm = _NAME.match(text[t.end():])
            if nm and _ok_name(_clean_name(nm.group(1).strip())):
                g = _after_name(_clean_name(nm.group(1).strip()), text[t.end() + nm.end():])
                break
    if not g:  # "Hannah Toney, consultant at X and author, discusses ..."
        for m in re.finditer(_SENT_NAME + r",\s((?:[^.]|\.(?=\S))*?),\s+(?:discusses|shares|explains|explores|unpacks|"
                             r"talks|reveals|walks|joins|sits)", text):
            if _ok_name(m.group(1)):
                role, company = _split_role(m.group(2))
                g = {"guest": m.group(1), "role": role, "company": company}
                break
    if not g:  # "Gemma Versace is Chief Client Officer at X-Team"
        for m in re.finditer(_SENT_NAME + r" is (?:the |a |an )?([^.]*?\bat\s+[A-Z][^.,]*)", text):
            if _ok_name(m.group(1)):
                role, company = _split_role(m.group(2))
                g = {"guest": m.group(1), "role": role, "company": company}
                break
    if not g:  # "Dr. Dafna Aaronson says ..."
        for m in re.finditer(_SENT_NAME + r" (?:says|argues|believes|explains|thinks)\b", text):
            if _ok_name(m.group(1)):
                g = {"guest": m.group(1)}
                break
    if g and not g.get("company"):  # "Gina is Chief People Officer ... at SAP."
        first = re.escape(re.sub(r"^(?:Dr|Prof)\.\s*", "", g["guest"]).split()[0])
        rs = re.search(rf"\b{first} is (?:the |a |an )?([^.]*?)\.", text)
        if rs:
            role, company = _split_role(rs.group(1))
            if company:
                g.update(role=role, company=company)
    if g:
        return g
    pm = re.search(r"leaders from ([A-Z][^.]*?)\s+(?:to|as|on|in)\s+[a-z]", text)
    if pm:
        return {"guest": "Panel", "role": "", "company": pm.group(1).strip()[:80]}
    if re.search(r"\bpanel\b", text, re.I):
        return {"guest": "Panel"}
    return {}


def guest_from_title(title: str) -> dict:
    """Fallback: '... with Jane Doe', '... with Jane Doe & John Roe, co-authors of X',
    '307: The Engineer Who Won't Use AI with Andrew Norcross'."""
    t = re.sub(r"[“”\"]", "", title or "")
    m = re.search(r"\bwith\s+((?:Dr\.\s+)?[A-Z][\w.'’\-]+(?:\s+[A-Z][\w.'’\-]+){1,3}"
                  r"(?:\s*(?:&|and)\s*(?:Dr\.\s+)?[A-Z][\w.'’\-]+(?:\s+[A-Z][\w.'’\-]+){1,3})?)"
                  r"\s*(?:,\s*(.+))?$", t)
    if not m or not _ok_name(m.group(1).split(" & ")[0].split(" and ")[0]):
        return {}
    g = {"guest": m.group(1).strip()}
    if m.group(2):
        role, company = _split_role(m.group(2))
        g.update(role=role, company=company)
    return g


def clean_notes(desc: str) -> str:
    """Episode description -> the intro paragraph (who, what), without sponsor and link blocks."""
    desc = re.split(r"🙏|👉|🎙|👤|Thank you to our|Thanks to our|See Privacy Policy|Subscribe to|"
                    r"Listen on|\n\s*\d{1,2}:\d{2}\s|Chapters|Timestamps",
                    desc or "")[0]
    desc = re.sub(r"\s+", " ", desc)
    return re.sub(r"\s+([.,;:!?])", r"\1", desc).strip()[:1000]


def set_fm(p: Path, updates: dict):
    """Set or add frontmatter keys in a transcript file (strings are JSON-quoted)."""
    _, fm, body = p.read_text(encoding="utf-8").split("---\n", 2)
    lines = fm.splitlines()
    for k, v in updates.items():
        val = v if k == "tags" else json.dumps(v or "", ensure_ascii=False)
        line = f"{k}: {val}"
        idx = next((i for i, l in enumerate(lines) if l.startswith(f"{k}:")), None)
        if idx is None:
            lines.append(line)
        else:
            lines[idx] = line
    p.write_text("---\n" + "\n".join(lines) + "\n---\n" + body, encoding="utf-8")


def show_notes(p: Path) -> str:
    """The show-notes quote kept above the transcript (first '> ' line that isn't a URL)."""
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("> ") and not line[2:].startswith("http"):
            return line[2:]
        if line.startswith("["):
            break
    return ""


def write_md(meta, chunks) -> Path:
    d = meta.get("upload_date") or ""
    date = f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else "undated"
    TDIR.mkdir(parents=True, exist_ok=True)
    for old in TDIR.glob(f"*_{meta['id']}.md"):
        old.unlink()
    name = f"{date}_{slug(meta['channel'], 30)}_{slug(meta['title'], 50)}_{meta['id']}.md"
    fm = [
        "---",
        f"id: {meta['id']}",
        f"title: {json.dumps(meta['title'], ensure_ascii=False)}",
        f"channel: {json.dumps(meta['channel'], ensure_ascii=False)}",
        f"date: {date}",
        f"url: {meta.get('url') or 'https://www.youtube.com/watch?v=' + meta['id']}",
        f"duration: {fmt_ts(meta.get('duration') or 0)}",
        f"lang: {meta['lang']}",
        f"captions: {meta['captions']}",
        f"tags: [{', '.join(meta.get('tags') or [])}]",
        *[f"{k}: {json.dumps(meta[k], ensure_ascii=False)}" for k in META_KEYS if meta.get(k)],
        "---",
        "",
        f"# {meta['title']}",
        "",
    ]
    if meta.get("summary"):  # show notes (guest, role, company) above the transcript
        fm += [f"> {meta['summary']}"] + ([f"> {meta['link']}"] if meta.get("link") else []) + [""]
    body = [f"[{fmt_ts(s)}] {t}\n" for s, t in chunks]
    p = TDIR / name
    p.write_text("\n".join(fm) + "\n" + "\n".join(body), encoding="utf-8")
    return p


def read_md(p: Path):
    _, fm, body = p.read_text(encoding="utf-8").split("---\n", 2)
    meta = {}
    for line in fm.splitlines():
        k, _, v = line.partition(": ")
        v = v.strip()
        if v.startswith('"'):
            v = json.loads(v)
        meta[k.strip()] = v
    meta["tags"] = [t.strip() for t in meta.get("tags", "[]").strip("[]").split(",") if t.strip()]
    chunks = [(parse_ts(ts), txt) for ts, txt in
              re.findall(r"^\[(\d+(?::\d\d)+)\] (.+)$", body, re.M)]
    return meta, chunks


def index_file(c, p: Path):
    meta, chunks = read_md(p)
    vid = meta["id"]
    c.execute("DELETE FROM chunks WHERE video_id=?", (vid,))
    c.execute(
        "INSERT OR REPLACE INTO videos(id, title, channel, date, duration, url, lang, captions, "
        "tags, path, words, guest, role, company) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (vid, meta.get("title"), meta.get("channel"), meta.get("date"), meta.get("duration"),
         meta.get("url"), meta.get("lang"), meta.get("captions"), ",".join(meta["tags"]),
         p.name, sum(len(t.split()) for _, t in chunks),
         meta.get("guest") or None, meta.get("role") or None, meta.get("company") or None),
    )
    c.executemany("INSERT INTO chunks(text, video_id, start) VALUES (?,?,?)",
                  [(t, vid, s) for s, t in chunks])
    return sum(len(t.split()) for _, t in chunks)

# ---------------------------------------------------------------- fetching

def ydl_opts(a):
    o = {"quiet": True, "no_warnings": True, "skip_download": True}
    if a.cookies_from_browser:
        o["cookiesfrombrowser"] = (a.cookies_from_browser,)
    return o


def expand(urls, a, yt_dlp, entries=False):
    """Turn video URLs, bare IDs, playlist and channel URLs into video IDs
    (or, with entries=True, the flat playlist entries incl. titles)."""
    ids, items = [], []
    opts = {**ydl_opts(a), "extract_flat": "in_playlist"}
    if getattr(a, "latest", None):
        opts["playlistend"] = a.latest
    with yt_dlp.YoutubeDL(opts) as y:
        for u in urls:
            u = u.strip()
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", u):
                ids.append(u)
                continue
            m = YT_ID.search(u)
            if m and "/playlist" not in u:
                ids.append(m.group(1))
                continue
            info = y.extract_info(u, download=False)
            if info.get("_type") == "playlist":
                es = [e for e in info.get("entries") or [] if e and e.get("id")]
                ids += [e["id"] for e in es]
                items += es
            else:
                ids.append(info["id"])
                items.append(info)
    return items if entries else list(dict.fromkeys(ids))


def cmd_queue(a):
    """Resolve a channel/playlist into a fixed list of video URLs in a queue file."""
    try:
        import yt_dlp  # type: ignore
    except ImportError:
        sys.exit("yt-dlp missing: pip install -U yt-dlp youtube-transcript-api")
    try:
        items = expand([a.url], a, yt_dlp, entries=True)
    except Exception as e:
        sys.exit(f"could not resolve {a.url}: {e}\n{HINT}")
    out = Path(a.output)
    existing = out.read_text(encoding="utf-8") if out.exists() else ""
    new = [e for e in items if e["id"] not in existing]
    lines = [f"\n# {a.url}  latest {a.latest}, resolved {time.strftime('%Y-%m-%d')}"]
    for e in new:
        dur = f"  [{fmt_ts(e['duration'])}]" if e.get("duration") else ""
        lines.append(f"https://www.youtube.com/watch?v={e['id']}  # {(e.get('title') or '')[:90]}{dur}")
    with out.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(new)} new videos written to {out} ({len(items) - len(new)} already listed)")


def ingest(y, vid, a):
    langs = [l.strip() for l in a.lang.split(",") if l.strip()]
    info = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
    meta = {
        "id": vid,
        "title": info.get("title") or vid,
        "channel": info.get("channel") or info.get("uploader") or "",
        "upload_date": info.get("upload_date"),
        "duration": info.get("duration"),
        "tags": [t.strip() for t in (a.tags or "").split(",") if t.strip()],
    }
    segs, lang, src, errors = None, None, None, []
    pick = pick_track(info, langs)
    if pick:
        lang, track, src = pick
        fmt = next((f for e in ("json3", "vtt") for f in track if f.get("ext") == e), None)
        if fmt:
            try:
                raw = y.urlopen(fmt["url"]).read().decode("utf-8")
                segs = parse_json3(raw) if fmt["ext"] == "json3" else parse_vtt(raw)
            except Exception as e:  # fall through to the second route
                errors.append(f"yt-dlp: {first_line(e)}")
    if not segs:
        try:
            jar = y.cookiejar if a.cookies_from_browser else None
            lang, segs, src = fetch_fallback(vid, langs, jar)
        except ImportError:
            pass
        except Exception as e:
            errors.append(f"fallback: {first_line(e)}")
    if not segs:
        if any(is_block(m) for m in errors):
            raise Blocked("; ".join(errors))
        raise RuntimeError("no captions available" + (f" ({'; '.join(errors)})" if errors else ""))
    meta.update(lang=lang, captions=src, summary=clean_notes(info.get("description")))
    meta.update(extract_guest(meta["summary"]))
    return write_md(meta, chunk(segs))

# ---------------------------------------------------------------- commands

def cmd_add(a):
    try:
        import yt_dlp  # type: ignore
    except ImportError:
        sys.exit("yt-dlp missing: pip install -U yt-dlp youtube-transcript-api")
    urls = list(a.urls)
    if a.file:
        urls += [l.strip() for l in Path(a.file).read_text().splitlines()
                 if l.strip() and not l.lstrip().startswith("#")]
    if not urls:
        sys.exit("nothing to add")
    try:
        ids = expand(urls, a, yt_dlp)
    except Exception as e:
        sys.exit(f"could not resolve URLs: {e}\n{HINT}")
    c = db()
    have = {r[0] for r in c.execute("SELECT id FROM videos")}
    todo = [v for v in ids if a.force or v not in have]
    skip = len(ids) - len(todo)
    ok = fail = 0
    stopped = False
    print(f"{len(todo)} to fetch, {skip} already indexed")
    with yt_dlp.YoutubeDL(ydl_opts(a)) as y:
        for n, vid in enumerate(todo, 1):
            for attempt in range(3):
                try:
                    p = ingest(y, vid, a)
                    words = index_file(c, p)
                    c.commit()
                    ok += 1
                    print(f"+ [{n}/{len(todo)}] {vid}  {words:>6} words  {p.name}")
                    break
                except Exception as e:
                    msg = first_line(e)
                    if isinstance(e, Blocked) or is_block(str(e)):
                        if attempt < 2:
                            wait = 120 * (attempt + 1)
                            print(f"  YouTube is rate-limiting; pausing {wait}s, then retrying {vid}",
                                  file=sys.stderr)
                            time.sleep(wait)
                            continue
                        stopped = True
                    else:
                        fail += 1
                        print(f"! [{n}/{len(todo)}] {vid}  {msg}", file=sys.stderr)
                    break
            if stopped:
                break
            time.sleep(a.sleep * random.uniform(0.6, 1.4))
    print(f"done: {ok} added, {skip} already indexed, {fail} failed")
    if stopped:
        print("stopped: YouTube is still blocking requests from this connection.\n"
              "Wait about an hour, then rerun the same command (finished videos are skipped).\n"
              + ("" if a.cookies_from_browser else
                 "Add --cookies-from-browser chrome so requests come from your logged-in browser.\n"),
              file=sys.stderr)
    elif fail:
        print(HINT, file=sys.stderr)


HINT = ("hint: if YouTube asks to 'confirm you're not a bot', add "
        "--cookies-from-browser chrome (or firefox/safari); keep yt-dlp current "
        "(pip install -U yt-dlp) and install deno if yt-dlp asks for a JS runtime.")


def _fts(c, sql, q, params):
    try:
        return c.execute(sql, (q, *params)).fetchall()
    except sqlite3.OperationalError:  # plain words instead of FTS syntax
        safe = " ".join('"' + w.replace('"', "") + '"' for w in q.split())
        return c.execute(sql, (safe, *params)).fetchall()


def cmd_search(a):
    c = db()
    q = " ".join(a.query)
    where, params = "", []
    if a.tag:
        where += " AND (','||v.tags||',') LIKE ?"
        params.append(f"%,{a.tag},%")
    if a.guest:
        where += " AND (v.guest LIKE ? OR v.company LIKE ?)"
        params += [f"%{a.guest}%"] * 2
    if a.cards:
        sql = f"""SELECT v.id, v.title, v.channel, 0,
                     snippet(cardtext, 0, '**', '**', '…', {a.width}),
                     v.guest, v.company, v.url
              FROM cardtext c JOIN videos v ON v.id = c.video_id
              WHERE cardtext MATCH ? {where} ORDER BY rank LIMIT ?"""
    else:
        sql = f"""SELECT v.id, v.title, v.channel, c.start,
                     snippet(chunks, 0, '**', '**', '…', {a.width}),
                     v.guest, v.company, v.url
              FROM chunks c JOIN videos v ON v.id = c.video_id
              WHERE chunks MATCH ? {where} ORDER BY rank LIMIT ?"""
    rows = _fts(c, sql, q, params + [a.n * 5])
    per, shown = {}, 0
    for vid, title, channel, start, snip, guest, company, url in rows:
        if per.get(vid, 0) >= a.per_video:
            continue
        per[vid] = per.get(vid, 0) + 1
        who = f"{guest}, {company}" if guest and company else guest or channel
        link = ""
        if a.links:
            link = f"  https://youtu.be/{vid}?t={int(start)}" if not vid.startswith("pod-") else f"  {url}"
        at = "card" if a.cards else fmt_ts(start)
        print(f"[{vid} @ {at}] {title[:60]} ({who[:50]}){link}\n  {snip}")
        shown += 1
        if shown >= a.n:
            break
    if not shown:
        print("no hits")


def cmd_show(a):
    c = db()
    rows = c.execute("SELECT CAST(start AS INT), text FROM chunks WHERE video_id=? "
                     "ORDER BY CAST(start AS INT)", (a.id,)).fetchall()
    if not rows:
        sys.exit(f"unknown id {a.id}")
    if a.at:
        t = parse_ts(a.at)
        i = max(i for i, (s, _) in enumerate(rows) if s <= t) if rows[0][0] <= t else 0
        rows = rows[max(0, i - a.window): i + a.window + 1]
    else:
        lo = parse_ts(a.frm) if a.frm else 0
        hi = parse_ts(a.to) if a.to else 10**9
        rows = [r for r in rows if lo <= r[0] <= hi]
    if a.header:
        title, ch, url = c.execute("SELECT title, channel, url FROM videos WHERE id=?",
                                   (a.id,)).fetchone()
        print(f"# {title} ({ch}) {url}")
    for s, t in rows:
        print(f"[{fmt_ts(s)}] {t}")


def cmd_list(a):
    c = db()
    sql, params = "SELECT id, date, duration, channel, title, tags FROM videos", []
    if a.tag:
        sql += " WHERE (','||tags||',') LIKE ?"
        params.append(f"%,{a.tag},%")
    for vid, date, dur, ch, title, tags in c.execute(sql + " ORDER BY date DESC", params):
        print(f"{vid}  {date}  {dur:>8}  {ch[:24]:<24}  {title[:70]}" + (f"  [{tags}]" if tags else ""))


def cmd_tag(a):
    c = db()
    row = c.execute("SELECT path FROM videos WHERE id=?", (a.id,)).fetchone()
    if not row:
        sys.exit(f"unknown id {a.id}")
    p = TDIR / row[0]
    meta, _ = read_md(p)
    tags = list(dict.fromkeys(meta["tags"] + a.tags))
    if a.remove:
        tags = [t for t in meta["tags"] if t not in a.tags]
    set_fm(p, {"tags": f"[{', '.join(tags)}]"})
    index_file(c, p)
    c.commit()
    print(f"{a.id}: [{', '.join(tags)}]")


def cmd_enrich(a):
    """Fill guest/role/company from the saved show notes of every transcript."""
    c = db()
    done = missing = kept = 0
    for p in sorted(TDIR.glob("*.md")):
        meta, _ = read_md(p)
        if meta.get("guest") and not a.force:
            kept += 1
            continue
        g = extract_guest(show_notes(p)) or guest_from_title(meta.get("title", ""))
        if g:
            set_fm(p, {k: g.get(k, "") for k in META_KEYS})
            index_file(c, p)
            done += 1
            print(f"+ {meta['id']}  {g.get('guest')} | {g.get('role', '')} | {g.get('company', '')}")
        else:
            missing += 1
            print(f"? {meta['id']}  no guest found: {meta.get('title', '')[:60]}")
    c.commit()
    print(f"done: {done} enriched, {kept} already had a guest, {missing} without "
          f"(set by hand: cited.py meta ID --guest '...' --role '...' --company '...')")


def cmd_meta(a):
    c = db()
    row = c.execute("SELECT path FROM videos WHERE id=?", (a.id,)).fetchone()
    if not row:
        sys.exit(f"unknown id {a.id}")
    p = TDIR / row[0]
    upd = {k: getattr(a, k) for k in META_KEYS if getattr(a, k) is not None}
    if upd:
        set_fm(p, upd)
        index_file(c, p)
        c.commit()
    meta, _ = read_md(p)
    print(f"{a.id}: " + " | ".join(meta.get(k) or "-" for k in META_KEYS))


def cmd_guests(a):
    c = db()
    sql, params = "SELECT id, date, guest, role, company, title FROM videos", []
    if a.tag:
        sql += " WHERE (','||tags||',') LIKE ?"
        params.append(f"%,{a.tag},%")
    for vid, date, guest, role, company, title in c.execute(sql + " ORDER BY date DESC", params):
        if guest:
            print(f"{vid}  {date}  {guest} | {role or '-'} | {company or '-'}")
        else:
            print(f"{vid}  {date}  ? (no guest)  {title[:60]}")



# ---------------------------------------------------------------- cards

CLAIM_SECTIONS = (("## Claims", "claim"), ("## Evidence", "evidence"), ("## Moments", "moment"))
_CLAIM_BULLET = re.compile(r"^-\s+\[(\d+(?::\d{2})+)\]\s+(.+)$", re.M)
_CLAIM_SPEAKER = re.compile(r"^(.*?)\s*\(([^)]{1,80})\)\s*$")


def read_card(p: Path):
    _, fm, body = p.read_text(encoding="utf-8").split("---\n", 2)
    meta = {}
    for line in fm.splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"')
    meta["topics"] = [t.strip() for t in meta.get("topics", "").strip("[]").split(",") if t.strip()]
    m = re.search(r"## Summary\s*\n(.+?)(?:\n## |\Z)", body, re.S)
    meta["summary"] = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    return meta, body


def parse_card_claims(body: str):
    """Pull Claims / Evidence / Moments bullets from a card body."""
    rows = []
    for head, kind in CLAIM_SECTIONS:
        m = re.search(rf"{re.escape(head)}\s*\n(.*?)(?:\n## |\Z)", body, re.S)
        if not m:
            continue
        for at, text in _CLAIM_BULLET.findall(m.group(1)):
            text = text.strip()
            speaker = ""
            if kind == "claim":
                sm = _CLAIM_SPEAKER.match(text)
                if sm:
                    text, speaker = sm.group(1).strip(), sm.group(2).strip()
            rows.append((kind, at, text, speaker))
    return rows


def claim_row_id(vid: str, at: str, kind: str, text: str) -> str:
    return f"{vid}@{at}|{kind}|{hashlib.sha256(text.encode()).hexdigest()[:8]}"


def index_claims(c, vid: str, body: str):
    c.execute("DELETE FROM claimtext WHERE video_id=?", (vid,))
    c.execute("DELETE FROM claims WHERE video_id=?", (vid,))
    for kind, at, text, speaker in parse_card_claims(body):
        cid = claim_row_id(vid, at, kind, text)
        c.execute("INSERT OR REPLACE INTO claims VALUES (?,?,?,?,?,?,?)",
                  (cid, vid, kind, at, parse_ts(at), text, speaker))
        c.execute("INSERT INTO claimtext(text, claim_id, video_id) VALUES (?,?,?)",
                  (text, cid, vid))


def index_card(c, p: Path):
    meta, body = read_card(p)
    vid = meta.get("id") or p.stem
    c.execute("DELETE FROM cardtext WHERE video_id=?", (vid,))
    c.execute("INSERT OR REPLACE INTO cards VALUES (?,?,?,?,?,?,?)",
              (vid, meta.get("format"), meta.get("sponsored"), meta.get("vendor_guest"),
               meta.get("ai_stance"), ",".join(meta["topics"]), meta["summary"]))
    c.execute("INSERT INTO cardtext(text, video_id) VALUES (?,?)", (body, vid))
    index_claims(c, vid, body)


def cmd_cards(a):
    if a.missing:  # transcripts that still need a card (personal episodes excluded)
        have = {p.stem for p in CDIR.glob("*.md")} if CDIR.exists() else set()
        todo = []
        for p in sorted(TDIR.glob("*.md")):
            meta, _ = read_md(p)
            if meta["id"] not in have and "personal" not in meta["tags"]:
                todo.append(str(p))
        print("\n".join(todo) if todo else "all transcripts have a card")
        return
    c = db()
    sql = """SELECT v.id, v.date, v.channel, v.guest, v.company, k.ai_stance, k.topics,
                    k.sponsored, k.vendor_guest, k.format, k.summary
             FROM cards k JOIN videos v ON v.id = k.id WHERE 1=1"""
    params = []
    if a.tag:
        sql += " AND (','||v.tags||',') LIKE ?"; params.append(f"%,{a.tag},%")
    if a.topic:
        sql += " AND (','||k.topics||',') LIKE ?"; params.append(f"%{a.topic}%")
    if a.stance:
        sql += " AND k.ai_stance = ?"; params.append(a.stance)
    rows = c.execute(sql + " ORDER BY v.date DESC", params).fetchall()
    for vid, date, ch, guest, comp, st, tops, sp, vg, fmt, summ in rows:
        flags = "".join(f for f, on in (("S", sp in ("series", "guest")), ("V", vg == "yes")) if on)
        who = guest + (f", {comp}" if comp else "") if guest else ch
        first = re.split(r"(?<=[.!?])\s", summ, maxsplit=1)[0] if a.short else summ
        print(f"{vid} {date} | {ch[:18]} | {who[:45]} | {st} {flags} | {tops}\n  {first[:400]}")
    print(f"{len(rows)} cards" + ("" if rows else " (none indexed? run: cited reindex)"))


def card_path(vid: str) -> Path:
    own = CDIR / f"{vid}.md"
    if own.exists():
        return own
    return FIXTURE / "cards" / f"{vid}.md"


def cmd_card(a):
    p = card_path(a.id)
    if not p.exists():
        sys.exit(f"no card for {a.id}")
    print(p.read_text(encoding="utf-8"))


def cmd_claims(a):
    """Search or list claim/evidence/moment bullets derived from cards."""
    c = db()
    where, params = ["1=1"], []
    if a.tag:
        where.append("(','||v.tags||',') LIKE ?"); params.append(f"%,{a.tag},%")
    if a.topic:
        where.append("(','||k.topics||',') LIKE ?"); params.append(f"%{a.topic}%")
    if a.kind:
        where.append("cl.kind = ?"); params.append(a.kind)
    if a.guest:
        where.append("(v.guest LIKE ? OR v.company LIKE ?)"); params += [f"%{a.guest}%"] * 2
    if a.episode:
        where.append("cl.video_id = ?"); params.append(a.episode)
    wh = " AND ".join(where)
    q = " ".join(a.query) if a.query else ""
    if q:
        sql = f"""SELECT cl.id, cl.video_id, cl.kind, cl.at,
                         snippet(claimtext, 0, '**', '**', '…', {a.width}),
                         cl.speaker, v.guest, v.company, v.channel, k.vendor_guest, k.sponsored
                  FROM claimtext ct
                  JOIN claims cl ON cl.id = ct.claim_id
                  JOIN videos v ON v.id = cl.video_id
                  LEFT JOIN cards k ON k.id = cl.video_id
                  WHERE claimtext MATCH ? AND {wh}
                  ORDER BY rank LIMIT ?"""
        rows = _fts(c, sql, q, params + [a.n * 5])
    else:
        sql = f"""SELECT cl.id, cl.video_id, cl.kind, cl.at, cl.text,
                         cl.speaker, v.guest, v.company, v.channel, k.vendor_guest, k.sponsored
                  FROM claims cl
                  JOIN videos v ON v.id = cl.video_id
                  LEFT JOIN cards k ON k.id = cl.video_id
                  WHERE {wh}
                  ORDER BY v.date DESC, cl.start
                  LIMIT ?"""
        rows = c.execute(sql, params + [a.n * 5]).fetchall()
    per_limit = a.per_video if not a.episode else max(a.per_video, a.n)
    per, shown = {}, 0
    for cid, vid, kind, at, snip, speaker, guest, company, channel, vg, sp in rows:
        if per.get(vid, 0) >= per_limit:
            continue
        per[vid] = per.get(vid, 0) + 1
        who = speaker or (f"{guest}, {company}" if guest and company else guest or channel)
        flags = "".join(f for f, on in (("S", sp in ("series", "guest")), ("V", vg == "yes")) if on)
        print(f"[{vid} @ {at}] {kind}{(' ' + flags) if flags else ''} ({who[:50]})\n  {snip}")
        print(f"  id: {cid}")
        shown += 1
        if shown >= a.n:
            break
    if not shown:
        print("no claims" if not q else "no hits")
    else:
        print(f"{shown} claims")


def cmd_claim(a):
    c = db()
    row = c.execute(
        """SELECT cl.id, cl.video_id, cl.kind, cl.at, cl.text, cl.speaker,
                  v.guest, v.company, v.channel, v.title, k.vendor_guest, k.sponsored
           FROM claims cl JOIN videos v ON v.id = cl.video_id
           LEFT JOIN cards k ON k.id = cl.video_id
           WHERE cl.id = ?""",
        (a.id,),
    ).fetchone()
    if not row:
        # allow prefix match when the hash is omitted
        rows = c.execute(
            """SELECT cl.id, cl.video_id, cl.kind, cl.at, cl.text, cl.speaker,
                      v.guest, v.company, v.channel, v.title, k.vendor_guest, k.sponsored
               FROM claims cl JOIN videos v ON v.id = cl.video_id
               LEFT JOIN cards k ON k.id = cl.video_id
               WHERE cl.id LIKE ? ORDER BY cl.id LIMIT 5""",
            (a.id.rstrip("|") + "%",),
        ).fetchall()
        if len(rows) == 1:
            row = rows[0]
        elif rows:
            print("ambiguous id; matches:")
            for r in rows:
                print(f"  {r[0]}")
            sys.exit(1)
        else:
            sys.exit(f"unknown claim {a.id}")
    cid, vid, kind, at, text, speaker, guest, company, channel, title, vg, sp = row
    who = speaker or (f"{guest}, {company}" if guest and company else guest or channel)
    flags = []
    if vg == "yes":
        flags.append("vendor_guest")
    if sp in ("series", "guest", "ads"):
        flags.append(f"sponsored={sp}")
    print(f"{cid}")
    print(f"{kind} | {vid} @ {at} | {who}" + (f" | {', '.join(flags)}" if flags else ""))
    print(f"{title}")
    print(text)
    print(f"verify: python3 cited.py show {vid} --at {at} --window 1")


def _md_sources(kind: str) -> list[Path]:
    """User files override the synthetic fixture when ids collide."""
    fixture = sorted((FIXTURE / kind).glob("*.md")) if (FIXTURE / kind).exists() else []
    own_dir = TDIR if kind == "transcripts" else CDIR
    own = sorted(own_dir.glob("*.md")) if own_dir.exists() else []
    return fixture + own


def cmd_reindex(a):
    for suffix in ("", "-journal", "-wal", "-shm"):  # stale journals would corrupt the new index
        f = Path(str(DB_PATH) + suffix)
        if f.exists():
            f.unlink()
    c = db()
    n = 0
    for p in _md_sources("transcripts"):
        index_file(c, p)
        n += 1
    k = 0
    for p in _md_sources("cards"):
        index_card(c, p)
        k += 1
    claims = c.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    c.commit()
    print(f"indexed {n} transcripts, {k} cards, {claims} claims")


def cmd_stats(a):
    c = db()
    v, w = c.execute("SELECT COUNT(*), COALESCE(SUM(words),0) FROM videos").fetchone()
    secs = sum(parse_ts(d) for (d,) in c.execute("SELECT duration FROM videos") if d)
    tags = {}
    for (t,) in c.execute("SELECT tags FROM videos"):
        for x in filter(None, (t or "").split(",")):
            tags[x] = tags.get(x, 0) + 1
    print(f"{v} videos, {secs/3600:.1f} h, {w:,} words (~{int(w*1.35):,} tokens if read in full)")
    if tags:
        print("tags: " + ", ".join(f"{k} ({n})" for k, n in sorted(tags.items(), key=lambda x: -x[1])))
    try:
        by = dict(c.execute("SELECT kind, COUNT(*) FROM claims GROUP BY kind").fetchall())
        if by:
            total = sum(by.values())
            parts = ", ".join(f"{k} ({by.get(k, 0)})" for k in ("claim", "evidence", "moment") if k in by)
            print(f"claims: {total} ({parts})")
    except sqlite3.OperationalError:
        pass
    print("(for full denominators: python3 cited.py corpus)")


def _mining_dir() -> Path:
    return ROOT / "mining"


def _run_mining_script(script: str, argv: list[str], use_venv: bool = False) -> int:
    """Dispatch to a mining/*.py module. Prefer .venv python for BGE propose."""
    py = sys.executable
    venv_py = ROOT / ".venv" / "bin" / "python"
    if use_venv and venv_py.exists():
        py = str(venv_py)
    cmd = [py, str(_mining_dir() / script), *argv]
    import subprocess
    return subprocess.call(cmd)


def cmd_corpus(a):
    sys.path.insert(0, str(_mining_dir()))
    from corpus_stats import corpus_report  # noqa: WPS433
    print(corpus_report(with_drift=bool(a.drift)))


def cmd_mine(a):
    """Wrap mining propose / walk / stats (CLI spine)."""
    sub = a.mine_cmd
    if sub == "propose":
        argv = []
        if getattr(a, "episode", None):
            argv += ["--episode", a.episode]
        if getattr(a, "coded_only", False):
            argv.append("--coded-only")
        if getattr(a, "uncoded_only", False):
            argv.append("--uncoded-only")
        if getattr(a, "min_score", None) is not None:
            argv += ["--min-score", str(a.min_score)]
        if getattr(a, "limit", None) is not None:
            argv += ["--limit", str(a.limit)]
        if getattr(a, "force", False):
            argv.append("--force")
        if getattr(a, "dry_run", False):
            argv.append("--dry-run")
        if getattr(a, "write_none", False):
            argv.append("--write-none")
        raise SystemExit(_run_mining_script("tag_candidates.py", argv, use_venv=True))
    if sub == "walk":
        argv = ["walk"]
        if getattr(a, "category", None):
            argv += ["--category", a.category]
        if getattr(a, "limit", None) is not None:
            argv += ["--limit", str(a.limit)]
        if getattr(a, "min_score", None) is not None:
            argv += ["--min-score", str(a.min_score)]
        if getattr(a, "include_unclear", False):
            argv.append("--include-unclear")
        raise SystemExit(_run_mining_script("review.py", argv))
    if sub == "stats":
        argv = []
        if getattr(a, "all", False):
            argv.append("--all")
        if getattr(a, "category", None):
            argv += ["--category", a.category]
        if getattr(a, "drift", False):
            argv.append("--drift")
        raise SystemExit(_run_mining_script("stats.py", argv))
    if sub in ("list", "show", "accept", "reject", "none"):
        rest = list(getattr(a, "rest", None) or [])
        if rest and rest[0] == "--":
            rest = rest[1:]
        argv = [sub] + rest
        raise SystemExit(_run_mining_script("review.py", argv))
    sys.exit(f"unknown mine subcommand {sub}")


def cmd_packet(a):
    sys.path.insert(0, str(_mining_dir()))
    import packets_lib  # noqa: WPS433
    if a.packet_cmd == "list":
        packets_lib.cmd_list()
    elif a.packet_cmd == "show":
        packets_lib.cmd_show([a.id] if getattr(a, "id", None) else [])
    elif a.packet_cmd == "refresh":
        packets_lib.cmd_refresh([getattr(a, "id", None) or "all"])
    elif a.packet_cmd == "new":
        argv = [a.id, a.title]
        if getattr(a, "cats", None):
            argv += ["--cats", a.cats]
        if getattr(a, "research", None):
            argv += ["--research", a.research]
        packets_lib.cmd_new(argv)
    else:
        sys.exit(f"unknown packet cmd {a.packet_cmd}")


def cmd_brief(a):
    sys.path.insert(0, str(_mining_dir()))
    import packets_lib  # noqa: WPS433
    argv = ["-n", str(a.n), a.target]
    packets_lib.cmd_brief(argv)


def cmd_card_scaffold(a):
    """Print meta + timestamped paragraph openings to draft a thin card (less transcript in context)."""
    sys.path.insert(0, str(ROOT))
    from domain import card_spec  # noqa: WPS433
    spec = card_spec()
    c = db()
    row = c.execute(
        "SELECT id, title, channel, date, guest, role, company, url, tags FROM videos WHERE id=?",
        (a.id,),
    ).fetchone()
    if not row:
        sys.exit(f"unknown id {a.id}")
    vid, title, channel, date, guest, role, company, url, tags = row
    print("--- scaffold for card ---")
    print(f"id: {vid}")
    print(f'title: "{title}"')
    print(f'show: "{channel}"')
    print(f"date: {date}")
    print(f'guest: "{guest or ""}"')
    print(f'role: "{role or ""}"')
    print(f'company: "{company or ""}"')
    for key, choices in spec["enums"].items():
        print(f"{key}: {' | '.join(choices)}")
    lo, hi = spec.get("topics_min", 2), spec.get("topics_max", 5)
    print(f"topics: [{lo}–{hi} of: {', '.join(spec['topics'])}]")
    print("---")
    print(f"url: {url}")
    print(f"tags: {tags}")
    print()
    print("## Paragraph openings (use as claim timestamps)")
    rows = c.execute(
        "SELECT CAST(start AS INT), text FROM chunks WHERE video_id=? ORDER BY CAST(start AS INT)",
        (vid,),
    ).fetchall()
    step = max(1, len(rows) // max(a.n, 1)) if rows else 1
    picked = rows[::step][: a.n] if rows else []
    for start, text in picked:
        snip = re.sub(r"\s+", " ", text).strip()[:140]
        print(f"- [{fmt_ts(start)}] {snip}")
    print()
    print("Write cards/<id>.md. Fields and headings come from domain/card.json.")
    print(f"Then: python3 validate_cards.py cards transcripts {vid}")
    print("Then: python3 cited.py reindex && python3 cited.py mine propose --episode", vid)


def cmd_grow(a):
    """CLI steps after picks: enrich → reindex → mine propose for missing-card eps or given ids."""
    print("=== cited grow ===")
    print("1) Enrich guest meta from show notes")
    cmd_enrich(argparse.Namespace(force=False))
    print("\n2) Reindex")
    cmd_reindex(argparse.Namespace())
    missing = []
    have = {p.stem for p in CDIR.glob("*.md")} if CDIR.exists() else set()
    for p in sorted(TDIR.glob("*.md")):
        meta, _ = read_md(p)
        if meta["id"] not in have and "personal" not in meta["tags"]:
            missing.append(meta["id"])
    if a.ids:
        targets = [x.strip() for x in Path(a.ids).read_text().splitlines() if x.strip() and not x.startswith("#")]
    elif a.episode:
        targets = [a.episode]
    else:
        targets = []
    print(f"\n3) Cards missing: {len(missing)}")
    if missing[:20]:
        print("   " + ", ".join(missing[:20]) + ("…" if len(missing) > 20 else ""))
    print("   → write thin cards, then: python3 validate_cards.py cards transcripts")
    print("   → python3 cited.py reindex")
    if targets:
        print(f"\n4) Mine propose for {len(targets)} episode(s)")
        for vid in targets:
            print(f"   → mine propose --episode {vid}")
            _run_mining_script("tag_candidates.py", ["--episode", vid], use_venv=True)
    else:
        print("\n4) Mine propose: pass --episode ID or --ids file after cards exist")
    print("\n5) Corpus")
    cmd_corpus(argparse.Namespace(drift=False))
    print("\nNext (human): python3 cited.py mine walk")
    print("Next (study): python3 cited.py packet list")

# ---------------------------------------------------------------- podcasts (RSS + Whisper)

NS = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
      "podcast": "https://podcastindex.org/namespace/1.0"}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) cited/1.0"}


def _ssl_ctx():
    try:
        import certifi  # python.org builds on macOS often lack root certificates
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def http_open(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                  timeout=timeout, context=_ssl_ctx())


def resolve_feed(src: str) -> str:
    """RSS URL as is; Apple Podcasts URL or numeric ID -> feed URL via the iTunes lookup."""
    m = re.fullmatch(r"(\d{6,})", src.strip()) or \
        ("podcasts.apple.com" in src and re.search(r"/id(\d{6,})", src))
    if m:
        data = json.loads(http_open(f"https://itunes.apple.com/lookup?id={m.group(1)}").read())
        try:
            return data["results"][0]["feedUrl"]
        except (KeyError, IndexError):
            sys.exit(f"no RSS feed found for Apple Podcasts id {m.group(1)}")
    return src


def _dur(s):
    s = (s or "").strip()
    if not s:
        return 0
    return parse_ts(s) if ":" in s else int(float(s))


def parse_feed(xml_bytes):
    ch = ET.fromstring(xml_bytes).find("channel")
    show = (ch.findtext("title") or "").strip()
    eps = []
    for it in ch.findall("item"):
        enc = it.find("enclosure")
        if enc is None or not enc.get("url"):
            continue
        guid = (it.findtext("guid") or enc.get("url")).strip()
        try:
            d = email.utils.parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y%m%d")
        except Exception:
            d = ""
        desc = clean_notes(html.unescape(_TAG.sub(" ", it.findtext("description") or "")))
        eps.append({
            "id": "pod-" + hashlib.sha1(guid.encode()).hexdigest()[:10],
            "title": (it.findtext("title") or "").strip(),
            "channel": show,
            "upload_date": d,
            "duration": _dur(it.findtext("itunes:duration", namespaces=NS)),
            "audio": enc.get("url"),
            "link": (it.findtext("link") or "").strip(),
            "url": (it.findtext("link") or "").strip() or enc.get("url"),
            "summary": desc,
            "transcripts": [(t.get("url"), (t.get("type") or "").lower())
                            for t in it.findall("podcast:transcript", NS) if t.get("url")],
        })
    return show, eps


def parse_transcript_json(raw):
    return [(s.get("startTime", 0), s.get("body", "")) for s in json.loads(raw).get("segments", [])]


def fetch_published_transcript(ep):
    """Use a transcript the publisher ships in the feed (podcast:transcript), if any."""
    for kind, parser in (("vtt", parse_vtt), ("srt", parse_vtt), ("subrip", parse_vtt),
                         ("json", parse_transcript_json)):
        for url, typ in ep["transcripts"]:
            if kind in typ:
                try:
                    segs = parser(http_open(url).read().decode("utf-8", "replace"))
                    if segs:
                        return segs
                except Exception as e:
                    print(f"  (published transcript failed: {first_line(e)})", file=sys.stderr)
    return None


_FW_MODEL = None


def transcribe(path, model=None):
    """Local speech-to-text. mlx-whisper on Apple Silicon, else faster-whisper (CPU)."""
    try:
        import mlx_whisper  # type: ignore
        if not shutil.which("ffmpeg"):
            sys.exit("mlx-whisper needs ffmpeg: brew install ffmpeg")
        # Speed without quality loss: greedy decoding only (no temperature fallback retries),
        # no conditioning on previous text (also prevents repetition loops). The prompt
        # is the names and terms in domain/whisper_prompt.txt.
        sys.path.insert(0, str(ROOT))
        from domain import whisper_prompt  # noqa: WPS433
        prompt = whisper_prompt()
        r = mlx_whisper.transcribe(
            path, path_or_hf_repo=model or os.environ.get("WHISPER_MODEL")
            or "mlx-community/whisper-large-v3-turbo",
            verbose=False, temperature=0.0, condition_on_previous_text=False,
            initial_prompt=prompt)
        return [(s["start"], s["text"]) for s in r["segments"]], r.get("language") or "en"
    except ImportError:
        pass
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        sys.exit("no transcriber installed: pip install mlx-whisper (Apple Silicon) or faster-whisper")
    global _FW_MODEL
    if _FW_MODEL is None:
        _FW_MODEL = WhisperModel(model or "large-v3-turbo", compute_type="int8")
    sys.path.insert(0, str(ROOT))
    from domain import whisper_prompt  # noqa: WPS433
    segs, info = _FW_MODEL.transcribe(path, vad_filter=True, beam_size=1,
                                      condition_on_previous_text=False,
                                      initial_prompt=whisper_prompt())
    return [(s.start, s.text) for s in segs], info.language


def cmd_pod(a):
    feed = resolve_feed(a.feed)
    try:
        show, eps = parse_feed(http_open(feed).read())
    except Exception as e:
        sys.exit(f"could not read feed {feed}: {first_line(e)}")
    if a.match:
        eps = [e for e in eps if re.search(a.match, e["title"] + " " + e["summary"], re.I)]
    if a.ids:  # exact selection by stable episode id (pod-...), independent of --latest
        want = set(re.findall(r"pod-[0-9a-f]{10}", Path(a.ids).read_text(encoding="utf-8")))
        eps = [e for e in eps if e["id"] in want]
    else:
        eps = eps[: a.latest]
    if a.list:
        n_tr = sum(1 for e in eps if e["transcripts"])
        print(f"# {show} | {len(eps)} episodes | {n_tr} with transcript in feed | {feed}")
        for i, e in enumerate(eps, 1):
            tr = " [T]" if e["transcripts"] else ""
            g = extract_guest(e["summary"])
            who = (g.get("guest", "") + (f", {g['company']}" if g.get("company") else "")) if g else ""
            print(f"{i:>3}. {e['id']} {e['upload_date'] or '????????'} {fmt_ts(e['duration']):>8}{tr} "
                  f"| {e['title'][:85]}" + (f" | {who[:60]}" if who else ""))
        return
    if a.pick:
        keep = set()
        for part in a.pick.split(","):
            lo, _, hi = part.strip().partition("-")
            keep.update(range(int(lo), int(hi or lo) + 1))
        eps = [e for i, e in enumerate(eps, 1) if i in keep]
    c = db()
    have = {r[0] for r in c.execute("SELECT id FROM videos")}
    todo = [e for e in eps if a.force or e["id"] not in have]
    total_audio = sum(e["duration"] for e in todo)
    print(f"{show}: {len(todo)} to transcribe ({total_audio/3600:.1f} h audio), "
          f"{len(eps) - len(todo)} already indexed")
    tags = [t.strip() for t in (a.tags or "").split(",") if t.strip()]
    for n, ep in enumerate(todo, 1):
        t0 = time.time()
        try:
            segs, lang, src = fetch_published_transcript(ep), "en", "published"
            if not segs:
                with tempfile.TemporaryDirectory() as tmp:
                    path = os.path.join(tmp, "episode.mp3")
                    with http_open(ep["audio"], timeout=300) as r, open(path, "wb") as f:
                        shutil.copyfileobj(r, f)
                    segs, lang = transcribe(path, a.model)
                    src = "whisper"
            meta = {**ep, "lang": lang, "captions": src, "tags": tags,
                    **(extract_guest(ep["summary"]) or guest_from_title(ep["title"]))}
            p = write_md(meta, chunk(segs))
            words = index_file(c, p)
            c.commit()
            print(f"+ [{n}/{len(todo)}] {words:>6} words  {time.time()-t0:5.0f}s  {ep['title'][:70]}")
        except Exception as e:
            print(f"! [{n}/{len(todo)}] {ep['title'][:60]}: {first_line(e)}", file=sys.stderr)
    print("done")

# ---------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(prog="cited", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="fetch transcripts for videos, playlists or channels")
    p.add_argument("urls", nargs="*")
    p.add_argument("-f", "--file", help="text file with one URL per line (# comments ok)")
    p.add_argument("--tags", default="", help="comma-separated, e.g. talks,field")
    p.add_argument("--lang", default="en,de", help="preferred caption languages, in order")
    p.add_argument("--cookies-from-browser", metavar="BROWSER")
    p.add_argument("--sleep", type=float, default=8, help="average pause between videos (s)")
    p.add_argument("--force", action="store_true", help="re-fetch videos already indexed")
    p.add_argument("--latest", type=int, help="only the N newest videos of a channel/playlist")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("queue", help="write the N newest videos of a channel/playlist to a queue file")
    p.add_argument("url", help="e.g. https://www.youtube.com/@example/videos")
    p.add_argument("--latest", type=int, default=30)
    p.add_argument("-o", "--output", default=str(ROOT / "queue.txt"))
    p.add_argument("--cookies-from-browser", metavar="BROWSER")
    p.set_defaults(fn=cmd_queue)

    p = sub.add_parser("pod", help="podcast RSS feed -> transcripts (feed transcript or local Whisper)")
    p.add_argument("feed", help="RSS URL, Apple Podcasts URL, or Apple Podcasts id")
    p.add_argument("--latest", type=int, default=30)
    p.add_argument("--match", help="only episodes whose title/notes match this regex, e.g. 'AI|perform'")
    p.add_argument("--list", action="store_true", help="only list episodes (numbered), fetch nothing")
    p.add_argument("--pick", help="numbers from --list to fetch, e.g. 1,3,5-9")
    p.add_argument("--ids", help="file with episode ids (pod-...) to fetch; ignores --latest")
    p.add_argument("--tags", default="")
    p.add_argument("--model", help="Whisper model (default large-v3-turbo)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_pod)

    p = sub.add_parser("search", help="full-text search; prints short snippets")
    p.add_argument("query", nargs="+", help='words or FTS5 syntax: "exact phrase", a OR b, NEAR(a b)')
    p.add_argument("-n", type=int, default=10)
    p.add_argument("--tag")
    p.add_argument("--guest", help="only episodes whose guest or company contains this")
    p.add_argument("--cards", action="store_true", help="search the summary cards, not transcripts")
    p.add_argument("--per-video", type=int, default=2)
    p.add_argument("--width", type=int, default=32, help="snippet length in tokens (max 64)")
    p.add_argument("--links", action="store_true", help="add timestamped YouTube links")
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("show", help="print part of a transcript")
    p.add_argument("id")
    p.add_argument("--at", help="timestamp to centre on, e.g. 12:30")
    p.add_argument("--window", type=int, default=1, help="paragraphs before/after --at")
    p.add_argument("--from", dest="frm")
    p.add_argument("--to")
    p.add_argument("--header", action="store_true")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("list", help="one line per video")
    p.add_argument("--tag")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("tag", help="add (or --remove) tags")
    p.add_argument("id")
    p.add_argument("tags", nargs="+")
    p.add_argument("--remove", action="store_true")
    p.set_defaults(fn=cmd_tag)

    sub.add_parser("reindex", help="rebuild cited.sqlite from transcripts, cards, and the fixture").set_defaults(fn=cmd_reindex)

    p = sub.add_parser("cards", help="list summary cards (filter by tag, topic, stance)")
    p.add_argument("--tag")
    p.add_argument("--topic", help="a topic id from domain/card.json")
    p.add_argument("--stance", choices=["optimist", "pragmatist", "sceptic", "n/a"])
    p.add_argument("--short", action="store_true", help="first summary sentence only")
    p.add_argument("--missing", action="store_true", help="list transcripts without a card")
    p.set_defaults(fn=cmd_cards)

    p = sub.add_parser("card", help="print one summary card")
    p.add_argument("id")
    p.set_defaults(fn=cmd_card)

    p = sub.add_parser("claims", help="search or list claim/evidence/moment bullets from cards")
    p.add_argument("query", nargs="*", help="FTS query; omit to list recent claims")
    p.add_argument("-n", type=int, default=10)
    p.add_argument("--tag")
    p.add_argument("--topic", help="a topic id from domain/card.json")
    p.add_argument("--kind", choices=["claim", "evidence", "moment"])
    p.add_argument("--guest", help="only episodes whose guest or company contains this")
    p.add_argument("--episode", help="only claims from this episode id")
    p.add_argument("--per-video", type=int, default=2)
    p.add_argument("--width", type=int, default=32, help="snippet length in tokens when searching")
    p.set_defaults(fn=cmd_claims)

    p = sub.add_parser("claim", help="print one claim by id (from cited claims)")
    p.add_argument("id", help="full claim id, or prefix like pod-abc@12:30|claim")
    p.set_defaults(fn=cmd_claim)

    sub.add_parser("stats").set_defaults(fn=cmd_stats)

    p = sub.add_parser("corpus", help="denominators: fetched / carded / claims / accepted tags")
    p.add_argument("--drift", action="store_true", help="also print codebook drift signals")
    p.set_defaults(fn=cmd_corpus)

    p = sub.add_parser("mine", help="codebook tags on claims (propose / walk / stats)")
    mine_sub = p.add_subparsers(dest="mine_cmd", required=True)
    mp = mine_sub.add_parser("propose", help="propose category candidates (needs .venv + BGE)")
    mp.add_argument("--episode")
    mp.add_argument("--coded-only", action="store_true")
    mp.add_argument("--uncoded-only", action="store_true")
    mp.add_argument("--min-score", type=float)
    mp.add_argument("--limit", type=int)
    mp.add_argument("--force", action="store_true")
    mp.add_argument("--dry-run", action="store_true")
    mp.add_argument("--write-none", action="store_true")
    mw = mine_sub.add_parser("walk", help="interactive accept/reject")
    mw.add_argument("--category")
    mw.add_argument("--limit", type=int)
    mw.add_argument("--min-score", type=float)
    mw.add_argument("--include-unclear", action="store_true")
    ms = mine_sub.add_parser("stats", help="accepted prevalence")
    ms.add_argument("--all", action="store_true")
    ms.add_argument("--category")
    ms.add_argument("--drift", action="store_true")
    for name in ("list", "show", "accept", "reject", "none"):
        mx = mine_sub.add_parser(name, help=f"review.py {name}")
        mx.add_argument("rest", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_mine)

    p = sub.add_parser("packet", help="packets for the questions you are learning")
    pkt = p.add_subparsers(dest="packet_cmd", required=True)
    pkt.add_parser("list").set_defaults(id=None, title=None, cats=None, research=None)
    ps = pkt.add_parser("show")
    ps.add_argument("id")
    pr = pkt.add_parser("refresh")
    pr.add_argument("id", nargs="?", default="all", help="packet id or 'all'")
    pn = pkt.add_parser("new")
    pn.add_argument("id")
    pn.add_argument("title")
    pn.add_argument("--cats", help="comma-separated category ids")
    pn.add_argument("--research", help="comma-separated question ids, e.g. Q1,Q2")
    p.set_defaults(fn=cmd_packet)

    p = sub.add_parser("brief", help="study pass for one packet or question")
    p.add_argument("target", help="packet id or question id")
    p.add_argument("-n", type=int, default=8, help="max cites per packet")
    p.set_defaults(fn=cmd_brief)

    p = sub.add_parser("card-scaffold", help="draft aid: frontmatter + paragraph openings for a card")
    p.add_argument("id")
    p.add_argument("-n", type=int, default=12, help="how many paragraph openings")
    p.set_defaults(fn=cmd_card_scaffold)

    p = sub.add_parser("grow", help="CLI grow steps: enrich → reindex → corpus (+ optional mine)")
    p.add_argument("--episode", help="also mine propose for this episode")
    p.add_argument("--ids", help="file of episode ids for mine propose")
    p.set_defaults(fn=cmd_grow)

    p = sub.add_parser("enrich", help="fill guest/role/company from saved show notes")
    p.add_argument("--force", action="store_true", help="also redo transcripts that have a guest")
    p.set_defaults(fn=cmd_enrich)

    p = sub.add_parser("meta", help="show or set guest/role/company by hand")
    p.add_argument("id")
    for k in META_KEYS:
        p.add_argument(f"--{k}")
    p.set_defaults(fn=cmd_meta)

    p = sub.add_parser("guests", help="one line per episode: guest | role | company")
    p.add_argument("--tag")
    p.set_defaults(fn=cmd_guests)

    a = ap.parse_args(argv)
    try:
        a.fn(a)
    except KeyboardInterrupt:
        sys.exit("\nstopped. Rerun the same command to continue; finished videos are skipped.")


if __name__ == "__main__":
    main()
