#!/usr/bin/env python3

import argparse
import csv
import html
from pathlib import Path


def read_tsv(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def table_html(rows, limit=None):
    if not rows:
        return "<p>No rows available.</p>"
    rows = rows[:limit] if limit else rows
    headers = list(rows[0].keys())
    body = []
    body.append("<table>")
    body.append("<thead><tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in headers) + "</tr></thead>")
    body.append("<tbody>")
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(h, '')))}</td>" for h in headers) + "</tr>")
    body.append("</tbody></table>")
    return "\n".join(body)


def metric_cards(stats_rows, qc_rows):
    stats = stats_rows[0] if stats_rows else {}
    total_reads = sum(int(float(row.get("total_reads", 0) or 0)) for row in qc_rows)
    total_bases = sum(int(float(row.get("total_bases", 0) or 0)) for row in qc_rows)
    metrics = [
        ("Input reads", total_reads),
        ("Input bases", total_bases),
        ("Contigs", stats.get("contigs", "0")),
        ("Assembly N50", stats.get("n50", "0")),
        ("Total contig bases", stats.get("total_bases", "0")),
        ("GC percent", stats.get("gc_percent", "0")),
    ]
    return "\n".join(
        f"<div class=\"metric\"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>"
        for label, value in metrics
    )


def count_rows(rows):
    return len(rows or [])


def logo_html():
    return """
<div class="title-logo-brand">
  <div class="title-logo-mark">H</div>
  <div class="title-logo-copy">
    <div class="title-logo-name">HOMES</div>
    <div class="title-logo-tagline">Harmonizing 'Omics for Managing</div>
    <div class="title-logo-tagline">Environmental Systems</div>
  </div>
</div>
""".strip()


def main():
    parser = argparse.ArgumentParser(description="Build HOMES assembly HTML report.")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--trim_summary", required=True)
    parser.add_argument("--qc", required=True)
    parser.add_argument("--length_distribution", required=True)
    parser.add_argument("--qvalue_distribution", required=True)
    parser.add_argument("--assembly_stats", required=True)
    parser.add_argument("--contigs", required=True)
    parser.add_argument("--binning_summary", required=True)
    parser.add_argument("--annotation_summary", required=True)
    parser.add_argument("--functional_annotations", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--logo", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    trim_rows = read_tsv(args.trim_summary)
    qc_rows = read_tsv(args.qc)
    length_rows = read_tsv(args.length_distribution)
    qvalue_rows = read_tsv(args.qvalue_distribution)
    stats_rows = read_tsv(args.assembly_stats)
    binning_rows = read_tsv(args.binning_summary)
    annotation_rows = read_tsv(args.annotation_summary)
    functional_rows = read_tsv(args.functional_annotations)
    command_text = Path(args.command).read_text().strip()

    title = f"HOMES Assembly {args.platform.capitalize()} Report"
    html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{
  color-scheme: light;
  --ink: #17202a;
  --muted: #5d6d7e;
  --line: #d8dee6;
  --panel: #f7f9fb;
  --accent: #006d77;
}}
body {{
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--ink);
  background: #ffffff;
}}
main {{
  max-width: 1120px;
  margin: 0 auto;
  padding: 34px 28px 56px;
}}
.title-logo-brand {{
  display: flex;
  align-items: center;
  gap: 22px;
  margin-bottom: 28px;
}}
.title-logo-mark {{
  width: 104px;
  height: 104px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  background: var(--accent);
  color: white;
  font-weight: 800;
  font-size: 64px;
  line-height: 1;
}}
.title-logo-name {{
  font-size: 58px;
  line-height: 0.95;
  font-weight: 800;
  letter-spacing: 0;
}}
.title-logo-tagline {{
  font-size: 20px;
  line-height: 1.24;
  color: var(--muted);
}}
h1 {{
  font-size: 34px;
  margin: 0 0 8px;
}}
h2 {{
  font-size: 22px;
  margin-top: 34px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}}
.lead {{
  color: var(--muted);
  max-width: 780px;
  line-height: 1.55;
}}
.metrics {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
  margin: 24px 0;
}}
.metric {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
}}
.metric span {{
  display: block;
  color: var(--muted);
  font-size: 13px;
}}
.metric strong {{
  display: block;
  font-size: 24px;
  margin-top: 6px;
}}
table {{
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0 18px;
  font-size: 13px;
}}
th, td {{
  border: 1px solid var(--line);
  padding: 8px 10px;
  text-align: left;
}}
th {{
  background: var(--panel);
}}
pre {{
  background: #101820;
  color: #f2f5f7;
  padding: 14px;
  border-radius: 8px;
  overflow-x: auto;
}}
@media (max-width: 620px) {{
  main {{ padding: 24px 18px 42px; }}
  .title-logo-brand {{ align-items: flex-start; gap: 14px; }}
  .title-logo-mark {{ width: 74px; height: 74px; font-size: 46px; border-radius: 14px; }}
  .title-logo-name {{ font-size: 40px; }}
  .title-logo-tagline {{ font-size: 15px; }}
}}
</style>
</head>
<body>
<main>
{logo_html()}
<h1>{html.escape(title)}</h1>
<p class="lead">Reads-to-genomes summary for HOMES. This report includes trimming/filtering, read-level QC, assembly statistics, binning, genome annotation, functional gene annotation, and the exact assembler command used for this run.</p>
<section class="metrics">
{metric_cards(stats_rows, qc_rows)}
<div class="metric"><span>Bins</span><strong>{count_rows(binning_rows)}</strong></div>
<div class="metric"><span>Annotated genomes</span><strong>{count_rows(annotation_rows)}</strong></div>
<div class="metric"><span>Functional genes</span><strong>{count_rows(functional_rows)}</strong></div>
</section>
<h2>Trim / Filter Summary</h2>
{table_html(trim_rows)}
<h2>Assembly Statistics</h2>
{table_html(stats_rows)}
<h2>Binning Summary</h2>
{table_html(binning_rows)}
<h2>Genome Annotation Summary</h2>
{table_html(annotation_rows)}
<h2>Functional Gene Annotation</h2>
{table_html(functional_rows, limit=80)}
<h2>Read QC</h2>
{table_html(qc_rows)}
<h2>Length Distribution</h2>
{table_html(length_rows, limit=40)}
<h2>Q Value Distribution</h2>
{table_html(qvalue_rows, limit=40)}
<h2>Assembler Command</h2>
<pre>{html.escape(command_text)}</pre>
<h2>Contigs</h2>
<p class="lead">Contigs file: {html.escape(Path(args.contigs).name)}</p>
</main>
</body>
</html>
"""
    Path(args.output).write_text(html_text)


if __name__ == "__main__":
    main()
