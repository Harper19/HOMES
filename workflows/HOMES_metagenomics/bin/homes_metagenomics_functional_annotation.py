#!/usr/bin/env python3

import argparse
import csv
import shutil
import subprocess
from pathlib import Path


FIELDS = [
    "gene_id", "description", "cog_category", "go_terms", "ec_numbers",
    "kegg_ko", "kegg_pathways", "cazy", "source",
]


def as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def require_command(command):
    if shutil.which(command) is None:
        raise RuntimeError(f"Required command '{command}' was not found in the selected container.")


def read_fasta(path):
    name, seq = None, []
    with Path(path).open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name:
                    yield name, "".join(seq)
                name, seq = line[1:].split()[0], []
            else:
                seq.append(line)
        if name:
            yield name, "".join(seq)


def write_empty(paths, source):
    for path, header in paths:
        if str(path).endswith((".fna", ".faa")):
            Path(path).write_text("")
            continue
        with Path(path).open("w", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(header)
            if header == FIELDS:
                writer.writerow(["not_run", "", "", "", "", "", "", "", source])


def native_gene_calling(contigs, genes_fna, proteins_faa):
    """Tiny deterministic fallback for offline graph tests; never used for real annotation."""
    rows = []
    with Path(genes_fna).open("w") as nucleotide, Path(proteins_faa).open("w") as protein:
        gene_index = 0
        for contig, sequence in read_fasta(contigs):
            sequence = sequence.upper()
            # Keep the fallback intentionally simple and isolated from scientific runs.
            for start in range(0, max(len(sequence) - 89, 0), 300):
                gene_index += 1
                gene_id = f"{contig}_native_gene_{gene_index:05d}"
                fragment = sequence[start:start + 90]
                nucleotide.write(f">{gene_id}\n{fragment}\n")
                protein.write(f">{gene_id}\nM" + "X" * 29 + "\n")
                rows.append({"gene_id": gene_id, "source": "native_test"})
    return rows


def run_prodigal(contigs, genes_fna, proteins_faa):
    require_command("prodigal")
    subprocess.run(
        ["prodigal", "-i", str(contigs), "-d", str(genes_fna), "-a", str(proteins_faa), "-p", "meta", "-q"],
        check=True,
    )


def parse_emapper(path):
    annotations = {}
    with Path(path).open() as handle:
        header = None
        for line in handle:
            if line.startswith("#"):
                candidate = line.lstrip("#").strip().split("\t")
                if candidate and candidate[0].lower() in {"query", "#query"}:
                    header = candidate
                continue
            if not line.strip() or not header:
                continue
            values = line.rstrip("\n").split("\t")
            row = dict(zip(header, values))
            gene_id = row.get("query", "")
            if not gene_id:
                continue
            annotations[gene_id] = {
                "gene_id": gene_id,
                "description": row.get("Description", ""),
                "cog_category": row.get("COG_category", ""),
                "go_terms": row.get("GOs", ""),
                "ec_numbers": row.get("EC", ""),
                "kegg_ko": row.get("KEGG_ko", ""),
                "kegg_pathways": row.get("KEGG_Pathway", ""),
                "cazy": row.get("CAZy", ""),
                "source": "eggnog_mapper",
            }
    return annotations


def write_annotations(path, rows):
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_term_summary(path, rows, field, label):
    counts = {}
    for row in rows:
        for term in row.get(field, "").replace(",", ";").split(";"):
            term = term.strip()
            if term and term != "-":
                counts[term] = counts.get(term, 0) + 1
    with Path(path).open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow([label, "annotated_genes"])
        for term, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            writer.writerow([term, count])


def main():
    parser = argparse.ArgumentParser(description="Predict metagenomic genes and run eggNOG functional annotation.")
    parser.add_argument("--contigs", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--tool", required=True, choices=["eggnog", "native"])
    parser.add_argument("--eggnog_data_dir", required=True)
    parser.add_argument("--download_eggnog_data", required=True)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--genes_fna", required=True)
    parser.add_argument("--proteins_faa", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--ko_summary", required=True)
    parser.add_argument("--ec_summary", required=True)
    parser.add_argument("--pathway_summary", required=True)
    parser.add_argument("--raw_dir", required=True)
    args = parser.parse_args()

    output_paths = [
        (args.genes_fna, ["gene_id", "sequence"]),
        (args.proteins_faa, ["gene_id", "protein"]),
        (args.annotations, FIELDS),
        (args.ko_summary, ["kegg_ko", "annotated_genes"]),
        (args.ec_summary, ["ec_number", "annotated_genes"]),
        (args.pathway_summary, ["kegg_pathway", "annotated_genes"]),
    ]
    Path(args.raw_dir).mkdir(parents=True, exist_ok=True)
    if not as_bool(args.run):
        write_empty(output_paths, "not_run")
        return

    raw_dir = Path(args.raw_dir)
    if args.tool == "native":
        native_rows = native_gene_calling(args.contigs, args.genes_fna, args.proteins_faa)
        rows = [{**{field: "" for field in FIELDS}, **row} for row in native_rows]
    else:
        run_prodigal(args.contigs, args.genes_fna, args.proteins_faa)
        data_dir = Path(args.eggnog_data_dir)
        if as_bool(args.download_eggnog_data) and not (data_dir / "eggnog.db").exists():
            require_command("download_eggnog_data.py")
            data_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(["download_eggnog_data.py", "-y", "--data_dir", str(data_dir)], check=True)
        if not (data_dir / "eggnog.db").exists():
            raise RuntimeError("eggNOG database is missing. Set --download_functional_db true once or provide --eggnog_data_dir.")
        require_command("emapper.py")
        subprocess.run([
            "emapper.py", "-i", args.proteins_faa, "-m", "diamond", "-o", "functional",
            "--output_dir", str(raw_dir), "--data_dir", str(data_dir), "--cpu", str(args.threads), "--override",
        ], check=True)
        rows = list(parse_emapper(raw_dir / "functional.emapper.annotations").values())

    write_annotations(args.annotations, rows)
    write_term_summary(args.ko_summary, rows, "kegg_ko", "kegg_ko")
    write_term_summary(args.ec_summary, rows, "ec_numbers", "ec_number")
    write_term_summary(args.pathway_summary, rows, "kegg_pathways", "kegg_pathway")


if __name__ == "__main__":
    main()
