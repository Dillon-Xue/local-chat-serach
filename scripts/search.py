#!/usr/bin/env python3
"""local-chat-search: search WorkBuddy local conversation history.

Pure-local, stdlib-only. Reads ~/.workbuddy/projects/<slug>/<conversationId>.jsonl.
Output: JSON to stdout.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone


def wb_root(override=None):
    if override:
        if override.startswith("~"):
            return os.path.expanduser(override)
        return override
    return os.path.expanduser("~/.workbuddy")


def slug_from_cwd(cwd):
    if not cwd:
        return ""
    p = cwd.strip().lower()
    p = p.replace(":", "")
    p = p.replace("\\", "/")
    p = p.replace("/", "-")
    while "--" in p:
        p = p.replace("--", "-")
    return p.strip("-")


def load_sessions(root):
    """Map normalized workDir(slug) -> conversationId."""
    fp = os.path.join(root, "app", "sessions.json")
    out = {}
    if not os.path.isfile(fp):
        return out
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        for s in data.get("sessions", []):
            wd = s.get("workDir") or s.get("cwd")
            if wd:
                out[slug_from_cwd(wd)] = s.get("conversationId")
    except Exception:
        pass
    return out


CACHE_DIR = os.path.join(tempfile.gettempdir(), "lcs_cache")


def _cache_path(fp):
    h = hashlib.md5(fp.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, h + ".json")


def load_parsed(fp):
    """返回 (records, title)。records: [(ts, text, role)]；优先读 temp 缓存，按 mtime+size 失效。"""
    try:
        st = os.stat(fp)
    except OSError:
        return [], None
    cpath = _cache_path(fp)
    if os.path.isfile(cpath):
        try:
            with open(cpath, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("mtime") == st.st_mtime and cache.get("size") == st.st_size:
                return cache.get("records", []), cache.get("title")
        except Exception:
            pass
    records = []
    title = None
    try:
        with open(fp, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("type") == "ai-title":
                    title = rec.get("aiTitle")
                    continue
                text, role = extract_text(rec)
                if text is None:
                    continue
                ts = rec.get("timestamp")
                if not isinstance(ts, (int, float)):
                    continue
                records.append([ts, text, role])
    except Exception:
        return records, title
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump({"mtime": st.st_mtime, "size": st.st_size,
                       "records": records, "title": title}, f, ensure_ascii=False)
    except Exception:
        pass
    return records, title


def iter_files(root, scope, cwd):
    projects = os.path.join(root, "projects")
    if not os.path.isdir(projects):
        return
    if scope == "current":
        sessions = load_sessions(root)
        slug = slug_from_cwd(cwd)
        cid = sessions.get(slug)
        if cid:
            cand = os.path.join(projects, slug, cid + ".jsonl")
            if os.path.isfile(cand):
                yield cand
                return
        sdir = os.path.join(projects, slug)
        if os.path.isdir(sdir):
            for fn in os.listdir(sdir):
                if fn.endswith(".jsonl"):
                    yield os.path.join(sdir, fn)
        return
    if scope == "project":
        slug = slug_from_cwd(cwd)
        sdir = os.path.join(projects, slug)
        if os.path.isdir(sdir):
            for fn in sorted(os.listdir(sdir)):
                if fn.endswith(".jsonl"):
                    yield os.path.join(sdir, fn)
        return
    # all
    for slug in sorted(os.listdir(projects)):
        sdir = os.path.join(projects, slug)
        if os.path.isdir(sdir):
            for fn in sorted(os.listdir(sdir)):
                if fn.endswith(".jsonl"):
                    yield os.path.join(sdir, fn)


def extract_text(rec):
    """Return (text, role) for searchable records, else (None, None)."""
    t = rec.get("type")
    role = rec.get("role")
    if t == "message" and role in ("user", "assistant"):
        parts = []
        for c in rec.get("content", []) or []:
            if isinstance(c, dict) and c.get("text"):
                parts.append(c["text"])
        return ("\n".join(parts).replace("\r", ""), role)
    if t == "function_call_result":
        out = rec.get("output")
        if isinstance(out, dict):
            return ((out.get("text") or "").replace("\r", ""), "tool")
        if isinstance(out, str):
            return (out.replace("\r", ""), "tool")
    return (None, None)


CODE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def tokenize(q):
    q = (q or "").strip()
    if not q:
        return []
    parts = re.split(r"[\s,，。、;；:：!！?？]+", q)
    parts = [p for p in parts if p]
    return parts or [q]


def score_text(text, terms):
    if not text or not terms:
        return 0.0
    low = text.lower()
    present = [t for t in terms if t.lower() in low]
    if not present:
        return 0.0
    hits = sum(low.count(t.lower()) for t in terms)
    return min(100.0, 40.0 + hits * 12.0)


def make_snippet(text, terms, width=90):
    low = text.lower()
    pos = -1
    for t in terms:
        i = low.find(t.lower())
        if i != -1 and (pos == -1 or i < pos):
            pos = i
    if pos == -1:
        return text[:width]
    start = max(0, pos - width // 3)
    end = min(len(text), start + width)
    snip = text[start:end]
    if start > 0:
        snip = "…" + snip
    if end < len(text):
        snip = snip + "…"
    return snip


def in_time_range(ts_ms, time_range, start=None, end=None):
    if time_range == "all" and not start and not end:
        return True
    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).astimezone()
    now = datetime.now()
    if time_range == "today":
        return dt.date() == now.date()
    if time_range == "yesterday":
        return dt.date() == (now - timedelta(days=1)).date()
    if time_range == "this_week":
        monday = now - timedelta(days=now.weekday())
        return dt.date() >= monday.date()
    if time_range == "last_week":
        monday = now - timedelta(days=now.weekday())
        lw_start = monday - timedelta(days=7)
        return lw_start.date() <= dt.date() < monday.date()
    if time_range == "custom":
        if start:
            sd = datetime.strptime(start, "%Y-%m-%d")
            if dt.date() < sd.date():
                return False
        if end:
            ed = datetime.strptime(end, "%Y-%m-%d")
            if dt.date() > ed.date():
                return False
        return True
    return True


def related_queries(q):
    toks = tokenize(q)
    sugg = []
    if len(toks) > 1:
        sugg.append(" ".join(toks[:-1]))
        sugg.append(" ".join(toks[1:]))
    return sugg[:3]


def time_range_rewrites(tr):
    mapping = {
        "today": ["昨天", "本周"],
        "yesterday": ["今天", "本周"],
        "this_week": ["上周", "最近一个月"],
        "last_week": ["本周", "最近一个月"],
        "custom": ["放宽时间范围", "不限时间"],
        "all": [],
    }
    return mapping.get(tr, [])


def empty_out(scope, query, time_range):
    out = {
        "search_scope": scope,
        "total_results": 0,
        "results": [],
    }
    if scope == "current":
        out["expand_suggestion"] = "当前对话中未找到相关内容，可扩大到「当前项目」或「所有项目」再试。"
    else:
        out["expand_suggestion"] = "在所有范围内均未找到匹配内容。"
    out["suggestions"] = {
        "related_queries": related_queries(query),
        "time_range_rewrites": time_range_rewrites(time_range),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--scope", default="current", choices=["current", "project", "all"])
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--root", default=None)
    ap.add_argument("--time-range", default="all",
                    choices=["all", "today", "yesterday", "this_week", "last_week", "custom"])
    ap.add_argument("--time-start", default=None)
    ap.add_argument("--time-end", default=None)
    ap.add_argument("--sort-by", default="relevance", choices=["relevance", "time"])
    ap.add_argument("--max-results", type=int, default=10)
    ap.add_argument("--no-code", action="store_true")
    args = ap.parse_args()

    root = wb_root(args.root)
    terms = tokenize(args.query)
    if not terms:
        print(json.dumps(empty_out(args.scope, args.query, args.time_range), ensure_ascii=False, indent=2))
        return

    results = []
    sess_turn = {}      # session -> 当前轮次（仅计 user/assistant）
    sess_titles = {}    # session -> ai-title

    for fp in iter_files(root, args.scope, args.cwd):
        slug = os.path.basename(os.path.dirname(fp))
        sid = os.path.splitext(os.path.basename(fp))[0]
        records, title = load_parsed(fp)
        if title:
            sess_titles[sid] = title
        for ts, text, role in records:
            if not in_time_range(ts, args.time_range, args.time_start, args.time_end):
                continue
            low = text.lower()
            if not any(tok.lower() in low for tok in terms):
                continue
            if role in ("user", "assistant"):
                sess_turn[sid] = sess_turn.get(sid, 0) + 1
            sc = score_text(text, terms)
            if sc <= 0:
                continue
            pos_idx = sess_turn.get(sid, 0)
            code = None
            if not args.no_code:
                m = CODE_RE.search(text)
                if m:
                    code = m.group(1).strip()
            snippet = make_snippet(text, terms)
            dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).astimezone()
            results.append({
                "session_id": sid,
                "session_title": sess_titles.get(sid),
                "project_name": slug,
                "position": f"第 {pos_idx} 轮" if args.scope == "current" else (sess_titles.get(sid) or sid[:8]),
                "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "match_score": round(sc, 1),
                "summary": snippet,
                "code_snippet": code,
                "highlight": [t for t in terms if t.lower() in text.lower()],
                "_ts": ts,
            })

    if args.sort_by == "time":
        results.sort(key=lambda r: r["_ts"], reverse=True)
    else:
        results.sort(key=lambda r: r["match_score"], reverse=True)
    results = results[: args.max_results]
    for r in results:
        r.pop("_ts", None)

    if results:
        out = {
            "search_scope": args.scope,
            "total_results": len(results),
            "results": results,
            "expand_suggestion": None,
            "suggestions": {"related_queries": [], "time_range_rewrites": []},
        }
    else:
        out = empty_out(args.scope, args.query, args.time_range)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
