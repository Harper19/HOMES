/* HOMES dashboard front end (no build step, no dependencies). */
(function () {
  "use strict";

  const WORKFLOWS = window.HOMES_WORKFLOWS;
  const ENGINES = window.HOMES_ENGINES;
  const SHEETS = window.HOMES_SAMPLESHEETS;
  const TOKEN = document.querySelector('meta[name="homes-token"]').content;
  const STORE_KEY = "homes-dashboard-v1";

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function h(tag, attrs, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k === "html") el.innerHTML = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else if (k === "dataset") Object.assign(el.dataset, v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      el.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return el;
  }

  // Like el.replaceChildren(), but skips null/false (the DOM would print them as text).
  function setKids(el, ...kids) {
    el.replaceChildren(...kids.flat().filter((c) => c != null && c !== false));
  }

  function toast(msg, ms) {
    const t = h("div", { class: "toast", role: "status" }, msg);
    document.body.append(t);
    setTimeout(() => t.remove(), ms || 2600);
  }

  function load() {
    try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch (e) { return {}; }
  }
  function save() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({ form: state.form, sheet: state.sheet }));
    } catch (e) { /* storage unavailable: fine */ }
  }

  const saved = load();
  const state = {
    server: false,
    status: null,
    view: "home",
    form: Object.assign(
      { wf: "HOMES_amplicon", platform: null, mode: "test", engine: "docker", values: {}, outdir: "", outdirTouched: false,
        label: "", resume: true, extra: "" },
      saved.form || {}
    ),
    sheet: Object.assign({ layout: "metagenomics", rows: [], path: "" }, saved.sheet || {}),
    runs: [],
    selectedRun: null,
    logOffset: 0,
    logRun: null,
  };

  // ------------------------------------------------------------------ API --
  async function api(path, body) {
    const opts = { headers: { "X-HOMES-Token": TOKEN }, credentials: "same-origin" };
    if (body !== undefined) {
      opts.method = "POST";
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    let data;
    try { data = await res.json(); } catch (e) { data = {}; }
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  async function detectServer() {
    if (TOKEN.startsWith("__") || !/^https?:$/.test(location.protocol)) return false;
    try {
      state.status = await api("/api/status");
      return true;
    } catch (e) {
      return false;
    }
  }

  // ----------------------------------------------------------- navigation --
  function show(view) {
    state.view = view;
    $$("section.view").forEach((s) => s.classList.toggle("active", s.id === "view-" + view));
    $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
    if (view === "runs") { state.detailSig = null; refreshRuns(); }
    if (view === "results") refreshResults();
    if (view === "setup") renderSetup();
    if (view === "sheet") renderSheet();
    window.scrollTo(0, 0);
    try { history.replaceState(null, "", "#" + view); } catch (e) { /* file:// */ }
  }
  document.addEventListener("click", (e) => {
    const g = e.target.closest("[data-goto]");
    if (g) { e.preventDefault(); show(g.dataset.goto); }
    const t = e.target.closest("#tabs button");
    if (t) show(t.dataset.view);
    const b = e.target.closest("[data-browse]");
    if (b) {
      e.preventDefault();
      const input = document.getElementById(b.dataset.browse);
      openBrowser({ mode: b.dataset.pick || "any", start: input.value, append: b.dataset.append }).then((p) => {
        if (p == null) return;
        input.value = p;
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
    }
  });

  // ------------------------------------------------------------- the form --
  const wfById = (id) => WORKFLOWS.find((w) => w.id === id) || WORKFLOWS[0];
  const curWf = () => wfById(state.form.wf);
  const curPlatform = () => {
    const wf = curWf();
    return wf.platforms.find((p) => p.id === state.form.platform) || wf.platforms[0];
  };

  function fieldDefault(f) {
    const p = curPlatform().id;
    if (f.platformDefault && p in f.platformDefault) return f.platformDefault[p];
    return f.default;
  }
  function fieldValue(f) {
    const v = state.form.values[state.form.wf + ":" + f.key];
    return v === undefined ? fieldDefault(f) : v;
  }
  function setFieldValue(f, v) {
    state.form.values[state.form.wf + ":" + f.key] = v;
  }
  function fieldVisible(f) {
    const p = curPlatform().id;
    if (f.platforms && !f.platforms.includes(p)) return false;
    if (f.engines && !f.engines.includes(state.form.engine)) return false;
    if (state.form.mode === "test" && !f.engines) return false;
    if (f.showIf) {
      for (const [k, want] of Object.entries(f.showIf)) {
        const other = curWf().fields.find((x) => x.key === k);
        if (!other || !fieldVisible(other)) return false;
        const have = fieldValue(other);
        const wants = Array.isArray(want) ? want : [want];
        if (!wants.some((w) => String(w) === String(have))) return false;
      }
    }
    return true;
  }

  function defaultOutdir() {
    const wf = curWf(), p = curPlatform();
    return "results/" + wf.id + "_" + p.id + (state.form.mode === "test" ? "_test" : "");
  }

  function renderChoices() {
    const wf = curWf();
    if (!wf.platforms.some((p) => p.id === state.form.platform)) state.form.platform = wf.platforms[0].id;
    if (!wf.engines.includes(state.form.engine)) state.form.engine = wf.engines[0];
    if (!state.form.outdirTouched) state.form.outdir = defaultOutdir();

    const wfBox = $("#wf-choices");
    setKids(wfBox, ...WORKFLOWS.map((w) =>
      h("button", { class: "choice" + (w.id === wf.id ? " selected" : ""), type: "button",
        onclick: () => { state.form.wf = w.id; renderForm(); } },
        h("div", { class: "t" }, w.title), h("div", { class: "s" }, w.subtitle),
        h("div", { class: "q" }, w.question))));

    const p = curPlatform();
    setKids($("#platform-choices"), ...wf.platforms.map((pl) =>
      h("button", { class: "choice compact" + (pl.id === p.id ? " selected" : ""), type: "button",
        onclick: () => { state.form.platform = pl.id; renderForm(); } },
        h("div", { class: "t" }, pl.label), h("div", { class: "s" }, pl.desc))));

    const modes = [
      ["test", "Built-in test data", "A tiny bundled dataset. Use this first to check that everything is installed. Takes minutes."],
      ["own", "My own data", "Analyse your samples. You will point HOMES at a samplesheet or FASTQ files."],
    ];
    setKids($("#mode-choices"), ...modes.map(([id, t, s]) =>
      h("button", { class: "choice compact" + (state.form.mode === id ? " selected" : ""), type: "button",
        onclick: () => { state.form.mode = id; renderForm(); } },
        h("div", { class: "t" }, t), h("div", { class: "s" }, s))));
    setKids($("#mode-note"), 
      state.form.mode === "test" && wf.testNote ? h("div", { class: "note info small" }, wf.testNote) : "");

    const tools = state.status && state.status.tools;
    setKids($("#engine-choices"), ...wf.engines.map((id) => {
      const e = ENGINES[id];
      let tag = null;
      if (tools && e.tool && tools[e.tool]) {
        const t = tools[e.tool];
        tag = t.found ? (t.running === false ? "⚠ installed but not running" : "✓ found on this computer") : "✗ not found on this computer";
      }
      return h("button", { class: "choice compact" + (id === state.form.engine ? " selected" : ""), type: "button",
        onclick: () => { state.form.engine = id; renderForm(); } },
        h("div", { class: "t" }, e.label), h("div", { class: "s" }, e.desc), tag ? h("div", { class: "tag" }, tag) : null);
    }));
  }

  function renderField(f) {
    const id = "f-" + f.key;
    const val = fieldValue(f);
    const onChange = (v) => { setFieldValue(f, v); renderForm({ keepFields: false, focus: id }); };
    let control;
    if (f.type === "bool") {
      const cb = h("input", { type: "checkbox", id, checked: val === true || val === "true",
        onchange: (e) => onChange(e.target.checked) });
      return h("div", { class: "field", dataset: { key: f.key } },
        h("label", { class: "toggle" }, cb, h("span", { class: "track" }), h("b", {}, f.label)),
        f.help ? h("div", { class: "help" }, f.help) : null);
    }
    if (f.type === "select") {
      control = h("select", { id, onchange: (e) => onChange(e.target.value) },
        ...f.options.map(([v, l]) => h("option", { value: v, selected: String(v) === String(val ?? "") }, l)));
    } else {
      const listId = f.suggest ? id + "-list" : null;
      const input = h("input", {
        type: f.type === "number" ? "number" : "text", id, value: val ?? "", step: "any",
        list: listId, placeholder: f.type === "path" ? "path/to/…" : (f.default != null ? String(f.default) : ""),
        oninput: (e) => { setFieldValue(f, e.target.value); updateCommand(); },
        onchange: (e) => onChange(e.target.value),
      });
      const parts = [input];
      if (f.type === "path") {
        parts.push(h("button", { class: "btn small server-only", type: "button",
          onclick: () => openBrowser({ mode: f.pick || "any", start: input.value }).then((p) => { if (p != null) onChange(p); }) }, "Browse…"));
        if (f.samplesheet) {
          parts.push(h("button", { class: "btn small", type: "button", title: "Open the samplesheet builder",
            onclick: () => {
              state.sheet.layout = curPlatform().samplesheet;
              state.sheet.target = f.key;
              save();
              show("sheet");
            } }, "Create…"));
        }
      }
      control = h("div", { class: "input-group" }, ...parts);
      if (f.suggest) {
        control.append(h("datalist", { id: listId }, ...f.suggest.map(([v, l]) => h("option", { value: v }, l))));
      }
    }
    return h("div", { class: "field", dataset: { key: f.key } },
      h("label", { class: "lbl", for: id }, f.label, f.required ? h("span", { class: "req" }, "*") : null),
      control,
      f.help ? h("div", { class: "help" }, f.help) : null,
      f.suggest ? h("div", { class: "help" }, "Common: ",
        ...f.suggest.map(([v, l], i) => [i ? " · " : "", h("button", { class: "linkbtn small", type: "button",
          onclick: () => onChange(v) }, l)])) : null);
  }

  function renderFields() {
    const wf = curWf();
    const visible = wf.fields.filter(fieldVisible);
    const basic = visible.filter((f) => !f.advanced);
    const adv = visible.filter((f) => f.advanced);
    setKids($("#fields-basic"), ...basic.map(renderField));
    setKids($("#fields-adv"), ...adv.map(renderField));
    $("#adv-wrap").classList.toggle("hidden", adv.length === 0);
    const hasOptions = visible.length > 0;
    $("#step-options").classList.toggle("hidden", !hasOptions);
    $("#step-out-num").textContent = hasOptions ? "6" : "5";
    $("#step-run-num").textContent = hasOptions ? "7" : "6";
    if (!basic.length && hasOptions) {
      setKids($("#fields-basic"), h("p", { class: "muted small" }, "Nothing required here – see advanced options if needed."));
    }
  }

  function renderForm(opts) {
    renderChoices();
    renderFields();
    $("#outdir").value = state.form.outdir;
    $("#run-label").value = state.form.label;
    $("#resume").checked = !!state.form.resume;
    $("#extra-args").value = state.form.extra;
    applyServerMode();
    updateCommand();
    save();
    if (opts && opts.focus) {
      const el = document.getElementById(opts.focus);
      if (el && el.type !== "checkbox" && el.tagName !== "SELECT") el.focus();
    }
  }

  function splitArgs(s) {
    const out = [];
    const re = /"([^"]*)"|'([^']*)'|(\S+)/g;
    let m;
    while ((m = re.exec(s))) out.push(m[1] ?? m[2] ?? m[3]);
    return out;
  }

  function buildArgv() {
    const wf = curWf(), p = curPlatform(), f = state.form;
    const profiles = [];
    if (f.mode === "test") profiles.push(p.test.profile);
    profiles.push(f.engine);
    const argv = ["nextflow", "run", "workflows/" + wf.id, "-profile", profiles.join(","), "--platform", p.id];
    const emitted = new Set(["platform"]);
    if (f.mode === "test") {
      for (const [k, v] of Object.entries(p.test.params || {})) { argv.push("--" + k, String(v)); emitted.add(k); }
    }
    for (const fld of wf.fields) {
      if (!fieldVisible(fld) || emitted.has(fld.key)) continue;
      const v = fieldValue(fld);
      if (v === undefined || v === null || v === "") continue;
      const def = fieldDefault(fld);
      if (!fld.emit && def !== undefined && String(v) === String(def)) continue;
      argv.push("--" + fld.key, String(v));
    }
    argv.push("--outdir", f.outdir || defaultOutdir());
    if (f.resume) argv.push("-resume");
    if (f.extra.trim()) argv.push(...splitArgs(f.extra));
    return argv;
  }

  function shellQuote(a) {
    return /^[A-Za-z0-9_\-.,/:=@+%]+$/.test(a) ? a : "'" + a.replace(/'/g, "'\\''") + "'";
  }
  function formatCommand(argv) {
    let out = argv.slice(0, 3).map(shellQuote).join(" ");
    for (let i = 3; i < argv.length; i++) {
      const a = argv[i];
      if (a.startsWith("-")) {
        out += " \\\n  " + shellQuote(a);
        if (i + 1 < argv.length && !argv[i + 1].startsWith("-")) out += " " + shellQuote(argv[++i]);
      } else {
        out += " " + shellQuote(a);
      }
    }
    return out;
  }

  function validate() {
    const errors = [], warnings = [];
    const wf = curWf(), f = state.form;
    $$(".field.invalid").forEach((el) => el.classList.remove("invalid"));
    if (f.mode === "own") {
      for (const fld of wf.fields) {
        if (!fieldVisible(fld)) continue;
        const v = fieldValue(fld);
        let bad = false;
        if (fld.required && (v === undefined || v === null || String(v).trim() === "")) {
          errors.push(`“${fld.label}” is required.`);
          bad = true;
        } else if (fld.type === "number" && v !== "" && v != null && isNaN(Number(v))) {
          errors.push(`“${fld.label}” must be a number.`);
          bad = true;
        }
        if (bad) {
          const el = $(`.field[data-key="${fld.key}"]`);
          if (el) el.classList.add("invalid");
        }
      }
      if (wf.id === "HOMES_metagenomics" && fieldValue(wf.fields.find((x) => x.key === "download_databases")) === true
          && fieldValue(wf.fields.find((x) => x.key === "skip_taxonomy")) !== true) {
        warnings.push("The first run downloads the selected Kraken2 database (several GB). Later runs reuse it.");
      }
    }
    if (!(f.outdir || "").trim()) errors.push("Choose a results folder.");
    const tools = state.status && state.status.tools;
    if (tools) {
      if (!tools.nextflow.found) errors.push("Nextflow is not installed or not on PATH – see the Setup tab.");
      const eng = ENGINES[f.engine];
      if (eng.tool && tools[eng.tool]) {
        if (!tools[eng.tool].found) warnings.push(`${eng.label} was not found on this computer.`);
        else if (tools[eng.tool].running === false) warnings.push("Docker is installed but not running. Open Docker Desktop first.");
      }
    }
    return { errors, warnings };
  }

  function updateCommand() {
    const argv = buildArgv();
    $("#cmd-preview").textContent = formatCommand(argv);
    const { errors, warnings } = validate();
    const box = $("#validation");
    setKids(box);
    if (errors.length) box.append(h("div", { class: "note bad" }, h("b", {}, "Before you can start:"), h("ul", {}, ...errors.map((e) => h("li", {}, e)))));
    if (warnings.length) box.append(h("div", { class: "note warn" }, h("ul", {}, ...warnings.map((e) => h("li", {}, e)))));
    if (!errors.length && !warnings.length) box.append(h("div", { class: "note good" }, "Everything looks ready."));
    $("#btn-launch").disabled = errors.length > 0;
    return argv;
  }

  $("#outdir").addEventListener("input", (e) => { state.form.outdir = e.target.value; state.form.outdirTouched = true; updateCommand(); save(); });
  $("#run-label").addEventListener("input", (e) => { state.form.label = e.target.value; save(); });
  $("#resume").addEventListener("change", (e) => { state.form.resume = e.target.checked; updateCommand(); save(); });
  $("#extra-args").addEventListener("input", (e) => { state.form.extra = e.target.value; updateCommand(); save(); });

  $("#btn-copy").addEventListener("click", async () => {
    const text = formatCommand(buildArgv());
    try { await navigator.clipboard.writeText(text); toast("Command copied"); }
    catch (e) { toast("Copy failed – select the text and copy it manually"); }
  });
  $("#btn-script").addEventListener("click", () => {
    const wf = curWf(), p = curPlatform();
    const text = "#!/usr/bin/env bash\n# HOMES " + wf.id + " (" + p.label + ") – generated by the HOMES dashboard\n" +
      "# Run from the HOMES repository folder:  bash " + "run_" + wf.id + "_" + p.id + ".sh\nset -euo pipefail\n\n" +
      formatCommand(buildArgv()) + "\n";
    download("run_" + wf.id + "_" + p.id + ".sh", text, "text/x-shellscript");
  });
  $("#btn-reset").addEventListener("click", () => {
    state.form.values = {};
    state.form.outdirTouched = false;
    state.form.extra = "";
    state.form.label = "";
    renderForm();
    toast("Form reset to defaults");
  });
  $("#btn-launch").addEventListener("click", async () => {
    const argv = updateCommand();
    const btn = $("#btn-launch");
    btn.disabled = true;
    try {
      const run = await api("/api/run", { argv, label: state.form.label || (curWf().title + " – " + curPlatform().label) });
      toast("Analysis started");
      state.selectedRun = run.id;
      show("runs");
    } catch (e) {
      toast("Could not start: " + e.message, 6000);
    } finally {
      btn.disabled = false;
    }
  });

  function download(name, text, type) {
    const a = h("a", { href: URL.createObjectURL(new Blob([text], { type: type || "text/plain" })), download: name });
    document.body.append(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }

  // ------------------------------------------------------ home overview --
  function renderHome() {
    setKids($("#home-workflows"), ...WORKFLOWS.map((w) =>
      h("button", { class: "choice", type: "button", onclick: () => { state.form.wf = w.id; renderForm(); show("new"); } },
        h("div", { class: "t" }, w.title), h("div", { class: "s" }, w.subtitle),
        h("div", { class: "q" }, w.question),
        h("p", { class: "muted small", style: "margin:8px 0 0" }, w.description),
        h("div", { class: "tag" }, w.platforms.map((p) => p.label).join(" · ")))));
    const box = $("#home-setup");
    setKids(box);
    if (!state.server) {
      box.append(h("div", { class: "note info" },
        h("b", {}, "Command-builder mode. "),
        "This page can build commands and samplesheets. To start runs, follow progress and open reports from here, run ",
        h("code", {}, "python3 dashboard/homes_dashboard.py"), " in the HOMES folder."));
    } else if (state.status) {
      const missing = (state.status.checks || []).filter((c) => c.status === "missing");
      if (missing.length) {
        box.append(h("div", { class: "note warn" }, "Before your first analysis, fix: " + missing.map((c) => c.title).join(", ") + ". ",
          h("a", { href: "#", "data-goto": "setup" }, "Open setup steps →")));
      }
    }
  }

  function renderHomeRuns() {
    const box = $("#home-runs");
    if (!state.runs.length) { box.textContent = state.server ? "No runs yet." : "Start the local server to track runs."; return; }
    setKids(box, ...state.runs.slice(0, 5).map((r) =>
      h("div", { class: "row", style: "padding:4px 0" },
        h("span", { class: "pill " + r.status }, r.status),
        h("a", { href: "#", onclick: (e) => { e.preventDefault(); state.selectedRun = r.id; show("runs"); } }, r.label),
        h("span", { class: "muted small" }, fmtTime(r.started)))));
  }

  // ------------------------------------------------------- samplesheets --
  function sheetDef() { return SHEETS[state.sheet.layout] || SHEETS.metagenomics; }

  function renderSheet() {
    const def = sheetDef();
    const sel = $("#sheet-layout");
    if (!sel.options.length) {
      for (const [k, d] of Object.entries(SHEETS)) sel.append(h("option", { value: k }, d.title));
      sel.addEventListener("change", () => { state.sheet.layout = sel.value; save(); renderSheet(); });
    }
    sel.value = state.sheet.layout;
    $("#sheet-hint").textContent = "Columns: " + def.columns.map((c) => c.key + (c.required ? "*" : "")).join(", ") +
      ". " + def.columns.map((c) => c.key + " = " + c.help).join("; ") + ".";
    if (!state.sheet.path) state.sheet.path = "samplesheets/my_samples." + def.ext;
    $("#sheet-path").value = state.sheet.path;

    const issues = validateSheet();
    const table = $("#sheet-table");
    const head = h("tr", {}, h("th", {}, "#"), ...def.columns.map((c) => h("th", { title: c.help }, c.key + (c.required ? " *" : ""))), h("th", {}, ""));
    const rows = state.sheet.rows.map((row, i) => h("tr", {},
      h("td", { class: "idx" }, String(i + 1)),
      ...def.columns.map((c) => {
        const bad = issues.cells.has(i + ":" + c.key);
        let ctl;
        if (c.options) {
          ctl = h("select", { onchange: (e) => { row[c.key] = e.target.value; save(); renderSheet(); } },
            h("option", { value: "" }, ""), ...c.options.map((o) => h("option", { value: o, selected: row[c.key] === o }, o)));
        } else {
          ctl = h("input", { type: "text", value: row[c.key] || "", placeholder: c.path ? "/path/to/file" : "",
            style: c.path ? "min-width:280px" : "",
            onchange: (e) => { row[c.key] = e.target.value.trim(); save(); renderSheet(); } });
        }
        return h("td", { class: bad ? "bad" : "" }, ctl);
      }),
      h("td", {}, h("button", { class: "btn small danger", title: "Remove row", onclick: () => { state.sheet.rows.splice(i, 1); save(); renderSheet(); } }, "✕"))));
    setKids(table, h("thead", {}, head), h("tbody", {}, ...rows));
    if (!rows.length) {
      table.append(h("tbody", {}, h("tr", {}, h("td", { colspan: def.columns.length + 2, class: "muted", style: "padding:18px;text-align:center" },
        state.server ? "No samples yet – add files from a folder, paste a table, or add rows by hand." : "No samples yet – paste a table or add rows by hand."))));
    }
    const vbox = $("#sheet-validation");
    setKids(vbox, );
    if (state.sheet.rows.length) {
      vbox.append(issues.messages.length
        ? h("div", { class: "note warn" }, h("ul", {}, ...issues.messages.map((m) => h("li", {}, m))))
        : h("div", { class: "note good" }, `${state.sheet.rows.length} sample(s), no problems found.`));
    }
    applyServerMode();
  }

  function validateSheet() {
    const def = sheetDef();
    const messages = [], cells = new Set();
    const seen = new Map();
    state.sheet.rows.forEach((row, i) => {
      const n = i + 1;
      for (const c of def.columns) {
        if (c.required && !(row[c.key] || "").trim()) { messages.push(`Row ${n}: ${c.key} is empty.`); cells.add(i + ":" + c.key); }
      }
      const s = (row.sample || "").trim();
      if (s) {
        if (seen.has(s)) { messages.push(`Row ${n}: sample “${s}” is also used in row ${seen.get(s)}.`); cells.add(i + ":sample"); }
        else seen.set(s, n);
        if (def.strictIds && !/^[A-Za-z][A-Za-z0-9_]*$/.test(s)) {
          messages.push(`Row ${n}: sample IDs must start with a letter and contain only letters, numbers and _.`);
          cells.add(i + ":sample");
        }
      }
      if (row.read_layout === "paired" && !(row.fastq_2 || "").trim()) {
        messages.push(`Row ${n}: paired layout needs fastq_2.`); cells.add(i + ":fastq_2");
      }
      if (row.read_layout === "single" && (row.fastq_2 || "").trim()) {
        messages.push(`Row ${n}: single layout should leave fastq_2 empty.`); cells.add(i + ":fastq_2");
      }
      if (def.gzOnly) {
        for (const k of ["fastq_1", "fastq_2"]) {
          if (row[k] && !/\.(fastq|fq)\.gz$/i.test(row[k])) { messages.push(`Row ${n}: ${k} must be a gzipped FASTQ (.fastq.gz).`); cells.add(i + ":" + k); }
        }
      }
    });
    return { messages, cells };
  }

  function sheetText() {
    const def = sheetDef();
    const sep = def.ext === "tsv" ? "\t" : ",";
    const esc = (v) => {
      v = v == null ? "" : String(v);
      return sep === "," && /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
    };
    const lines = [def.columns.map((c) => c.key).join(sep)];
    for (const r of state.sheet.rows) lines.push(def.columns.map((c) => esc(r[c.key])).join(sep));
    return lines.join("\n") + "\n";
  }

  function parseTable(text) {
    const lines = text.replace(/\r/g, "").split("\n").filter((l) => l.trim());
    if (!lines.length) return [];
    const sep = lines[0].includes("\t") ? "\t" : ",";
    const split = (line) => {
      if (sep === "\t") return line.split("\t");
      const out = []; let cur = "", q = false;
      for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (q) { if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') q = false; else cur += ch; }
        else if (ch === '"') q = true; else if (ch === ",") { out.push(cur); cur = ""; } else cur += ch;
      }
      out.push(cur);
      return out;
    };
    const def = sheetDef();
    const aliases = { sampleid: "sample", forwardreads: "fastq_1", reversereads: "fastq_2", r1: "fastq_1", r2: "fastq_2" };
    let header = split(lines[0]).map((x) => x.trim());
    const norm = header.map((x) => aliases[x.toLowerCase()] || x);
    const known = def.columns.map((c) => c.key);
    let body = lines.slice(1);
    let cols = norm;
    if (!norm.some((x) => known.includes(x))) { cols = known; body = lines; } // no header row: use column order
    return body.map((l) => {
      const vals = split(l);
      const row = {};
      cols.forEach((c, i) => { if (known.includes(c)) row[c] = (vals[i] || "").trim(); });
      return row;
    });
  }

  $("#sheet-add").addEventListener("click", () => {
    const def = sheetDef();
    const row = {};
    def.columns.forEach((c) => { if (c.default) row[c.key] = c.default; });
    state.sheet.rows.push(row); save(); renderSheet();
  });
  $("#sheet-clear").addEventListener("click", () => {
    if (state.sheet.rows.length && !confirm("Remove all rows?")) return;
    state.sheet.rows = []; save(); renderSheet();
  });
  $("#sheet-path").addEventListener("input", (e) => { state.sheet.path = e.target.value; save(); });
  $("#sheet-download").addEventListener("click", () => {
    const name = (state.sheet.path || "samplesheet." + sheetDef().ext).split(/[\\/]/).pop();
    download(name, sheetText(), "text/csv");
  });
  $("#sheet-save").addEventListener("click", async () => {
    const path = state.sheet.path.trim();
    if (!path) return toast("Enter a file name first");
    const issues = validateSheet();
    if (issues.messages.length && !confirm("The samplesheet has problems:\n\n" + issues.messages.slice(0, 8).join("\n") + "\n\nSave anyway?")) return;
    try {
      let res;
      try { res = await api("/api/save-samplesheet", { path, content: sheetText() }); }
      catch (e) {
        if (!/already exists/.test(e.message) || !confirm(e.message + ".\nOverwrite it?")) throw e;
        res = await api("/api/save-samplesheet", { path, content: sheetText(), overwrite: true });
      }
      state.sheet.savedPath = res.path; save();
      toast("Saved " + res.path);
    } catch (e) { toast("Save failed: " + e.message, 5000); }
  });
  $("#sheet-use").addEventListener("click", () => {
    const path = state.sheet.savedPath || state.sheet.path;
    if (state.server && !state.sheet.savedPath) {
      toast("Save the file first so the workflow can read it");
      return;
    }
    const layout = state.sheet.layout;
    const wfId = layout.startsWith("amplicon") ? "HOMES_amplicon" : layout === "assembly" ? "HOMES_assembly" : "HOMES_metagenomics";
    state.form.wf = wfId;
    state.form.mode = "own";
    if (layout === "amplicon_short") state.form.platform = "short";
    if (layout === "amplicon_nanopore") state.form.platform = "nanopore";
    const key = layout === "amplicon_nanopore" ? "sample_sheet" : "input";
    state.form.values[wfId + ":" + key] = path;
    renderForm();
    show("new");
    toast("Samplesheet filled in");
  });
  $("#sheet-paste").addEventListener("click", () => {
    const ta = h("textarea", { rows: 12, placeholder: "Paste rows copied from Excel / Google Sheets, or a CSV/TSV file's contents.\nA header row with the column names is recommended." });
    const file = h("input", { type: "file", accept: ".csv,.tsv,.txt",
      onchange: async (e) => { const f = e.target.files[0]; if (f) ta.value = await f.text(); } });
    const replace = h("input", { type: "checkbox" });
    modal("Paste or import a table", [
      h("p", { class: "muted small" }, "Expected columns: " + sheetDef().columns.map((c) => c.key).join(", ") + ". Legacy names sampleID / forwardReads / reverseReads are understood."),
      h("p", {}, "Or load a file: ", file), ta,
      h("label", { class: "row small", style: "margin-top:8px" }, replace, "Replace existing rows"),
    ], [["Import", "primary", () => {
      const rows = parseTable(ta.value);
      if (!rows.length) { toast("Nothing to import"); return false; }
      state.sheet.rows = replace.checked ? rows : state.sheet.rows.concat(rows);
      save(); renderSheet(); toast(rows.length + " row(s) imported");
    }]]);
  });
  $("#sheet-scan").addEventListener("click", async () => {
    const folder = await openBrowser({ mode: "folder", title: "Choose the folder that contains your FASTQ files" });
    if (folder == null) return;
    try {
      const res = await api("/api/scan-fastq", { folder, recursive: true });
      if (!res.rows.length) return toast("No FASTQ files found in " + res.folder, 5000);
      const def = sheetDef();
      const rows = res.rows.map((r) => {
        const row = {};
        def.columns.forEach((c) => { row[c.key] = r[c.key] != null ? r[c.key] : (c.default || ""); });
        return row;
      });
      state.sheet.rows = state.sheet.rows.concat(rows);
      save(); renderSheet();
      toast(`Found ${res.files} FASTQ file(s) → ${rows.length} sample(s). Check the names and layout.`, 5000);
    } catch (e) { toast("Scan failed: " + e.message, 5000); }
  });

  // --------------------------------------------------------------- runs --
  let runsTimer = null, logTimer = null;

  function fmtTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleString();
  }
  function duration(a, b) {
    if (!a) return "";
    const s = Math.max(0, Math.round(((b ? new Date(b) : new Date()) - new Date(a)) / 1000));
    if (s < 60) return s + " s";
    if (s < 3600) return Math.floor(s / 60) + " min " + (s % 60) + " s";
    return Math.floor(s / 3600) + " h " + Math.floor((s % 3600) / 60) + " min";
  }

  async function refreshRuns() {
    if (!state.server) return;
    try {
      state.runs = (await api("/api/runs")).runs;
    } catch (e) { return; }
    const running = state.runs.filter((r) => r.status === "running").length;
    const badge = $("#running-count");
    badge.textContent = running;
    badge.classList.toggle("hidden", !running);
    renderHomeRuns();
    if (state.view === "runs") renderRuns();
    clearTimeout(runsTimer);
    if (running || state.view === "runs") runsTimer = setTimeout(refreshRuns, running ? 3000 : 10000);
  }

  function renderRuns() {
    const list = $("#runs-list");
    if (!state.runs.length) {
      setKids(list, h("div", { class: "card muted" }, "No runs yet. ", h("a", { href: "#", "data-goto": "new" }, "Start a new analysis →")));
      setKids($("#run-detail"), );
      return;
    }
    if (!state.selectedRun || !state.runs.some((r) => r.id === state.selectedRun)) state.selectedRun = state.runs[0].id;
    setKids(list, ...state.runs.map((r) =>
      h("div", { class: "list-item clickable" + (r.id === state.selectedRun ? " selected" : ""),
        onclick: () => { state.selectedRun = r.id; renderRuns(); } },
        h("div", { class: "main" },
          h("div", { class: "title" }, r.label),
          h("div", { class: "muted small" }, [r.workflow, r.platform, fmtTime(r.started)].filter(Boolean).join(" · "))),
        h("span", { class: "pill " + r.status }, r.status))));
    const run = state.runs.find((r) => r.id === state.selectedRun);
    // Only rebuild the detail panel when something changed, so scrolling and open sections survive polling.
    const sig = JSON.stringify(run);
    if (sig !== state.detailSig || !$("#run-log")) { state.detailSig = sig; renderRunDetail(run); }
  }

  const HINTS = [
    [/Cannot connect to the Docker daemon|docker: command not found|Is the docker daemon running/i, "Docker is not running. Open Docker Desktop and wait until it is ready."],
    [/No such file|does not exist|not found:|Cannot find|Missing required/i, "A file or folder could not be found. Check the paths in your samplesheet and options – relative paths are read from the HOMES folder."],
    [/exit status 137|OutOfMemory|Killed|out of memory/i, "A step ran out of memory. Close other programs, give Docker more memory (Docker Desktop → Settings → Resources), or run on a server."],
    [/Java version|requires Java|UnsupportedClassVersion/i, "Nextflow needs Java 17 or newer – see the Setup tab."],
    [/samplesheet|Samplesheet/, "There may be a problem with the samplesheet. Open it in the Samplesheet tab to check sample names and columns."],
    [/Plugin with id .* not found|registry\.nextflow\.io|Failed to prefetch plugin/i, "Nextflow could not download its plugins (e.g. nf-schema). Check the internet connection; on a work network, ask IT to allow registry.nextflow.io, github.com and Docker Hub."],
    [/toomanyrequests|429 Too Many Requests|pull rate limit/i, "Docker Hub is limiting downloads. Wait a few minutes and start again with Resume on, or sign in with `docker login`."],
    [/No space left on device/i, "The disk is full. Free some space (e.g. delete the work/ folder of old runs) and resume."],
  ];

  function renderRunDetail(run) {
    const box = $("#run-detail");
    if (!run) { setKids(box); return; }
    const prog = run.progress || { steps: [] };
    const hint = prog.error ? (HINTS.find(([re]) => re.test(prog.error)) || [null, null])[1] : null;
    const logPre = h("pre", { class: "log", id: "run-log" });
    const children = [
      h("div", { class: "row" },
        h("h3", { style: "margin:0;flex:1" }, run.label),
        h("span", { class: "pill " + run.status }, run.status)),
      h("p", { class: "muted small" }, `Started ${fmtTime(run.started)} · ${duration(run.started, run.finished)}` +
        (run.exit_code != null ? ` · exit code ${run.exit_code}` : "")),
      run.status === "succeeded" ? h("div", { class: "note good" }, "Finished successfully. ",
        h("a", { href: "#", "data-goto": "results" }, "Open the results →")) : null,
      run.status === "failed" ? h("div", { class: "note bad" }, h("b", {}, "The run stopped with an error. "),
        hint || "Check the log below; the first lines starting with ERROR usually explain the problem.",
        " After fixing it, start the same analysis again with Resume on – finished steps are reused.") : null,
      run.status === "unknown" ? h("div", { class: "note warn" }, "The dashboard was restarted while this run was going, so its status is unknown. Check the log or the results folder.") : null,
      h("div", { class: "row" },
        run.status === "running" ? h("button", { class: "btn danger", onclick: async () => {
          if (!confirm("Stop this analysis? You can resume it later.")) return;
          try { await api(`/api/runs/${run.id}/stop`, {}); toast("Stopping…"); refreshRuns(); } catch (e) { toast(e.message); }
        } }, "■ Stop") : null,
        run.outdir ? h("button", { class: "btn", onclick: () => show("results") }, "Results folder") : null,
        h("button", { class: "btn", onclick: async () => {
          try { await navigator.clipboard.writeText(formatCommand(run.argv)); toast("Command copied"); } catch (e) { toast("Copy failed"); }
        } }, "Copy command")),
      h("h4", { style: "margin-top:16px" }, `Steps started (${prog.steps.length})`),
      prog.steps.length
        ? h("div", { class: "steps-list" }, ...prog.steps.map((s) =>
            h("span", { class: s.cached === s.tasks ? "cached" : "", title: s.cached ? `${s.cached} reused from a previous run` : "" },
              s.name + (s.tasks > 1 ? ` ×${s.tasks}` : "") + (s.cached === s.tasks ? " (reused)" : ""))))
        : h("p", { class: "muted small" }, run.status === "running" ? "Preparing – the first run downloads containers, which can take a while…" : "No steps recorded."),
      h("details", { class: "advanced" },
        h("summary", {}, "Command"), h("pre", { class: "cmd" }, formatCommand(run.argv))),
      h("h4", { style: "margin-top:16px" }, "Live log"),
      logPre,
    ];
    setKids(box, h("div", { class: "card" }, ...children));
    if (state.logRun !== run.id) { state.logRun = run.id; state.logOffset = 0; state.logText = ""; }
    logPre.textContent = state.logText || "";
    logPre.scrollTop = logPre.scrollHeight;
    pollLog(run);
  }

  async function pollLog(run) {
    clearTimeout(logTimer);
    if (state.view !== "runs" || state.logRun !== run.id) return;
    try {
      const res = await api(`/api/runs/${run.id}/log?offset=${state.logOffset}`);
      if (state.logRun !== run.id) return;
      if (res.text) {
        state.logText = ((state.logText || "") + res.text).slice(-400000);
        const pre = $("#run-log");
        if (pre) {
          const atBottom = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 30;
          pre.textContent = state.logText;
          if (atBottom) pre.scrollTop = pre.scrollHeight;
        }
      }
      state.logOffset = res.offset;
    } catch (e) { /* server gone */ }
    if (run.status === "running") logTimer = setTimeout(() => pollLog(run), 2000);
  }

  $("#runs-refresh").addEventListener("click", refreshRuns);

  // ------------------------------------------------------------ results --
  async function refreshResults() {
    if (!state.server) return;
    const list = $("#results-list");
    setKids(list, h("p", { class: "muted" }, "Looking for results…"));
    let results;
    try { results = (await api("/api/results")).results; }
    catch (e) { setKids(list, h("div", { class: "note bad" }, e.message)); return; }
    if (!results.length) {
      setKids(list, h("div", { class: "card muted" }, "No results yet. They appear here once an analysis has written to its results folder."));
      return;
    }
    setKids(list, ...results.map(renderResult));
  }

  const fileUrl = (p) => "/files" + p.split("/").map(encodeURIComponent).join("/");

  function renderResult(r) {
    const mainReports = r.reports.filter((x) => x.kind === "report");
    const otherReports = r.reports.filter((x) => x.kind !== "report");
    return h("div", { class: "card" },
      h("div", { class: "row" },
        h("div", { style: "flex:1;min-width:220px" },
          h("h3", { style: "margin:0" }, r.name),
          h("div", { class: "muted small mono" }, r.path),
          h("div", { class: "muted small" }, (r.workflow || "HOMES") + (r.modified ? " · updated " + fmtTime(r.modified) : ""))),
        h("button", { class: "btn small", title: "Remove from this list (files are not deleted)", onclick: async () => {
          await api("/api/results/forget", { path: r.path }); refreshResults();
        } }, "Hide")),
      !r.exists ? h("div", { class: "note warn" }, "This folder does not exist yet.") : null,
      r.exists && !r.reports.length && !r.tables.length ? h("p", { class: "muted small" }, "No reports or tables yet.") : null,
      mainReports.length ? h("div", { class: "row", style: "margin-top:12px" },
        ...mainReports.map((x) => h("a", { class: "btn primary", href: fileUrl(x.path), target: "_blank", rel: "noopener" }, "📊 " + x.rel.split("/").pop()))) : null,
      otherReports.length ? h("div", { class: "row", style: "margin-top:8px" },
        ...otherReports.map((x) => h("a", { class: "btn small", href: fileUrl(x.path), target: "_blank", rel: "noopener" },
          (x.kind === "qc" ? "QC: " : "Run info: ") + x.rel.split("/").pop()))) : null,
      r.tables.length ? h("details", { class: "advanced" },
        h("summary", {}, `Tables (${r.tables.length})`),
        h("div", { class: "list" }, ...r.tables.map((t) =>
          h("div", { class: "row small" },
            h("span", { class: "mono", style: "flex:1;min-width:200px" }, t.rel),
            h("button", { class: "btn small", onclick: () => previewTable(t.path) }, "Preview"),
            h("a", { class: "btn small", href: fileUrl(t.path), download: t.rel.split("/").pop() }, "Download"))))) : null);
  }

  async function previewTable(path) {
    try {
      const t = await api("/api/table?path=" + encodeURIComponent(path));
      const isNum = (v) => v !== "" && !isNaN(Number(v));
      const tbl = h("table", {},
        h("thead", {}, h("tr", {}, ...t.header.map((c) => h("th", {}, c)))),
        h("tbody", {}, ...t.rows.map((r) => h("tr", {}, ...r.map((c) => h("td", { class: isNum(c) ? "num" : "" }, c))))));
      modal(path.split("/").pop(), [
        h("p", { class: "muted small" }, t.total_rows > t.rows.length ? `Showing first ${t.rows.length} of ${t.total_rows} rows.` : `${t.total_rows} rows.`),
        h("div", { class: "table-wrap" }, tbl),
      ], [], true);
    } catch (e) { toast(e.message, 5000); }
  }

  $("#results-refresh").addEventListener("click", refreshResults);
  $("#btn-quit").addEventListener("click", async () => {
    const running = state.runs.filter((r) => r.status === "running").length;
    if (!confirm("Quit the HOMES dashboard?" + (running ? `\n\n${running} analysis(es) will keep running; reopen the dashboard to see them.` : ""))) return;
    try { await api("/api/shutdown", {}); } catch (e) { /* server already gone */ }
    setKids(document.body, h("main", {}, h("div", { class: "card" },
      h("h2", {}, "The HOMES dashboard has stopped."),
      h("p", { class: "muted" }, "You can close this window. Open the HOMES Dashboard app again whenever you need it."))));
    setTimeout(() => window.close(), 400);
  });
  $("#results-add").addEventListener("click", async () => {
    const p = $("#results-add-path").value.trim();
    if (!p) return;
    try { await api("/api/results/add", { path: p }); $("#results-add-path").value = ""; refreshResults(); }
    catch (e) { toast(e.message, 5000); }
  });

  // -------------------------------------------------------------- setup --
  function renderSetup() {
    const box = $("#setup-checks");
    if (!state.server) {
      setKids(box, h("div", { class: "note info" },
        "Automatic checks need the local server. In a terminal, inside the HOMES folder, run ",
        h("code", {}, "python3 dashboard/homes_dashboard.py"), ". Until then, check manually with ",
        h("code", {}, "java -version"), ", ", h("code", {}, "nextflow info"), " and ", h("code", {}, "docker run hello-world"), "."));
      return;
    }
    const checks = state.status.checks || [];
    const icons = { ok: ["ok", "✓"], warn: ["warn", "!"], missing: ["no", "✗"], optional: ["opt", "–"] };
    const missing = checks.filter((c) => c.status === "missing");
    setKids(box,
      h("div", { class: "row" }, h("h3", { style: "margin:0;flex:1" }, "This computer"),
        h("button", { class: "btn small", onclick: async () => { state.status = await api("/api/status"); renderSetup(); renderForm(); renderHome(); toast("Checked again"); } }, "Check again")),
      ...checks.map((c) => h("div", { class: "check" },
        h("div", { class: "icon " + icons[c.status][0] }, icons[c.status][1]),
        h("div", {},
          h("b", {}, c.title), " ", h("span", { class: "muted small" }, c.detail),
          c.fix && (c.status === "missing" || c.status === "warn") ? h("div", { class: "small" }, "→ " + c.fix) : null,
          c.link && c.status !== "ok" ? h("div", { class: "small" }, h("a", { href: c.link, target: "_blank", rel: "noopener" }, "Download / instructions ↗")) : null))),
      h("p", { class: "muted small", style: "margin-top:10px" }, "HOMES folder: ", h("code", {}, state.status.repo)),
      missing.length
        ? h("div", { class: "note bad" }, "Fix before running: " + missing.map((c) => c.title).join(", ") + ". Then press “Check again”.")
        : h("div", { class: "note good" }, "All set. Try a test run: ", h("a", { href: "#", "data-goto": "new" }, "New analysis → Built-in test data")));
  }

  // ------------------------------------------------------- file browser --
  function openBrowser({ mode, start, title, append }) {
    if (!state.server) { toast("Browsing files needs the local server"); return Promise.resolve(null); }
    return new Promise((resolve) => {
      let current = null, selected = null;
      const pathInput = h("input", { type: "text", class: "mono", onkeydown: (e) => { if (e.key === "Enter") go(pathInput.value); } });
      const listBox = h("div", {});
      const err = h("div", {});
      const go = async (p) => {
        try {
          const res = await api("/api/browse?path=" + encodeURIComponent(p || ""));
          current = res; selected = null; setKids(err, );
          pathInput.value = res.path;
          setKids(listBox, 
            res.parent ? h("div", { class: "fb-entry", onclick: () => go(res.parent) }, h("span", { class: "ic" }, "⬆"), "..") : null,
            ...res.entries.map((e) => {
              const row = h("div", { class: "fb-entry" },
                h("span", { class: "ic" }, e.dir ? "📁" : "📄"), e.name,
                e.size != null ? h("span", { class: "sz" }, fmtSize(e.size)) : null);
              row.addEventListener("click", () => {
                if (e.dir && mode === "folder") { go(e.path); return; }
                $$(".fb-entry.sel", listBox).forEach((x) => x.classList.remove("sel"));
                row.classList.add("sel"); selected = e;
              });
              row.addEventListener("dblclick", () => { if (e.dir) go(e.path); else if (mode !== "folder") finish(e.path); });
              return row;
            }));
          if (!res.entries.length) listBox.append(h("p", { class: "muted small" }, "Empty folder."));
        } catch (e) { setKids(err, h("div", { class: "note bad" }, e.message)); }
      };
      let done = false;
      const finish = (v) => { if (done) return; done = true; close(); resolve(v); };
      const buttons = [];
      if (mode !== "file") buttons.push([mode === "folder" ? "Use this folder" : "Use current folder", "", () => {
        let p = current && current.path;
        if (p && append) p = p.replace(/\/$/, "") + "/" + append + "." + sheetDef().ext;
        finish(p); return false;
      }]);
      buttons.push(["Select", "primary", () => {
        if (selected && (mode !== "folder" || selected.dir)) {
          if (selected.dir && mode === "file") { go(selected.path); return false; }
          finish(selected.path); return false;
        }
        if (mode === "folder" && current) { finish(current.path); return false; }
        toast("Pick an item first"); return false;
      }]);
      const close = modal(title || (mode === "folder" ? "Choose a folder" : "Choose a file"), [
        h("div", { class: "row", style: "margin-bottom:8px" }, pathInput,
          h("button", { class: "btn small", onclick: () => go(pathInput.value) }, "Go"),
          h("button", { class: "btn small", onclick: () => go(state.status.repo) }, "HOMES folder")),
        err, listBox,
      ], buttons, false, () => { if (!done) { done = true; resolve(null); } });
      const startDir = start ? (start.startsWith("/") ? start : state.status.repo + "/" + start) : state.status.repo;
      go(startDir).then(() => { if (!current) go(state.status.repo); });
    });
  }

  function fmtSize(n) {
    if (n < 1024) return n + " B";
    const u = ["KB", "MB", "GB", "TB"]; let i = -1;
    do { n /= 1024; i++; } while (n >= 1024 && i < u.length - 1);
    return n.toFixed(n < 10 ? 1 : 0) + " " + u[i];
  }

  // -------------------------------------------------------------- modal --
  function modal(title, body, buttons, wide, onClose) {
    const root = $("#modal-root");
    const close = () => { back.remove(); document.removeEventListener("keydown", onKey); if (onClose) onClose(); };
    const onKey = (e) => { if (e.key === "Escape") close(); };
    const footer = h("footer", {}, h("button", { class: "btn", onclick: close }, buttons && buttons.length ? "Cancel" : "Close"),
      ...(buttons || []).map(([label, cls, fn]) => h("button", { class: "btn " + cls, onclick: () => { if (fn() !== false) close(); } }, label)));
    const box = h("div", { class: "modal", role: "dialog", "aria-modal": "true", style: wide ? "width:min(1100px,100%)" : "" },
      h("header", {}, h("h3", {}, title), h("button", { class: "btn small", onclick: close, "aria-label": "Close" }, "✕")),
      h("div", { class: "body" }, ...body), footer);
    const back = h("div", { class: "modal-back", onclick: (e) => { if (e.target === back) close(); } }, box);
    root.append(back);
    document.addEventListener("keydown", onKey);
    return close;
  }

  // --------------------------------------------------------------- boot --
  function applyServerMode() {
    $$(".server-only").forEach((el) => el.classList.toggle("hidden", !state.server));
    $$(".static-only").forEach((el) => el.classList.toggle("hidden", state.server));
  }

  async function boot() {
    renderHome();
    renderForm();
    state.server = await detectServer();
    const conn = $("#conn");
    conn.className = "conn " + (state.server ? "on" : "off");
    conn.textContent = state.server ? "● Connected" : "Command-builder mode";
    conn.title = state.server ? "Connected to the local HOMES dashboard server" : "Open via python3 dashboard/homes_dashboard.py to launch runs";
    applyServerMode();
    renderHome();
    renderForm();
    if (state.server) refreshRuns();
    else renderHomeRuns();
    const initial = (location.hash || "").slice(1);
    if (initial && $("#view-" + initial)) show(initial);
  }
  boot();
})();
