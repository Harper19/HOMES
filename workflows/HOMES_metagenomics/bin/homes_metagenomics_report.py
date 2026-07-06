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


def table_html(title, rows, section_id=None):
    section_attr = f' id="{html.escape(section_id)}"' if section_id else ""
    if not rows:
        return f"<section{section_attr}><h2>{html.escape(title)}</h2><p>No records.</p></section>"
    headers = list(rows[0].keys())
    out = [f"<section{section_attr}>", f"<h2>{html.escape(title)}</h2>", "<table>", "<thead><tr>"]
    out.extend(f"<th>{html.escape(header)}</th>" for header in headers)
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        out.extend(f"<td>{html.escape(str(row.get(header, '')))}</td>" for header in headers)
        out.append("</tr>")
    out.append("</tbody></table></section>")
    return "\n".join(out)


def inline_logo(path):
    if not path:
        return ""
    logo_path = Path(path)
    if not logo_path.exists():
        return ""
    content = logo_path.read_text()
    if "<svg" in content:
        return f'<div class="logo">{content}</div>'
    return ""


def toc_logo(path):
    return """
<div class="toc-logo">
  <div class="toc-logo-mark">H</div>
  <div class="toc-logo-copy">
    <div class="toc-logo-name">HOMES</div>
    <div class="toc-logo-tagline">Harmonizing 'Omics for Managing<br>Environmental Systems</div>
  </div>
</div>
"""


def toc_html():
    items = [
        ("qc-summary", "QC Summary"),
        ("read-length-distribution", "Length Distribution"),
        ("qvalue-distribution", "Q Value Distribution"),
        ("top-taxa", "Top Taxa"),
        ("taxonomy", "Taxonomy"),
        ("abundance-counts", "Abundance Counts"),
        ("relative-abundance", "Relative Abundance"),
    ]
    links = "\n".join(f'<li><a href="#{anchor}">{html.escape(label)}</a></li>' for anchor, label in items)
    return f'<ul class="nav nav-pills nav-stacked">{links}</ul>'


def platform_label(platform):
    return "Nanopore" if platform == "nanopore" else "Illumina"


def read_qc_plot(rows):
    parsed = []
    for row in rows:
        try:
            parsed.append(
                {
                    "sample": row.get("sample", "Unknown"),
                    "mean_read_length": float(row.get("mean_read_length", 0.0)),
                    "n50_read_length": float(row.get("n50_read_length", 0.0)),
                    "mean_read_quality": float(row.get("mean_read_quality", 0.0)),
                }
            )
        except ValueError:
            continue

    if not parsed:
        return "<p>No read QC rows.</p>"

    width = 920
    row_height = 34
    label_width = 220
    plot_width = 260
    gap = 100
    height = 58 + row_height * len(parsed)
    max_length = max(max(item["mean_read_length"], item["n50_read_length"]) for item in parsed) or 1
    max_quality = max(item["mean_read_quality"] for item in parsed) or 1

    out = [
        f'<svg viewBox="0 0 {width} {height}" role="img">',
        "<style>text{font-family:Arial,sans-serif;font-size:13px}.mean{fill:#1f9e89}.n50{fill:#194d44}.qual{fill:#d95f02}.axis{fill:#5f6368}</style>",
        '<text class="axis" x="0" y="18">Sample</text>',
        f'<text class="axis" x="{label_width}" y="18">Mean / N50 length</text>',
        f'<text class="axis" x="{label_width + plot_width + gap}" y="18">Mean Q value</text>',
    ]

    for index, item in enumerate(parsed):
        y = 42 + index * row_height
        mean_width = max(1, item["mean_read_length"] / max_length * plot_width)
        n50_width = max(1, item["n50_read_length"] / max_length * plot_width)
        quality_x = label_width + plot_width + gap
        quality_width = max(1, item["mean_read_quality"] / max_quality * plot_width)
        out.append(f'<text x="0" y="{y + 15}">{html.escape(item["sample"][:28])}</text>')
        out.append(f'<rect class="n50" x="{label_width}" y="{y}" width="{n50_width:.2f}" height="8"></rect>')
        out.append(f'<rect class="mean" x="{label_width}" y="{y + 10}" width="{mean_width:.2f}" height="8"></rect>')
        out.append(
            f'<text x="{label_width + max(mean_width, n50_width) + 8:.2f}" y="{y + 15}">'
            f'mean {item["mean_read_length"]:.0f}; N50 {item["n50_read_length"]:.0f}</text>'
        )
        out.append(f'<rect class="qual" x="{quality_x}" y="{y}" width="{quality_width:.2f}" height="18"></rect>')
        out.append(f'<text x="{quality_x + quality_width + 8:.2f}" y="{y + 15}">Q{item["mean_read_quality"]:.2f}</text>')

    out.append("</svg>")
    return "\n".join(out)


def grouped_distribution(rows, value_key):
    grouped = {}
    for row in rows:
        sample = row.get("sample") or "Sample"
        try:
            if value_key == "length":
                value = int(float(row.get("length_bin_start", 0)))
                label = f"{int(float(row.get('length_bin_start', 0)))}-{int(float(row.get('length_bin_end', 0)))}"
            else:
                value = int(float(row.get("q_bin", 0)))
                label = f"Q{value}"
            count = int(float(row.get("read_count", 0)))
        except ValueError:
            continue
        grouped.setdefault(sample, []).append((value, label, count))
    for sample in grouped:
        grouped[sample] = sorted(grouped[sample], key=lambda item: item[0])
    return grouped


def distribution_svg(title, rows, value_key, section_id):
    grouped = grouped_distribution(rows, value_key)
    if not grouped:
        return f'<section id="{section_id}"><h2>{html.escape(title)}</h2><p>No distribution rows.</p></section>'

    width = 920
    plot_width = 760
    left = 130
    sample_height = 150
    height = 46 + sample_height * len(grouped)
    max_count = max(count for values in grouped.values() for _, _, count in values) or 1
    max_bins = max(len(values) for values in grouped.values()) or 1
    bar_gap = 2
    bar_width = max(2, min(18, (plot_width - (max_bins - 1) * bar_gap) / max_bins))

    parts = [
        f'<section id="{section_id}">',
        f'<h2>{html.escape(title)}</h2>',
        f'<svg viewBox="0 0 {width} {height}" role="img">',
        "<style>text{font-family:Arial,sans-serif;font-size:12px}.bar{fill:#1f9e89}.sample{font-weight:bold;font-size:14px}.axis{fill:#5f6368}</style>",
    ]
    y0 = 36
    for sample, values in grouped.items():
        parts.append(f'<text class="sample" x="0" y="{y0}">{html.escape(sample)}</text>')
        baseline = y0 + 96
        parts.append(f'<line x1="{left}" y1="{baseline}" x2="{left + plot_width}" y2="{baseline}" stroke="#d4d7dc"></line>')
        for idx, (_, label, count) in enumerate(values):
            x = left + idx * (bar_width + bar_gap)
            bar_height = max(1, count / max_count * 86)
            y = baseline - bar_height
            parts.append(f'<rect class="bar" x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}"><title>{html.escape(label)}: {count}</title></rect>')
        if values:
            parts.append(f'<text class="axis" x="{left}" y="{baseline + 18}">{html.escape(values[0][1])}</text>')
            parts.append(f'<text class="axis" x="{left + plot_width - 80}" y="{baseline + 18}">{html.escape(values[-1][1])}</text>')
            parts.append(f'<text class="axis" x="{left + plot_width + 8}" y="{baseline - 78}">max {max(count for _, _, count in values)}</text>')
        y0 += sample_height
    parts.append("</svg></section>")
    return "\n".join(parts)


def abundance_plot(rows):
    parsed = []
    for row in rows:
        try:
            parsed.append((row.get("taxon", "Unknown"), float(row.get("relative_abundance", 0.0))))
        except ValueError:
            continue
    parsed = sorted(parsed, key=lambda value: value[1], reverse=True)[:20]
    if not parsed:
        return '<section id="top-taxa"><h2>Top Taxa</h2><p>No abundance rows.</p></section>'

    width = 920
    row_height = 26
    label_width = 280
    plot_width = width - label_width - 80
    height = 48 + row_height * len(parsed)
    out = [f'<section id="top-taxa"><h2>Top Taxa</h2><svg viewBox="0 0 {width} {height}" role="img">']
    out.append("<style>text{font-family:Arial,sans-serif;font-size:13px}.bar{fill:#1f9e89}</style>")
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
    parser.add_argument("--length_distribution", nargs="*", default=[])
    parser.add_argument("--qvalue_distribution", nargs="*", default=[])
    parser.add_argument("--taxonomy", nargs="*", default=[])
    parser.add_argument("--abundance", nargs="*", default=[])
    parser.add_argument("--relative_abundance", nargs="*", default=[])
    parser.add_argument("--logo")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    qc_rows = []
    for path in args.qc:
        qc_rows.extend(read_tsv(path))

    length_rows = []
    for path in args.length_distribution:
        length_rows.extend(read_tsv(path))

    qvalue_rows = []
    for path in args.qvalue_distribution:
        qvalue_rows.extend(read_tsv(path))

    taxonomy_rows = []
    for path in args.taxonomy:
        taxonomy_rows.extend(read_tsv(path))

    abundance_rows = []
    for path in args.abundance:
        abundance_rows.extend(read_tsv(path))

    relative_rows = []
    for path in args.relative_abundance:
        relative_rows.extend(read_tsv(path))

    platform = platform_label(args.platform)
    css = """
body{font-family:Calibri,helvetica,sans-serif;margin:0;color:#202124;line-height:1.45;background:#fff}
h1{color:rgb(36,176,100);font-size:200%;margin:16px 0 4px}h2{color:rgb(36,176,100);font-size:150%;margin-top:30px}
h3.subtitle{font-size:120%;color:#000;font-weight:bold;margin:4px 0 18px}
table{border-collapse:collapse;width:100%;margin-top:10px;font-size:14px}th,td{border:1px solid #d4d7dc;padding:7px;text-align:left}
th{background:#f2f4f7}section{margin-bottom:22px}a{color:#24b064;text-decoration:none}
.main-container{max-width:1160px;margin-left:310px;padding:28px 42px 60px}
#TOC{position:fixed;left:0;top:0;bottom:0;width:270px;overflow-y:auto;background:#f8f8f8;border-right:1px solid #e2e2e2;padding:18px 18px 28px}
.toc-logo{display:flex;align-items:center;gap:10px;margin-bottom:22px;padding:8px 0}
.toc-logo-mark{flex:0 0 58px;width:58px;height:58px;border-radius:8px;background:#194d44;color:#f7faf8;display:flex;align-items:center;justify-content:center;font-family:Arial,Helvetica,sans-serif;font-size:30px;font-weight:700}
.toc-logo-copy{min-width:0}.toc-logo-name{font-family:Arial,Helvetica,sans-serif;font-size:30px;font-weight:700;letter-spacing:1px;line-height:1;color:#194d44}
.toc-logo-tagline{font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.18;color:#45635d;margin-top:5px}
.title-logo{max-width:900px}.title-logo svg{width:100%;max-width:900px;height:auto;display:block;margin-bottom:18px}
.nav{list-style:none;padding-left:0;margin:0}.nav li a{display:block;padding:8px 10px;border-radius:4px;color:#333}
.nav li a:hover{background:#e7f5ed;color:#24b064}.nav li:first-child a{background:#24b064;color:#fff}
.badge{display:inline-block;background:#24b064;color:white;padding:5px 9px;border-radius:4px;font-size:13px;margin-right:6px;margin-bottom:4px}
.subtle{color:#45635d}.platform-line{margin:10px 0 16px}svg{max-width:100%;height:auto}
@media(max-width:900px){#TOC{position:static;width:auto;border-right:0}.main-container{margin-left:0;padding:22px}}
"""
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HOMES_metagenomics {html.escape(platform)} report</title>
<style>{css}</style>
</head>
<body>
<nav id="TOC">
{toc_logo(args.logo)}
{toc_html()}
</nav>
<main class="main-container">
<div class="title-logo">{inline_logo(args.logo)}</div>
<h1>HOMES_metagenomics<br>{html.escape(platform)} report</h1>
<h3 class="subtitle">HOMES_metagenomics {html.escape(platform)} workflow</h3>
<p><strong>HOMES</strong>: Harmonizing 'Omics for Managing Environmental Systems</p>
<p class="platform-line"><span class="badge">Platform: {html.escape(platform)}</span><span class="badge">Classifier: Kraken2-ready</span><span class="badge">Report: QC, taxonomy, abundance</span></p>
<p class="subtle">Shotgun metagenomics QC, taxonomy, abundance, and reporting summary. QC includes N50 read length, read length distributions, and Q value distributions.</p>
<section id="qc-summary">
<h2>QC Summary</h2>
{read_qc_plot(qc_rows)}
</section>
{table_html("QC Summary Table", qc_rows)}
{distribution_svg("Length Distribution", length_rows, "length", "read-length-distribution")}
{distribution_svg("Q Value Distribution", qvalue_rows, "qvalue", "qvalue-distribution")}
{abundance_plot(relative_rows)}
{table_html("Taxonomy", taxonomy_rows, "taxonomy")}
{table_html("Abundance Counts", abundance_rows, "abundance-counts")}
{table_html("Relative Abundance", relative_rows, "relative-abundance")}
</main>
</body>
</html>
"""
    Path(args.output).write_text(doc)


if __name__ == "__main__":
    main()
