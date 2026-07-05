#!/usr/bin/env python3

import argparse
import csv
import html
from pathlib import Path


def read_tsv(path):
    rows = []
    if not path:
        return rows
    with Path(path).open() as handle:
        rows.extend(csv.DictReader(handle, delimiter="\t"))
    return rows


def table_html(title, rows):
    if not rows:
        return f"<section><h2>{html.escape(title)}</h2><p>No records.</p></section>"
    headers = list(rows[0].keys())
    out = ["<section>", f"<h2>{html.escape(title)}</h2>", "<table>", "<thead><tr>"]
    out.extend(f"<th>{html.escape(header)}</th>" for header in headers)
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        out.extend(f"<td>{html.escape(str(row.get(header, '')))}</td>" for header in headers)
        out.append("</tr>")
    out.append("</tbody></table></section>")
    return "\n".join(out)


def read_qc_plot(rows):
    parsed = []
    for row in rows:
        try:
            parsed.append(
                {
                    "sample": row.get("sample", "Unknown"),
                    "mean_read_length": float(row.get("mean_read_length", 0.0)),
                    "min_read_length": float(row.get("min_read_length", 0.0)),
                    "max_read_length": float(row.get("max_read_length", 0.0)),
                    "mean_read_quality": float(row.get("mean_read_quality", 0.0)),
                }
            )
        except ValueError:
            continue

    if not parsed:
        return "<section><h2>Read Length and Quality</h2><p>No read QC rows.</p></section>"

    width = 940
    row_height = 34
    label_width = 230
    plot_width = 280
    gap = 90
    height = 72 + row_height * len(parsed)
    max_length = max(max(item["max_read_length"], item["mean_read_length"]) for item in parsed) or 1
    max_quality = max(item["mean_read_quality"] for item in parsed) or 1

    out = [
        f'<section><h2>Read Length and Quality</h2><svg viewBox="0 0 {width} {height}" role="img">',
        "<style>text{font-family:Arial,sans-serif;font-size:13px}.len{fill:#2878b5}.qual{fill:#d95f02}.axis{fill:#5f6368}</style>",
        '<text class="axis" x="0" y="18">Sample</text>',
        f'<text class="axis" x="{label_width}" y="18">Mean read length</text>',
        f'<text class="axis" x="{label_width + plot_width + gap}" y="18">Mean read quality</text>',
    ]

    for index, item in enumerate(parsed):
        y = 42 + index * row_height
        length_width = max(1, item["mean_read_length"] / max_length * plot_width)
        quality_width = max(1, item["mean_read_quality"] / max_quality * plot_width)
        quality_x = label_width + plot_width + gap
        out.append(f'<text x="0" y="{y + 15}">{html.escape(item["sample"][:28])}</text>')
        out.append(f'<rect class="len" x="{label_width}" y="{y}" width="{length_width:.2f}" height="18"></rect>')
        out.append(
            f'<text x="{label_width + length_width + 8:.2f}" y="{y + 15}">'
            f'{item["mean_read_length"]:.2f} bp ({item["min_read_length"]:.0f}-{item["max_read_length"]:.0f})</text>'
        )
        out.append(f'<rect class="qual" x="{quality_x}" y="{y}" width="{quality_width:.2f}" height="18"></rect>')
        out.append(f'<text x="{quality_x + quality_width + 8:.2f}" y="{y + 15}">Q{item["mean_read_quality"]:.2f}</text>')

    out.append("</svg></section>")
    return "\n".join(out)


def abundance_plot(rows):
    parsed = []
    for row in rows:
        try:
            parsed.append((row.get("taxon", "Unknown"), float(row.get("relative_abundance", 0.0))))
        except ValueError:
            continue
    parsed = sorted(parsed, key=lambda value: value[1], reverse=True)[:20]
    if not parsed:
        return "<section><h2>Top Taxa</h2><p>No abundance rows.</p></section>"

    width = 920
    row_height = 26
    label_width = 280
    plot_width = width - label_width - 80
    height = 48 + row_height * len(parsed)
    out = [f'<section><h2>Top Taxa</h2><svg viewBox="0 0 {width} {height}" role="img">']
    out.append("<style>text{font-family:Arial,sans-serif;font-size:13px}.bar{fill:#2a9d8f}</style>")
    for index, (taxon, rel_abundance) in enumerate(parsed):
        y = 32 + index * row_height
        bar_width = max(1, rel_abundance * plot_width)
        out.append(f'<text x="0" y="{y + 14}">{html.escape(taxon[:45])}</text>')
        out.append(f'<rect class="bar" x="{label_width}" y="{y}" width="{bar_width:.2f}" height="18"></rect>')
        out.append(f'<text x="{label_width + bar_width + 8:.2f}" y="{y + 14}">{rel_abundance * 100:.2f}%</text>')
    out.append("</svg></section>")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Build the HOMES metagenomics HTML report.")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--qc", nargs="*", default=[])
    parser.add_argument("--taxonomy", nargs="*", default=[])
    parser.add_argument("--abundance", nargs="*", default=[])
    parser.add_argument("--relative_abundance", nargs="*", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    qc_rows = []
    for path in args.qc:
        qc_rows.extend(read_tsv(path))

    taxonomy_rows = []
    for path in args.taxonomy:
        taxonomy_rows.extend(read_tsv(path))

    abundance_rows = []
    for path in args.abundance:
        abundance_rows.extend(read_tsv(path))

    relative_rows = []
    for path in args.relative_abundance:
        relative_rows.extend(read_tsv(path))

    css = """
body{font-family:Arial,sans-serif;margin:32px;color:#202124;line-height:1.45}
h1{font-size:28px;margin-bottom:4px}h2{font-size:19px;margin-top:28px}
table{border-collapse:collapse;width:100%;margin-top:10px}th,td{border:1px solid #d4d7dc;padding:7px;text-align:left}
th{background:#f2f4f7}section{margin-bottom:22px}
"""
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HOMES_metagenomics {html.escape(args.platform)} report</title>
<style>{css}</style>
</head>
<body>
<h1>HOMES_metagenomics {html.escape(args.platform)} report</h1>
<p>QC, taxonomy, abundance, and reporting summary.</p>
{table_html("QC Summary", qc_rows)}
{read_qc_plot(qc_rows)}
{abundance_plot(relative_rows)}
{table_html("Taxonomy", taxonomy_rows)}
{table_html("Abundance Counts", abundance_rows)}
{table_html("Relative Abundance", relative_rows)}
</body>
</html>
"""
    Path(args.output).write_text(doc)


if __name__ == "__main__":
    main()
