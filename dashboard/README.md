# HOMES Dashboard

A point-and-click web dashboard for the HOMES workflows. It is meant for people who would rather not type
Nextflow commands: pick an analysis, point it at your data, press **Start**, follow progress, and open the
HTML report.

It needs only Python 3.8+ (standard library, nothing to `pip install`) plus the usual HOMES requirements
(Java 17+, Nextflow, Docker or Singularity).

## Before you start

Install these once, in this order:

| # | What | Why | How (macOS) |
| --- | --- | --- | --- |
| 1 | **Docker Desktop** | Provides all bioinformatics tools (fastp, Kraken2, DADA2, …) automatically | [Download](https://docs.docker.com/get-started/get-docker/), install, open it once and wait until it says *running* |
| 2 | **Java 17 or newer** | Nextflow runs on Java | Install [Temurin 17](https://adoptium.net/temurin/releases/?version=17) |
| 3 | **Nextflow** | Runs the HOMES workflows | See [Installation](../README.md#nextflow) in the main README |
| 4 | **HOMES** | The workflows and this dashboard | `git clone https://github.com/Harper19/HOMES.git` or *Code → Download ZIP* on GitHub |
| 5 | Python 3 | Runs the dashboard | Usually already there. If not, typing `python3` in Terminal offers to install it |
| – | Chrome or Edge (optional) | Opens the dashboard as its own app window | Without it, the dashboard opens in Safari / your default browser |

Then check everything in one go from the HOMES folder:

```bash
python3 dashboard/homes_dashboard.py --check
```

It lists what is ready (✓), what needs attention (!) and what is missing (✗), with download links.
The same checks are on the dashboard's **Setup** tab.

Good to know:

- **Open Docker Desktop before every analysis.** The dashboard warns you if Docker is not running.
- **The first run needs internet and takes longer.** Docker downloads the software images, and
  metagenomics downloads its Kraken2 database (Standard-8 ≈ 8 GB). Later runs reuse both.
- **Disk space:** keep at least 30–50 GB free for containers, databases and intermediate files
  (about 45 GB more for eggNOG functional annotation). Old `work/` folders can be deleted after a run finishes.
- **Memory:** 8 GB is enough for the built-in test data and most amplicon runs. Use 16 GB or more for real
  metagenomics or assembly, and give Docker that memory in *Docker Desktop → Settings → Resources*.
- **Windows:** Nextflow does not run on Windows directly. Install
  [WSL2](https://learn.microsoft.com/windows/wsl/install) (Ubuntu), then install Java, Nextflow and HOMES
  inside it and start the dashboard from the Ubuntu terminal. The Windows `.bat` launcher alone cannot run
  analyses.
- **First analysis:** choose *Built-in test data* in **New analysis** to confirm everything works before
  using your own samples.

## Start

From the HOMES folder:

```bash
python3 dashboard/homes_dashboard.py
```

The dashboard opens in its own window at <http://127.0.0.1:8765>. If Chrome, Edge, Chromium or Brave is
installed, this is an app window without tabs or address bar; otherwise it opens in your default browser.
Stop the dashboard with `Ctrl+C` or **Setup → Quit dashboard**; analyses that are already running keep going.

## Use it like a desktop app

Run this once from the HOMES folder:

```bash
python3 dashboard/homes_dashboard.py --install-app
```

| System | What gets created |
| --- | --- |
| macOS | `~/Applications/HOMES Dashboard.app` – open it from Finder, Spotlight or Launchpad, or drag it to the Dock. |
| Windows | `HOMES Dashboard.bat` on the Desktop. |
| Linux | A *HOMES Dashboard* entry in the applications menu. |

Double-clicking starts the dashboard in the background and opens its window. If it is already running, the
existing dashboard is reopened instead of starting a second one. The app points at this HOMES folder, so
re-run `--install-app` if you move the folder. Messages from the dashboard are written to
`.homes_dashboard/dashboard.log`.

The app is started through your login shell (macOS) and also looks in the usual install folders
(`~/.local/bin`, Homebrew, conda, Docker Desktop), so Nextflow and Docker are found even though no terminal
is open.

Without installing anything, you can also double-click one of the files in `dashboard/launchers/`
(`HOMES Dashboard.command` on macOS, `HOMES Dashboard.bat` on Windows, `homes-dashboard.sh` on Linux).
In Chrome or Edge you can additionally use the *Install* icon in the address bar to add the page as an app.

Options:

```bash
python3 dashboard/homes_dashboard.py --port 9000        # use another port
python3 dashboard/homes_dashboard.py --no-browser       # don't open a window automatically
python3 dashboard/homes_dashboard.py --browser          # open in a normal browser tab instead of an app window
python3 dashboard/homes_dashboard.py --check            # check that this computer is ready, then exit
```

On a remote server, keep the default address and use an SSH tunnel instead of opening the port:

```bash
ssh -L 8765:127.0.0.1:8765 user@server
# then on the server:  python3 dashboard/homes_dashboard.py --no-browser
# and on your laptop open http://127.0.0.1:8765
```

## What it does

| Tab | Purpose |
| --- | --- |
| **Home** | Choose a workflow by the question you want answered; see recent runs and missing software. |
| **New analysis** | Step-by-step form: workflow → sequencing platform → test data or your own data → Docker / Singularity / SLURM / PBS → options (with plain-language help) → results folder. Shows the exact Nextflow command, checks for missing inputs, and starts the run. The command can also be copied or downloaded as a `.sh` script. |
| **Samplesheet** | Build samplesheets for each workflow. *Add files from a folder* finds FASTQ files and pairs R1/R2 automatically; you can also paste rows from Excel or import a CSV/TSV. Checks for duplicate or invalid sample names and missing files, then saves the file and fills it into the form. |
| **Runs** | Live progress of every run started from the dashboard: steps started, live log, plain-language hints when something fails (Docker not running, missing file, out of memory…), and a Stop button. |
| **Results** | Lists result folders (`results/` and any folder you add) with one-click buttons for the HTML reports and MultiQC, plus a preview of summary / abundance tables. |
| **Setup** | Checks whether Java, Nextflow, Docker, Singularity/Apptainer and an HPC scheduler are available and shows install steps. |

## Command-builder mode (no server)

Opening `dashboard/static/index.html` directly in a browser (or hosting the `static/` folder on any
web server, e.g. GitHub Pages) gives a reduced version: the guided form, the command preview, script
download and the samplesheet builder all work, but starting runs, browsing files and opening results
need the Python server.

## Files

```text
dashboard/
  homes_dashboard.py     # local web server + run manager + app installer (stdlib only)
  launchers/             # double-click launchers for macOS / Windows / Linux
  static/index.html      # page layout
  static/app.js          # dashboard logic
  static/workflows.js    # workflow catalogue: options, defaults, help texts, samplesheet layouts
  static/style.css       # styles (light and dark)
  static/icon*.{svg,png}, static/manifest.webmanifest   # app icon and install metadata
```

Run logs and dashboard state are stored in `.homes_dashboard/` in the HOMES folder (ignored by Git).

To expose a new workflow option in the form, add an entry to the workflow's `fields` list in
`static/workflows.js`. Keep its `default` equal to the value in the workflow's `nextflow.config` so the
option is only added to the command when the user changes it.

## Security

The dashboard can start programs on your computer, so by default it:

- listens on `127.0.0.1` only (not reachable from other machines);
- rejects requests whose `Host` header is not the dashboard's own address (blocks DNS rebinding);
- requires a random per-session token (cookie + header) for every API call;
- only launches `nextflow run workflows/HOMES_*`, without a shell;
- serves result files only from inside the HOMES folder and result folders you have added.

Using `--host 0.0.0.0` makes it reachable from your network; anyone who can open the page could then start
runs as your user. Prefer an SSH tunnel.
