#!/usr/bin/env python3
"""
HOMES dashboard: a local, browser-based front end for the HOMES workflows.

Start it from the repository root:

    python3 dashboard/homes_dashboard.py

and open the printed address (default http://127.0.0.1:8765). The dashboard
uses only the Python standard library, so no extra packages are needed.

It lets you:
  * check that Nextflow, Java and a container engine are installed,
  * build samplesheets (including auto-detection of FASTQ files in a folder),
  * fill in a guided form and launch HOMES_amplicon, HOMES_metagenomics or
    HOMES_assembly,
  * follow running analyses live and stop them,
  * open the HTML reports and preview result tables.

Security notes: the server binds to 127.0.0.1 by default, rejects requests
whose Host header is not the address it listens on, requires a per-session
token (cookie + header) for every API call, and launches only
`nextflow run workflows/HOMES_*` without a shell.
"""

import argparse
import csv
import datetime as _dt
import http.server
import io
import json
import mimetypes
import os
import re
import secrets
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

DASHBOARD_DIR = Path(__file__).resolve().parent
REPO_ROOT = DASHBOARD_DIR.parent
STATIC_DIR = DASHBOARD_DIR / "static"
STATE_DIR = REPO_ROOT / ".homes_dashboard"
RUNS_DIR = STATE_DIR / "runs"
RESULT_DIRS_FILE = STATE_DIR / "result_dirs.json"

WORKFLOWS = ("HOMES_amplicon", "HOMES_metagenomics", "HOMES_assembly")
FASTQ_RE = re.compile(r"\.(fastq|fq)(\.gz)?$", re.IGNORECASE)
PAIR_RE = re.compile(
    r"^(?P<name>.+?)(?:[._-](?:S\d+))?(?:[._-]L\d{3})?[._-](?:R)?(?P<read>[12])(?:[._-]\d{3})?\.(?:fastq|fq)(?:\.gz)?$",
    re.IGNORECASE,
)
TABLE_EXT = (".tsv", ".csv", ".txt")
MAX_TABLE_ROWS = 200

TOKEN = secrets.token_urlsafe(24)
COOKIE_NAME = "homes_dashboard_token"

_runs_lock = threading.Lock()
_procs = {}  # run_id -> subprocess.Popen


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _now():
    return _dt.datetime.now().isoformat(timespec="seconds")


def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def _resolve(path_str, base=REPO_ROOT):
    p = Path(os.path.expanduser(str(path_str)))
    if not p.is_absolute():
        p = base / p
    return p.resolve()


def _tool_version(cmd):
    exe = shutil.which(cmd[0])
    if not exe:
        return {"found": False, "version": None}
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        text = (out.stdout or "") + (out.stderr or "")
        line = next((l.strip() for l in text.splitlines() if l.strip()), "")
        return {"found": True, "version": line[:160], "path": exe}
    except (OSError, subprocess.SubprocessError):
        return {"found": True, "version": None, "path": exe}


def check_tools():
    tools = {
        "nextflow": _tool_version(["nextflow", "-version"]),
        "java": _tool_version(["java", "-version"]),
        "docker": _tool_version(["docker", "--version"]),
        "singularity": _tool_version(["singularity", "--version"]),
        "apptainer": _tool_version(["apptainer", "--version"]),
        "sbatch": {"found": bool(shutil.which("sbatch")), "version": None},
        "qsub": {"found": bool(shutil.which("qsub")), "version": None},
    }
    # Nextflow's -version output starts with a blank/banner line; find the version line.
    if tools["nextflow"]["found"]:
        try:
            out = subprocess.run(["nextflow", "-version"], capture_output=True, text=True, timeout=30)
            m = re.search(r"version\s+([0-9][^\s]*)", out.stdout + out.stderr)
            if m:
                tools["nextflow"]["version"] = m.group(1)
        except (OSError, subprocess.SubprocessError):
            pass
    if tools["docker"]["found"]:
        try:
            ok = subprocess.run(["docker", "info"], capture_output=True, timeout=20).returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
        tools["docker"]["running"] = ok
    return tools


# --------------------------------------------------------------------------- #
# Runs
# --------------------------------------------------------------------------- #

def _run_dir(run_id):
    if not re.fullmatch(r"[0-9A-Za-z_-]+", run_id or ""):
        raise ValueError("bad run id")
    return RUNS_DIR / run_id


def validate_argv(argv):
    if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
        raise ValueError("argv must be a list of strings")
    if len(argv) < 3 or argv[0] != "nextflow" or argv[1] != "run":
        raise ValueError("only 'nextflow run workflows/HOMES_*' can be launched")
    target = argv[2].rstrip("/")
    if target not in {f"workflows/{w}" for w in WORKFLOWS}:
        raise ValueError(f"unknown workflow: {argv[2]}")
    for a in argv:
        if "\x00" in a or "\n" in a:
            raise ValueError("arguments may not contain newlines")
    return target.split("/", 1)[1]


def _arg_value(argv, flag):
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            return argv[i + 1]
    return None


def start_run(argv, label=""):
    workflow = validate_argv(argv)
    if shutil.which("nextflow") is None:
        raise ValueError("Nextflow was not found on PATH. Open the 'Setup' tab for install steps.")
    run_id = _dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
    rdir = _run_dir(run_id)
    rdir.mkdir(parents=True, exist_ok=True)

    full_argv = list(argv)
    if "-ansi-log" not in full_argv:
        full_argv += ["-ansi-log", "false"]
    outdir = _arg_value(full_argv, "--outdir")
    meta = {
        "id": run_id,
        "label": label or workflow,
        "workflow": workflow,
        "platform": _arg_value(full_argv, "--platform"),
        "profile": _arg_value(full_argv, "-profile"),
        "argv": full_argv,
        "outdir": str(_resolve(outdir)) if outdir else None,
        "started": _now(),
        "finished": None,
        "status": "running",
        "exit_code": None,
        "pid": None,
    }
    log_fh = open(rdir / "nextflow.out.log", "wb")
    popen_kwargs = {}
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        full_argv,
        cwd=str(REPO_ROOT),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "NXF_ANSI_LOG": "false"},
        **popen_kwargs,
    )
    meta["pid"] = proc.pid
    _write_json(rdir / "meta.json", meta)
    with _runs_lock:
        _procs[run_id] = proc
    if meta["outdir"]:
        remember_result_dir(meta["outdir"])

    def _wait():
        code = proc.wait()
        log_fh.close()
        with _runs_lock:
            m = _read_json(rdir / "meta.json", meta)
            m["exit_code"] = code
            m["finished"] = _now()
            if m.get("status") != "stopped":
                m["status"] = "succeeded" if code == 0 else "failed"
            _write_json(rdir / "meta.json", m)
            _procs.pop(run_id, None)

    threading.Thread(target=_wait, daemon=True).start()
    return meta


def stop_run(run_id):
    rdir = _run_dir(run_id)
    with _runs_lock:
        proc = _procs.get(run_id)
        meta = _read_json(rdir / "meta.json", None)
        if meta is None:
            raise ValueError("run not found")
        if proc is None or proc.poll() is not None:
            return meta
        meta["status"] = "stopped"
        _write_json(rdir / "meta.json", meta)
    # Nextflow cleans up its tasks on SIGTERM; signal only the Nextflow process
    # so it can cancel submitted jobs itself.
    try:
        proc.send_signal(signal.SIGTERM)
    except OSError:
        pass
    return meta


def list_runs():
    runs = []
    if RUNS_DIR.exists():
        for d in sorted(RUNS_DIR.iterdir(), reverse=True):
            meta = _read_json(d / "meta.json", None)
            if not meta:
                continue
            with _runs_lock:
                if meta.get("status") == "running" and meta["id"] not in _procs:
                    # Dashboard restarted while this run was going; we no longer own it.
                    meta["status"] = "unknown"
            meta["progress"] = parse_progress(d / "nextflow.out.log")
            runs.append(meta)
    return runs


SUBMIT_RE = re.compile(r"\[([0-9a-f]{2}/[0-9a-f]{6,})\]\s+(Submitted|Cached) process > ([^\s(]+)")
ERROR_RE = re.compile(r"^(ERROR ~|Error executing process|ERROR:|Caused by:)", re.MULTILINE)


def parse_progress(log_path):
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return {"steps": [], "submitted": 0, "cached": 0, "error": None}
    steps = {}
    submitted = cached = 0
    for m in SUBMIT_RE.finditer(text):
        name = m.group(3).split(":")[-1]
        kind = m.group(2)
        if kind == "Cached":
            cached += 1
        else:
            submitted += 1
        s = steps.setdefault(name, {"name": name, "tasks": 0, "cached": 0})
        s["tasks"] += 1
        if kind == "Cached":
            s["cached"] += 1
    err = None
    m = ERROR_RE.search(text)
    if m:
        err = text[m.start(): m.start() + 1500].strip()
    return {"steps": list(steps.values()), "submitted": submitted, "cached": cached, "error": err}


def read_log(run_id, offset):
    path = _run_dir(run_id) / "nextflow.out.log"
    try:
        size = path.stat().st_size
    except OSError:
        return {"text": "", "offset": 0}
    offset = max(0, min(int(offset or 0), size))
    if offset == 0 and size > 400_000:
        offset = size - 400_000
    with open(path, "rb") as fh:
        fh.seek(offset)
        data = fh.read(1_000_000)
    return {"text": data.decode("utf-8", errors="replace"), "offset": offset + len(data)}


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #

def remember_result_dir(path):
    dirs = _read_json(RESULT_DIRS_FILE, [])
    p = str(_resolve(path))
    if p not in dirs:
        dirs.append(p)
        _write_json(RESULT_DIRS_FILE, dirs)


def forget_result_dir(path):
    dirs = [d for d in _read_json(RESULT_DIRS_FILE, []) if d != str(_resolve(path))]
    _write_json(RESULT_DIRS_FILE, dirs)


def allowed_roots():
    roots = [REPO_ROOT]
    roots += [Path(d) for d in _read_json(RESULT_DIRS_FILE, [])]
    return roots


def is_allowed(path):
    p = Path(path).resolve()
    for root in allowed_roots():
        try:
            p.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _guess_workflow(path):
    name = path.name.lower()
    for w in WORKFLOWS:
        if w.lower() in name:
            return w
    if (path / "nanopore").is_dir() or (path / "dada2").is_dir():
        return "HOMES_amplicon"
    if (path / "binning").is_dir() or (path / "assembly").is_dir():
        return "HOMES_assembly"
    if (path / "taxonomy").is_dir() or (path / "abundance").is_dir():
        return "HOMES_metagenomics"
    return None


def describe_result_dir(path):
    path = Path(path)
    info = {
        "path": str(path),
        "name": path.name,
        "exists": path.is_dir(),
        "workflow": _guess_workflow(path),
        "reports": [],
        "tables": [],
        "modified": None,
    }
    if not path.is_dir():
        return info
    info["modified"] = _dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    reports, tables = [], []
    for root, dirs, files in os.walk(path):
        rel_depth = len(Path(root).relative_to(path).parts)
        # Skip deep/noisy folders (per-sample intermediates).
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "work"]
        if rel_depth >= 4:
            dirs[:] = []
        for f in files:
            fp = Path(root) / f
            rel = str(fp.relative_to(path))
            low = f.lower()
            if low.endswith(".html"):
                kind = "pipeline" if rel.startswith("pipeline_info") else (
                    "qc" if "multiqc" in rel.lower() or "fastqc" in rel.lower() else "report")
                if kind == "qc" and "fastqc" in rel.lower():
                    continue  # one FastQC page per file: too noisy, MultiQC summarises them
                reports.append({"path": str(fp), "rel": rel, "kind": kind, "size": fp.stat().st_size})
            elif low.endswith(TABLE_EXT) and not rel.startswith("pipeline_info"):
                if any(k in low for k in ("summary", "abundance", "stats", "diversity", "taxonomy", "counts", "annotation")):
                    tables.append({"path": str(fp), "rel": rel, "size": fp.stat().st_size})
    order = {"report": 0, "qc": 1, "pipeline": 2}
    reports.sort(key=lambda r: (order[r["kind"]], r["rel"]))
    tables.sort(key=lambda t: t["rel"])
    info["reports"] = reports
    info["tables"] = tables[:60]
    return info


def list_results():
    seen, out = set(), []
    candidates = []
    results_root = REPO_ROOT / "results"
    if results_root.is_dir():
        candidates += [p for p in results_root.iterdir() if p.is_dir()]
    candidates += [Path(d) for d in _read_json(RESULT_DIRS_FILE, [])]
    for c in candidates:
        key = str(c.resolve()) if c.exists() else str(c)
        if key in seen:
            continue
        seen.add(key)
        out.append(describe_result_dir(Path(key)))
    out.sort(key=lambda r: r["modified"] or "", reverse=True)
    return out


def read_table(path):
    p = _resolve(path)
    if not is_allowed(p):
        raise PermissionError("path is outside the HOMES folder and known result folders")
    delim = "," if p.suffix.lower() == ".csv" else "\t"
    rows, total = [], 0
    with open(p, "r", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.reader(fh, delimiter=delim):
            total += 1
            if len(rows) <= MAX_TABLE_ROWS:
                rows.append(row)
    return {"path": str(p), "header": rows[0] if rows else [], "rows": rows[1:], "total_rows": max(0, total - 1)}


# --------------------------------------------------------------------------- #
# Files / samplesheets
# --------------------------------------------------------------------------- #

def browse(path):
    p = _resolve(path or str(REPO_ROOT))
    if p.is_file():
        p = p.parent
    entries = []
    try:
        for e in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if e.name.startswith("."):
                continue
            try:
                is_dir = e.is_dir()
                size = None if is_dir else e.stat().st_size
            except OSError:
                continue
            entries.append({"name": e.name, "path": str(e), "dir": is_dir, "size": size})
    except PermissionError:
        raise PermissionError(f"cannot read {p}")
    return {"path": str(p), "parent": str(p.parent) if p.parent != p else None, "entries": entries[:2000],
            "repo": str(REPO_ROOT)}


def _sanitize_sample(name):
    s = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_") or "sample"
    if not s[0].isalpha():
        s = "S" + s
    return s


def scan_fastq(directory, recursive=False):
    d = _resolve(directory)
    if not d.is_dir():
        raise ValueError(f"not a folder: {d}")
    files = []
    it = d.rglob("*") if recursive else d.iterdir()
    for f in it:
        if f.is_file() and FASTQ_RE.search(f.name):
            files.append(f)
    files.sort()
    groups = {}
    for f in files:
        m = PAIR_RE.match(f.name)
        if m:
            key = (str(f.parent), m.group("name"))
            groups.setdefault(key, {})[m.group("read")] = f
        else:
            key = (str(f.parent), FASTQ_RE.sub("", f.name))
            groups.setdefault(key, {})["1"] = f
    rows, used = [], set()
    for (_parent, name), reads in sorted(groups.items()):
        sample = _sanitize_sample(name)
        base, n = sample, 2
        while sample in used:
            sample, n = f"{base}_{n}", n + 1
        used.add(sample)
        r1, r2 = reads.get("1"), reads.get("2")
        if r1 is None and r2 is not None:
            r1, r2 = r2, None
        rows.append({
            "sample": sample,
            "fastq_1": str(r1),
            "fastq_2": str(r2) if r2 else "",
            "read_layout": "paired" if r2 else "single",
        })
    return {"folder": str(d), "rows": rows, "files": len(files)}


def save_text_file(path, content, overwrite=False):
    p = _resolve(path)
    if p.suffix.lower() not in (".csv", ".tsv"):
        raise ValueError("samplesheets must end with .csv or .tsv")
    if p.exists() and not overwrite:
        raise FileExistsError(f"{p} already exists")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)
    return {"path": str(p)}


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "HOMESDashboard/1.0"
    allowed_hosts = set()

    def log_message(self, fmt, *args):
        if os.environ.get("HOMES_DASHBOARD_VERBOSE"):
            super().log_message(fmt, *args)

    # -- plumbing ----------------------------------------------------------- #
    def _host_ok(self):
        host = (self.headers.get("Host") or "").lower()
        return host in self.allowed_hosts

    def _cookie_token(self):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE_NAME:
                return v
        return None

    def _authed(self, require_header):
        if not secrets.compare_digest(self._cookie_token() or "", TOKEN):
            return False
        if require_header and not secrets.compare_digest(self.headers.get("X-HOMES-Token") or "", TOKEN):
            return False
        return True

    def _send(self, code, body, ctype="application/json", extra_headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, msg):
        self._send(code, {"error": msg})

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 20_000_000:
            raise ValueError("request too large")
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    # -- routes ------------------------------------------------------------- #
    def do_GET(self):
        if not self._host_ok():
            return self._error(403, "bad host")
        url = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        path = url.path

        if path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/static/index.html")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        if path == "/static/index.html":
            html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
            html = html.replace("__HOMES_TOKEN__", TOKEN)
            cookie = f"{COOKIE_NAME}={TOKEN}; Path=/; HttpOnly; SameSite=Strict"
            return self._send(200, html, "text/html; charset=utf-8", {"Set-Cookie": cookie})

        if path.startswith("/static/"):
            fp = (STATIC_DIR / urllib.parse.unquote(path[len("/static/"):])).resolve()
            if STATIC_DIR not in fp.parents or not fp.is_file():
                return self._error(404, "not found")
            ctype = mimetypes.guess_type(fp.name)[0] or "application/octet-stream"
            return self._send(200, fp.read_bytes(), ctype)

        if path.startswith("/workflows/"):
            # Logos/figures that live in the workflows folder (the page links them as ../../workflows/...).
            fp = (REPO_ROOT / "workflows" / urllib.parse.unquote(path[len("/workflows/"):])).resolve()
            if (REPO_ROOT / "workflows") not in fp.parents or not fp.is_file() or fp.suffix.lower() not in (".svg", ".png"):
                return self._error(404, "not found")
            return self._send(200, fp.read_bytes(), mimetypes.guess_type(fp.name)[0])

        if not self._authed(require_header=False):
            return self._error(401, "reload the dashboard page")

        if path.startswith("/files/"):
            fp = Path(urllib.parse.unquote(path[len("/files"):])).resolve()
            if not is_allowed(fp) or not fp.is_file():
                return self._error(404, "not found")
            ctype = mimetypes.guess_type(fp.name)[0] or "text/plain"
            if ctype.startswith("text/") or ctype in ("application/json",):
                ctype += "; charset=utf-8"
            return self._send(200, fp.read_bytes(), ctype)

        try:
            if path == "/api/status":
                return self._send(200, {"server": True, "repo": str(REPO_ROOT), "tools": check_tools(),
                                        "platform": sys.platform})
            if path == "/api/runs":
                return self._send(200, {"runs": list_runs()})
            m = re.fullmatch(r"/api/runs/([^/]+)/log", path)
            if m:
                return self._send(200, read_log(m.group(1), q.get("offset", 0)))
            if path == "/api/results":
                return self._send(200, {"results": list_results()})
            if path == "/api/table":
                return self._send(200, read_table(q.get("path", "")))
            if path == "/api/browse":
                return self._send(200, browse(q.get("path")))
        except PermissionError as e:
            return self._error(403, str(e))
        except (ValueError, OSError) as e:
            return self._error(400, str(e))
        return self._error(404, "not found")

    def do_POST(self):
        if not self._host_ok():
            return self._error(403, "bad host")
        if not self._authed(require_header=True):
            return self._error(401, "reload the dashboard page")
        path = urllib.parse.urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/run":
                return self._send(200, start_run(body.get("argv"), body.get("label", "")))
            m = re.fullmatch(r"/api/runs/([^/]+)/stop", path)
            if m:
                return self._send(200, stop_run(m.group(1)))
            if path == "/api/scan-fastq":
                return self._send(200, scan_fastq(body.get("folder", ""), bool(body.get("recursive"))))
            if path == "/api/save-samplesheet":
                return self._send(200, save_text_file(body.get("path", ""), body.get("content", ""),
                                                      bool(body.get("overwrite"))))
            if path == "/api/results/add":
                p = _resolve(body.get("path", ""))
                if not p.is_dir():
                    raise ValueError(f"not a folder: {p}")
                remember_result_dir(p)
                return self._send(200, describe_result_dir(p))
            if path == "/api/results/forget":
                forget_result_dir(body.get("path", ""))
                return self._send(200, {"ok": True})
        except FileExistsError as e:
            return self._error(409, str(e))
        except PermissionError as e:
            return self._error(403, str(e))
        except (ValueError, OSError, json.JSONDecodeError) as e:
            return self._error(400, str(e))
        return self._error(404, "not found")


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    ap = argparse.ArgumentParser(description="HOMES workflow dashboard")
    ap.add_argument("--host", default="127.0.0.1",
                    help="address to listen on (default 127.0.0.1 = this computer only)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    args = ap.parse_args()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingServer((args.host, args.port), Handler)
    port = httpd.server_address[1]
    hosts = {f"{args.host}:{port}", f"127.0.0.1:{port}", f"localhost:{port}"}
    if args.host not in ("127.0.0.1", "localhost"):
        print("WARNING: the dashboard is reachable from other machines. Anyone who can reach this "
              "port and load the page can launch Nextflow runs as your user.")
        hosts.add(f"{socketserver.socket.gethostname().lower()}:{port}")
    Handler.allowed_hosts = {h.lower() for h in hosts}

    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '') else args.host}:{port}/"
    Handler.allowed_hosts.add(urllib.parse.urlparse(url).netloc.lower())
    print(f"HOMES dashboard running at {url}  (press Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard. Running analyses keep going in the background.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
