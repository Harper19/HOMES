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
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("Picked up ")]
        line = next((l for l in lines if "version" in l.lower()), lines[0] if lines else "")
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


LINKS = {
    "docker": "https://docs.docker.com/get-started/get-docker/",
    "java": "https://adoptium.net/temurin/releases/?version=17",
    "nextflow": "https://www.nextflow.io/docs/latest/install.html",
    "wsl": "https://learn.microsoft.com/windows/wsl/install",
    "chrome": "https://www.google.com/chrome/",
}
MIN_DISK_GB = 30
MIN_RAM_GB = 8
GOOD_RAM_GB = 16


def _java_major(version_line):
    m = re.search(r'version "?(\d+)(?:\.(\d+))?', version_line or "")
    if not m:
        return None
    major = int(m.group(1))
    return int(m.group(2) or 0) if major == 1 else major  # "1.8.0" means Java 8


def _total_ram_gb():
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5)
            return int(out.stdout.strip()) / 1024 ** 3
        if sys.platform.startswith("linux"):
            with open("/proc/meminfo") as fh:
                for line in fh:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / 1024 ** 2
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


def _docker_ram_gb():
    try:
        out = subprocess.run(["docker", "info", "--format", "{{.MemTotal}}"], capture_output=True, text=True, timeout=20)
        return int(out.stdout.strip()) / 1024 ** 3 if out.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def system_checks(tools=None):
    """Everything a user needs before running HOMES, as a list of plain-language checks.

    status: ok | warn (works, but read the note) | missing (must fix) | optional (not needed for most users)
    """
    tools = tools or check_tools()
    checks = []

    def add(cid, title, status, detail, fix=None, link=None):
        checks.append({"id": cid, "title": title, "status": status, "detail": detail, "fix": fix, "link": link})

    if os.name == "nt":
        add("os", "Operating system", "missing", "Windows cannot run Nextflow directly.",
            "Install WSL2 (Ubuntu), then install Java, Nextflow and HOMES inside it and start the dashboard from there.",
            LINKS["wsl"])
    else:
        add("os", "Operating system", "ok", {"darwin": "macOS"}.get(sys.platform, "Linux"))

    add("python", "Python", "ok", "Python " + ".".join(map(str, sys.version_info[:3])))

    j = tools["java"]
    major = _java_major(j.get("version")) if j["found"] else None
    if not j["found"]:
        add("java", "Java 17 or newer", "missing", "Java was not found.", "Install Temurin 17 (or newer) and restart the dashboard.", LINKS["java"])
    elif major is not None and major < 17:
        add("java", "Java 17 or newer", "missing", f"Java {major} is too old for Nextflow.", "Install Temurin 17 (or newer).", LINKS["java"])
    else:
        add("java", "Java 17 or newer", "ok", j.get("version") or "found")

    n = tools["nextflow"]
    if n["found"]:
        add("nextflow", "Nextflow", "ok", "Version " + (n.get("version") or "?"))
    else:
        add("nextflow", "Nextflow", "missing", "Nextflow was not found.",
            'Run: curl -s https://get.nextflow.io | bash && mkdir -p ~/.local/bin && mv nextflow ~/.local/bin/', LINKS["nextflow"])

    d = tools["docker"]
    other_engine = tools["singularity"]["found"] or tools["apptainer"]["found"]
    if d["found"] and d.get("running"):
        add("docker", "Docker", "ok", d.get("version") or "running")
        mem = _docker_ram_gb()
        if mem is not None and mem < MIN_RAM_GB - 0.5:
            add("docker_mem", "Memory available to Docker", "warn", f"Docker may use only {mem:.0f} GB.",
                "Docker Desktop → Settings → Resources: give Docker at least 8 GB (16 GB+ for real metagenomics / assembly).")
        elif mem is not None:
            add("docker_mem", "Memory available to Docker", "ok", f"{mem:.0f} GB")
    elif d["found"]:
        add("docker", "Docker", "warn" if other_engine else "missing", "Installed but not running.",
            "Open Docker Desktop and wait until it says it is running. Do this every time before you start an analysis.")
    elif other_engine:
        add("docker", "Docker", "optional", "Not found. Singularity/Apptainer will be used instead (servers/HPC).")
    else:
        add("docker", "Docker", "missing", "No container engine found.",
            "Install Docker Desktop. It provides all the bioinformatics software automatically.", LINKS["docker"])

    if other_engine:
        t = tools["singularity"] if tools["singularity"]["found"] else tools["apptainer"]
        add("singularity", "Singularity / Apptainer", "ok", t.get("version") or "found")

    try:
        free = int(shutil.disk_usage(REPO_ROOT).free / 1024 ** 3)
        if free < 10:
            add("disk", "Free disk space", "missing", f"Only {free:.0f} GB free.",
                f"Free at least {MIN_DISK_GB} GB: containers, databases (Standard-8 ≈ 8 GB, eggNOG ≈ 45 GB) and intermediate files need room.")
        elif free < MIN_DISK_GB:
            add("disk", "Free disk space", "warn", f"{free:.0f} GB free.",
                f"Enough for test runs. Real analyses need {MIN_DISK_GB}–50 GB+ (more with eggNOG functional annotation).")
        else:
            add("disk", "Free disk space", "ok", f"{free:.0f} GB free")
    except OSError:
        pass

    ram = _total_ram_gb()
    if ram is not None:
        if ram < MIN_RAM_GB - 0.5:
            add("ram", "Memory (RAM)", "warn", f"{ram:.0f} GB.", "Test runs may work; real analyses need 16 GB or more, or a server.")
        elif ram < GOOD_RAM_GB - 0.5:
            add("ram", "Memory (RAM)", "warn", f"{ram:.0f} GB.", "Fine for amplicon and test runs; metagenomics / assembly work best with 16 GB+.")
        else:
            add("ram", "Memory (RAM)", "ok", f"{ram:.0f} GB")

    add("chrome", "Chrome or Edge", "ok" if _app_browser() else "optional",
        "Found – the dashboard opens in its own app window." if _app_browser()
        else "Not found – the dashboard opens in your normal browser instead.", None, None if _app_browser() else LINKS["chrome"])
    return checks


def print_checks():
    """Terminal version of the Setup page. Returns the exit code (1 when something must be fixed)."""
    color = sys.stdout.isatty() and os.name != "nt"
    marks = {"ok": ("✓", "32"), "warn": ("!", "33"), "missing": ("✗", "31"), "optional": ("–", "90")}
    print("\nHOMES setup check\n")
    checks = system_checks()
    for c in checks:
        sym, code = marks[c["status"]]
        sym = f"\033[{code}m{sym}\033[0m" if color else sym
        print(f"  {sym} {c['title']}: {c['detail']}")
        if c["fix"] and c["status"] in ("missing", "warn"):
            print(f"      → {c['fix']}")
        if c["link"] and c["status"] != "ok":
            print(f"      → {c['link']}")
    missing = [c for c in checks if c["status"] == "missing"]
    print()
    if missing:
        print(f"{len(missing)} thing(s) to fix before running HOMES: " + ", ".join(c["title"] for c in missing))
        return 1
    print("Ready. Start the dashboard with:  python3 dashboard/homes_dashboard.py")
    print("First run tip: choose 'Built-in test data' to confirm everything works.")
    return 0


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
    httpd = None

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
            if fp.suffix == ".webmanifest":
                ctype = "application/manifest+json"
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
                tools = check_tools()
                return self._send(200, {"server": True, "repo": str(REPO_ROOT), "tools": tools,
                                        "checks": system_checks(tools), "platform": sys.platform})
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
            if path == "/api/shutdown":
                threading.Thread(target=self.httpd.shutdown, daemon=True).start()
                return self._send(200, {"ok": True})
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


APP_NAME = "HOMES Dashboard"
DEFAULT_PORT = 8765


def _augment_path():
    """Apps started from Finder / a desktop menu get a minimal PATH; add the usual install locations."""
    extra = [
        Path.home() / ".local" / "bin",
        Path.home() / "bin",
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
        Path.home() / "miniforge3" / "bin",
        Path.home() / "miniconda3" / "bin",
        Path.home() / "anaconda3" / "bin",
        Path("/Applications/Docker.app/Contents/Resources/bin"),
    ]
    parts = os.environ.get("PATH", "").split(os.pathsep)
    for d in extra:
        if d.is_dir() and str(d) not in parts:
            parts.append(str(d))
    os.environ["PATH"] = os.pathsep.join(p for p in parts if p)


def _app_browser():
    """Find a Chromium-based browser that can open a page as a standalone app window."""
    candidates = []
    if sys.platform == "darwin":
        for app in ("Google Chrome", "Microsoft Edge", "Chromium", "Brave Browser"):
            for root in ("/Applications", str(Path.home() / "Applications")):
                exe = Path(root) / f"{app}.app" / "Contents" / "MacOS" / app
                candidates.append(str(exe))
    elif os.name == "nt":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base:
                candidates.append(os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"))
                candidates.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser"):
            exe = shutil.which(name)
            if exe:
                candidates.append(exe)
    return next((c for c in candidates if os.path.isfile(c)), None)


def open_window(url, mode="app"):
    """Open the dashboard: as an app window (no tabs / address bar) when possible, else a browser tab."""
    if mode == "app":
        exe = _app_browser()
        if exe:
            profile = STATE_DIR / "app-window-profile"
            try:
                subprocess.Popen(
                    [exe, f"--app={url}", f"--user-data-dir={profile}", "--window-size=1280,900",
                     "--no-first-run", "--no-default-browser-check"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=(os.name == "posix"))
                return
            except OSError:
                pass
    webbrowser.open(url)


def _already_running(port):
    """True if a HOMES dashboard already answers on this port."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/static/index.html", timeout=1.5) as r:
            return r.headers.get("Server", "").startswith("HOMESDashboard")
    except Exception:
        return False


def install_app():
    """Create a double-clickable launcher for this computer."""
    script = Path(__file__).resolve()
    python = sys.executable or "python3"
    log = STATE_DIR / "dashboard.log"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        app = Path.home() / "Applications" / f"{APP_NAME}.app"
        macos = app / "Contents" / "MacOS"
        macos.mkdir(parents=True, exist_ok=True)
        (app / "Contents" / "Info.plist").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>{APP_NAME}</string>
  <key>CFBundleDisplayName</key><string>{APP_NAME}</string>
  <key>CFBundleIdentifier</key><string>org.homes.dashboard</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>launch</string>
  <key>CFBundleIconFile</key><string>homes</string>
  <key>LSUIElement</key><true/>
</dict></plist>
""", encoding="utf-8")
        launcher = macos / "launch"
        # A login shell picks up the PATH set in ~/.zprofile / ~/.zshrc (Nextflow, Java, conda...).
        launcher.write_text(f"""#!/bin/zsh -l
exec "{python}" "{script}" >> "{log}" 2>&1
""", encoding="utf-8")
        launcher.chmod(0o755)
        _make_mac_icon(app / "Contents" / "Resources")
        print(f"Created {app}\nOpen it from Finder > Applications (your home folder), Spotlight, or drag it to the Dock.")
        return app
    if os.name == "nt":
        desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
        desktop.mkdir(parents=True, exist_ok=True)
        bat = desktop / f"{APP_NAME}.bat"
        pyw = Path(python).with_name("pythonw.exe")
        runner = pyw if pyw.exists() else Path(python)
        bat.write_text(f'@echo off\r\nstart "" "{runner}" "{script}"\r\n', encoding="utf-8")
        print(f"Created {bat} - double-click it to open the dashboard.")
        return bat
    apps = Path.home() / ".local" / "share" / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    desktop = apps / "homes-dashboard.desktop"
    icon = STATIC_DIR / "icon.svg"
    desktop.write_text(f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Run HOMES microbiome workflows
Exec=sh -c '"{python}" "{script}" >> "{log}" 2>&1'
Icon={icon}
Terminal=false
Categories=Science;Biology;
""", encoding="utf-8")
    desktop.chmod(0o755)
    print(f"Created {desktop}\nThe dashboard now appears in your applications menu.")
    return desktop


def _make_mac_icon(resources):
    """Best effort: turn icon.png into homes.icns with the macOS sips/iconutil tools."""
    resources.mkdir(parents=True, exist_ok=True)
    png = STATIC_DIR / "icon-512.png"
    if not png.exists() or not shutil.which("iconutil") or not shutil.which("sips"):
        return
    iconset = STATE_DIR / "homes.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    try:
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                px = size * scale
                name = f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
                subprocess.run(["sips", "-z", str(px), str(px), str(png), "--out", str(iconset / name)],
                               capture_output=True, check=True)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(resources / "homes.icns")],
                       capture_output=True, check=True)
    except (OSError, subprocess.SubprocessError):
        pass
    finally:
        shutil.rmtree(iconset, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="HOMES workflow dashboard")
    ap.add_argument("--host", default="127.0.0.1",
                    help="address to listen on (default 127.0.0.1 = this computer only)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-browser", action="store_true", help="do not open a window")
    ap.add_argument("--browser", action="store_true",
                    help="open in a normal browser tab instead of a standalone app window")
    ap.add_argument("--check", action="store_true",
                    help="check that Java, Nextflow, Docker, disk space and memory are ready, then exit")
    ap.add_argument("--install-app", action="store_true",
                    help="create a double-clickable app / menu entry for this computer and exit")
    args = ap.parse_args()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _augment_path()
    if args.check:
        sys.exit(print_checks())
    if args.install_app:
        install_app()
        return
    window_mode = "browser" if args.browser else "app"

    if _already_running(args.port):
        url = f"http://127.0.0.1:{args.port}/"
        print(f"HOMES dashboard is already running at {url} - opening it.")
        if not args.no_browser:
            open_window(url, window_mode)
        return

    httpd = ThreadingServer((args.host, args.port), Handler)
    port = httpd.server_address[1]
    hosts = {f"{args.host}:{port}", f"127.0.0.1:{port}", f"localhost:{port}"}
    if args.host not in ("127.0.0.1", "localhost"):
        print("WARNING: the dashboard is reachable from other machines. Anyone who can reach this "
              "port and load the page can launch Nextflow runs as your user.")
        hosts.add(f"{socketserver.socket.gethostname().lower()}:{port}")
    Handler.allowed_hosts = {h.lower() for h in hosts}
    Handler.httpd = httpd

    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '') else args.host}:{port}/"
    Handler.allowed_hosts.add(urllib.parse.urlparse(url).netloc.lower())
    print(f"HOMES dashboard running at {url}  (press Ctrl+C or use Setup > Quit dashboard to stop)")
    if not args.no_browser:
        threading.Timer(0.8, lambda: open_window(url, window_mode)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard. Running analyses keep going in the background.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
