#!/usr/bin/env python3

import argparse
import csv
import html
import math
from pathlib import Path


def read_tsv(path):
    rows = []
    if not path:
        return rows
    with Path(path).open() as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows.extend(reader)
    return rows


def table_html(title, rows, section_id=None):
    section_attr = f' id="{html.escape(section_id)}"' if section_id else ""
    if not rows:
        return f"<section{section_attr}><h2>{html.escape(title)}</h2><p>No records.</p></section>"
    headers = list(rows[0].keys())
    body = [f"<section{section_attr}>", f"<h2>{html.escape(title)}</h2>", "<table>", "<thead><tr>"]
    body.extend(f"<th>{html.escape(header)}</th>" for header in headers)
    body.append("</tr></thead><tbody>")
    for row in rows:
        body.append("<tr>")
        body.extend(f"<td>{html.escape(str(row.get(header, '')))}</td>" for header in headers)
        body.append("</tr>")
    body.append("</tbody></table></section>")
    return "\n".join(body)


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
    if not path:
        return ""
    logo_path = Path(path)
    if not logo_path.exists():
        return ""
    content = logo_path.read_text()
    if "<svg" in content:
        return f'<div class="toc-logo">{content}</div>'
    return ""


def toc_html():
    items = [
        ("read-qc-summary", "Read QC Summary"),
        ("top-taxa-per-sample", "Top Taxa Per Sample"),
        ("abundance", "Abundance"),
        ("lineage-sankey", "Lineage Sankey"),
        ("lineage-sunburst", "Lineage Sunburst"),
        ("taxonomy-explorer", "Taxonomy Explorer"),
        ("alpha-diversity", "Alpha Diversity"),
    ]
    links = "\n".join(f'<li><a href="#{anchor}">{html.escape(label)}</a></li>' for anchor, label in items)
    return f'<ul class="nav nav-pills nav-stacked">{links}</ul>'


def rows_by_sample(rows):
    grouped = {}
    for row in rows:
        sample = row.get("sample") or "Sample"
        grouped.setdefault(sample, []).append(row)
    return grouped


def preferred_visual_rows(rows):
    if not rows:
        return rows
    available = []
    for row in rows:
        level = (row.get("tax_level") or "taxonomy").strip()
        if level and level not in available:
            available.append(level)
    for level in ["genus", "species", "family", "order", "class", "phylum", "kingdom", "reference"]:
        if level in available:
            return [row for row in rows if (row.get("tax_level") or "").strip() == level]
    return rows


def abundance_matrix_html(rows):
    if not rows:
        return '<section id="abundance"><h2>Abundance</h2><p>No relative abundance table was generated.</p></section>'

    levels = []
    for row in rows:
        level = (row.get("tax_level") or "taxonomy").strip() or "taxonomy"
        if level not in levels:
            levels.append(level)

    options = "\n".join(
        f'<option value="abundance-level-{html.escape(level)}">{html.escape(level)}</option>'
        for level in levels
    )
    parts = [
        '<section id="abundance">',
        '<h2>Abundance</h2>',
        '<p>Relative abundance is calculated independently within each sample. Rows are taxa and columns are sample IDs.</p>',
        '<label for="abundance-level-select"><strong>Taxonomy level</strong></label> ',
        f'<select id="abundance-level-select" onchange="showAbundanceLevel()">{options}</select>',
    ]

    for idx, level in enumerate(levels):
        level_rows = [row for row in rows if (row.get("tax_level") or "taxonomy").strip() == level]
        samples = sorted({row.get("sample") or "Sample" for row in level_rows})
        taxa = sorted({row.get("taxon") or "Unclassified" for row in level_rows})
        values = {}
        for row in level_rows:
            sample = row.get("sample") or "Sample"
            taxon = row.get("taxon") or "Unclassified"
            try:
                value = float(row.get("relative_abundance", 0)) * 100
            except ValueError:
                value = 0.0
            values[(taxon, sample)] = value

        style = "" if idx == 0 else ' style="display:none"'
        parts.append(f'<div class="abundance-level" id="abundance-level-{html.escape(level)}"{style}>')
        parts.append(f'<h3>{html.escape(level.title())}</h3>')
        parts.append('<table class="abundance-table"><thead><tr><th>Taxa</th>')
        parts.extend(f'<th>{html.escape(sample)}</th>' for sample in samples)
        parts.append('</tr></thead><tbody>')
        for taxon in taxa:
            parts.append(f'<tr><th>{html.escape(taxon)}</th>')
            for sample in samples:
                parts.append(f'<td>{values.get((taxon, sample), 0.0):.4f}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div>')

    parts.append(
        """
<script>
function showAbundanceLevel() {
  const selected = document.getElementById('abundance-level-select').value;
  document.querySelectorAll('.abundance-level').forEach(el => {
    el.style.display = el.id === selected ? '' : 'none';
  });
}
</script>
"""
    )
    parts.append('</section>')
    return "\n".join(parts)


def barplot_svg(rows, top_taxa):
    rows = preferred_visual_rows(rows)
    grouped_rows = {}
    for sample, sample_rows in rows_by_sample(rows).items():
        abundance_rows = []
        for row in sample_rows:
            try:
                abundance_rows.append((row.get("taxon", "Unknown"), float(row.get("relative_abundance", 0)), int(float(row.get("reads", 0)))))
            except ValueError:
                continue
        abundance_rows = sorted(abundance_rows, key=lambda item: item[1], reverse=True)[:top_taxa]
        if abundance_rows:
            grouped_rows[sample] = abundance_rows
    if not grouped_rows:
        return '<section id="top-taxa-per-sample"><h2>Top Taxa Per Sample</h2><p>No abundance table was generated.</p></section>'
    width = 900
    row_height = 26
    sample_header_height = 28
    label_width = 260
    plot_width = width - label_width - 40
    height = 42 + sum(sample_header_height + row_height * len(sample_rows) for sample_rows in grouped_rows.values())
    parts = [f'<section id="top-taxa-per-sample"><h2>Top Taxa Per Sample</h2><svg viewBox="0 0 {width} {height}" role="img">']
    parts.append('<style>text{font-family:Arial,sans-serif;font-size:13px}.sample{font-weight:bold;font-size:14px}.bar{fill:#1f9e89}</style>')
    y = 28
    for sample, abundance_rows in grouped_rows.items():
        parts.append(f'<text class="sample" x="0" y="{y}">{html.escape(sample)}</text>')
        y += sample_header_height
        for taxon, rel, reads in abundance_rows:
            bar_width = max(1, rel * plot_width)
            parts.append(f'<text x="0" y="{y + 14}">{html.escape(taxon[:42])}</text>')
            parts.append(f'<rect class="bar" x="{label_width}" y="{y}" width="{bar_width:.2f}" height="18"></rect>')
            parts.append(f'<text x="{label_width + bar_width + 8:.2f}" y="{y + 14}">{rel * 100:.2f}% ({reads})</text>')
            y += row_height
    parts.append("</svg></section>")
    return "\n".join(parts)


def lineage_parts(taxon):
    taxon = (taxon or "Unclassified").strip() or "Unclassified"
    for sep in (";", "|"):
        if sep in taxon:
            return [part.strip() for part in taxon.split(sep) if part.strip()]
    return [taxon]


def lineage_counts(rows):
    rows = preferred_visual_rows(rows)
    counts = {}
    for row in rows:
        try:
            reads = int(float(row.get("reads", 0)))
        except ValueError:
            reads = 0
        parts = lineage_parts(row.get("taxon", "Unclassified"))
        path = []
        for part in parts:
            path.append(part)
            key = tuple(path)
            counts[key] = counts.get(key, 0) + reads
    return counts


def sankey_svg(rows, top_taxa):
    counts = lineage_counts(rows)
    leaf_paths = sorted(
        [path for path in counts if len(path) > 0],
        key=lambda path: (-counts[path], path)
    )[:top_taxa]
    if not leaf_paths:
        return '<section id="lineage-sankey"><h2>Lineage Sankey</h2><p>No lineages available.</p></section>'
    width = 980
    row_height = 30
    height = max(120, 50 + len(leaf_paths) * row_height)
    max_depth = max(len(path) for path in leaf_paths)
    col_width = max(150, (width - 80) / max(max_depth, 1))
    parts = [f'<section id="lineage-sankey"><h2>Lineage Sankey</h2><svg viewBox="0 0 {width} {height}" role="img">']
    parts.append('<style>text{font-family:Arial,sans-serif;font-size:12px}.node{fill:#194d44}.link{stroke:#67a59b;stroke-opacity:.45;fill:none}</style>')
    for row_idx, path in enumerate(leaf_paths):
        y = 35 + row_idx * row_height
        for depth, name in enumerate(path):
            x = 20 + depth * col_width
            parts.append(f'<circle class="node" cx="{x:.1f}" cy="{y}" r="4"></circle>')
            parts.append(f'<text x="{x + 8:.1f}" y="{y + 4}">{html.escape(name[:22])}</text>')
            if depth > 0:
                x0 = 20 + (depth - 1) * col_width
                parts.append(f'<path class="link" d="M{x0:.1f},{y} C{x0 + col_width/2:.1f},{y} {x - col_width/2:.1f},{y} {x:.1f},{y}" stroke-width="3"></path>')
        parts.append(f'<text x="{width - 70}" y="{y + 4}">{counts[path]}</text>')
    parts.append("</svg></section>")
    return "\n".join(parts)


def sunburst_svg(rows, top_taxa):
    counts = lineage_counts(rows)
    top_paths = sorted(
        [path for path in counts if len(path) > 0],
        key=lambda path: (-counts[path], path)
    )[:top_taxa]
    if not top_paths:
        return '<section id="lineage-sunburst"><h2>Lineage Sunburst</h2><p>No lineages available.</p></section>'
    width = 760
    height = 760
    cx = width / 2
    cy = height / 2
    total = sum(counts[path] for path in top_paths) or 1
    colors = ["#194d44", "#1f9e89", "#45635d", "#6ab7a8", "#2f6f65", "#8accc0", "#355c7d", "#5a8ca8"]
    angle = -math.pi / 2
    parts = [f'<section id="lineage-sunburst"><h2>Lineage Sunburst</h2><svg viewBox="0 0 {width} {height}" role="img">']
    parts.append('<style>text{font-family:Arial,sans-serif;font-size:12px}.slice{stroke:white;stroke-width:1}</style>')
    legend_y = 24
    for idx, path in enumerate(top_paths):
        frac = counts[path] / total
        next_angle = angle + 2 * math.pi * frac
        depth = min(len(path), 7)
        r0 = 34
        r1 = 34 + depth * 34
        x0 = cx + r0 * math.cos(angle)
        y0 = cy + r0 * math.sin(angle)
        x1 = cx + r1 * math.cos(angle)
        y1 = cy + r1 * math.sin(angle)
        x2 = cx + r1 * math.cos(next_angle)
        y2 = cy + r1 * math.sin(next_angle)
        x3 = cx + r0 * math.cos(next_angle)
        y3 = cy + r0 * math.sin(next_angle)
        large = 1 if next_angle - angle > math.pi else 0
        color = colors[idx % len(colors)]
        d = f"M{x0:.2f},{y0:.2f} L{x1:.2f},{y1:.2f} A{r1},{r1} 0 {large} 1 {x2:.2f},{y2:.2f} L{x3:.2f},{y3:.2f} A{r0},{r0} 0 {large} 0 {x0:.2f},{y0:.2f} Z"
        label = " > ".join(path)
        parts.append(f'<path class="slice" d="{d}" fill="{color}"><title>{html.escape(label)}: {counts[path]}</title></path>')
        parts.append(f'<rect x="20" y="{legend_y}" width="12" height="12" fill="{color}"></rect>')
        parts.append(f'<text x="38" y="{legend_y + 11}">{html.escape(label[:58])} ({counts[path]})</text>')
        legend_y += 18
        angle = next_angle
    parts.append("</svg></section>")
    return "\n".join(parts)


def taxonomy_tree_html(rows):
    rows = preferred_visual_rows(rows)
    taxa = [row.get("taxon", "") for row in rows if row.get("taxon")]
    if not taxa:
        return '<section id="taxonomy-explorer"><h2>Taxonomy Explorer</h2><p>No taxonomy records.</p></section>'
    items = "\n".join(f"<li>{html.escape(taxon)}</li>" for taxon in taxa[:200])
    return f"""
<section id="taxonomy-explorer">
<h2>Taxonomy Explorer</h2>
<input id="tax-filter" placeholder="Filter taxa" oninput="filterTaxa()" />
<ul id="tax-list">{items}</ul>
<script>
function filterTaxa() {{
  const q = document.getElementById('tax-filter').value.toLowerCase();
  document.querySelectorAll('#tax-list li').forEach(li => {{
    li.style.display = li.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>
</section>
"""


def main():
    parser = argparse.ArgumentParser(description="Build a compact HOMES_amplicon Nanopore HTML report.")
    parser.add_argument("--qc", nargs="*", default=[])
    parser.add_argument("--relative_abundance", nargs="*", default=[])
    parser.add_argument("--diversity", nargs="*", default=[])
    parser.add_argument("--classifier", default="none")
    parser.add_argument("--target_marker", default="16S")
    parser.add_argument("--tax_level", default="genus")
    parser.add_argument("--top_taxa", type=int, default=20)
    parser.add_argument("--logo")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    qc_rows = []
    for path in args.qc:
        qc_rows.extend(read_tsv(path))

    abundance_rows = []
    for path in args.relative_abundance:
        abundance_rows.extend(read_tsv(path))

    diversity_rows = []
    for path in args.diversity:
        diversity_rows.extend(read_tsv(path))

    css = """
body{font-family:Calibri,helvetica,sans-serif;margin:0;color:#202124;line-height:1.45;background:#fff}
h1{color:rgb(36,176,100);font-size:200%;margin:16px 0 4px}h2{color:rgb(36,176,100);font-size:150%;margin-top:30px}
h3.subtitle{font-size:120%;color:#000;font-weight:bold;margin:4px 0 18px}
table{border-collapse:collapse;width:100%;margin-top:10px;font-size:14px}th,td{border:1px solid #d4d7dc;padding:7px;text-align:left}
th{background:#f2f4f7}section{margin-bottom:22px}input,select{padding:8px;border:1px solid #b8bdc7;max-width:100%}
a{color:#24b064;text-decoration:none}.main-container{max-width:980px;margin-left:310px;padding:28px 42px 60px}
#TOC{position:fixed;left:0;top:0;bottom:0;width:270px;overflow-y:auto;background:#f8f8f8;border-right:1px solid #e2e2e2;padding:18px 18px 28px}
.toc-logo svg{width:100%;height:auto;display:block;margin-bottom:18px}.title-logo svg{width:100%;max-width:900px;height:auto;display:block;margin-bottom:16px}
.nav{list-style:none;padding-left:0;margin:0}.nav li a{display:block;padding:8px 10px;border-radius:4px;color:#333}
.nav li a:hover{background:#e7f5ed;color:#24b064}.nav li:first-child a{background:#24b064;color:#fff}
.badge{display:inline-block;background:#24b064;color:white;padding:5px 9px;border-radius:4px;font-size:13px;margin-right:6px;margin-bottom:4px}
.subtle{color:#45635d}.platform-line{margin:10px 0 16px}
.abundance-table th:first-child{min-width:220px}.abundance-table td{text-align:right}
svg{max-width:100%;height:auto}@media(max-width:900px){#TOC{position:static;width:auto;border-right:0}.main-container{margin-left:0;padding:22px}}
"""
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HOMES_amplicon Nanopore report</title>
<style>{css}</style>
</head>
<body>
<nav id="TOC">
{toc_logo(args.logo)}
{toc_html()}
</nav>
<main class="main-container">
<div class="title-logo">{inline_logo(args.logo)}</div>
<h1>HOMES_amplicon<br>Nanopore report</h1>
<h3 class="subtitle">HOMES_amplicon Nanopore workflow</h3>
<p><strong>HOMES</strong>: Harmonizing 'Omics for Managing Environmental Systems</p>
<p class="platform-line"><span class="badge">Platform: Nanopore</span><span class="badge">Marker: {html.escape(args.target_marker)}</span><span class="badge">Classifier: {html.escape(args.classifier)}</span><span class="badge">Tax level: {html.escape(args.tax_level)}</span></p>
<p class="subtle">Nanopore-only amplicon QC, taxonomy, abundance, and diversity summary. The Nanopore branch follows the wf-16s-style concepts of minimap2 or kraken2 classification, taxonomic profiles, abundance tables, lineage exploration, and top-taxa comparison.</p>
{table_html("Read QC Summary", qc_rows, "read-qc-summary")}
{barplot_svg(abundance_rows, args.top_taxa)}
{abundance_matrix_html(abundance_rows)}
{sankey_svg(abundance_rows, args.top_taxa)}
{sunburst_svg(abundance_rows, args.top_taxa)}
{taxonomy_tree_html(abundance_rows)}
{table_html("Alpha Diversity", diversity_rows, "alpha-diversity")}
</main>
</body>
</html>
"""
    Path(args.output).write_text(doc)


if __name__ == "__main__":
    main()
