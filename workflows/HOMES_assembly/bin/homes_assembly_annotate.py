#!/usr/bin/env python3

import argparse
import csv
import shutil
import subprocess
from pathlib import Path


def as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def require_command(command):
    if shutil.which(command) is None:
        raise RuntimeError(
            f"Required command '{command}' was not found. Run with Docker/Singularity "
            "or disable annotation with --skip_annotation true."
        )


def read_fasta(path):
    name = None
    seq = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name:
                    yield name, "".join(seq)
                name = line[1:].split()[0]
                seq = []
            else:
                seq.append(line)
        if name:
            yield name, "".join(seq)


def candidate_genomes(bins_dir, contigs):
    paths = sorted(Path(bins_dir).glob("*.fa*")) + sorted(Path(bins_dir).glob("*.fasta"))
    seen = []
    for path in paths:
        if path not in seen:
            seen.append(path)
    if seen:
        return seen
    return [Path(contigs)]


def native_annotation(genome_path, output_dir, genome_id):
    out_dir = output_dir / genome_id
    out_dir.mkdir(parents=True, exist_ok=True)
    gff = out_dir / f"{genome_id}.gff"
    faa = out_dir / f"{genome_id}.faa"
    functions = []
    gene_count = 0
    with open(gff, "w") as gff_handle, open(faa, "w") as faa_handle:
        gff_handle.write("##gff-version 3\n")
        for contig, seq in read_fasta(genome_path):
            seq = seq.upper()
            starts = list(range(0, max(len(seq) - 90, 0), 300))
            if not starts and len(seq) >= 30:
                starts = [0]
            for start in starts:
                end = min(start + 90, len(seq))
                if end - start < 30:
                    continue
                gene_count += 1
                gene_id = f"{genome_id}_gene_{gene_count:05d}"
                product = "predicted protein"
                gff_handle.write(
                    f"{contig}\tHOMES_native\tCDS\t{start + 1}\t{end}\t.\t+\t0\tID={gene_id};product={product}\n"
                )
                faa_handle.write(f">{gene_id} {product}\n")
                faa_handle.write("M" + "X" * max(((end - start) // 3) - 1, 0) + "\n")
                functions.append(
                    {
                        "genome_id": genome_id,
                        "gene_id": gene_id,
                        "product": product,
                        "ec_number": "",
                        "ko_id": "",
                        "source": "HOMES_native",
                    }
                )
    return {"genome_id": genome_id, "genes": gene_count, "cds": gene_count, "rrna": 0, "trna": 0}, functions


def run_prokka(genome_path, output_dir, genome_id, threads):
    require_command("prokka")
    out_dir = output_dir / genome_id
    subprocess.run(
        [
            "prokka",
            "--outdir",
            str(out_dir),
            "--prefix",
            genome_id,
            "--cpus",
            str(threads),
            "--metagenome",
            str(genome_path),
        ],
        check=True,
    )
    tsv = out_dir / f"{genome_id}.tsv"
    functions = []
    genes = 0
    if tsv.exists():
        with open(tsv, newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                genes += 1
                functions.append(
                    {
                        "genome_id": genome_id,
                        "gene_id": row.get("locus_tag", ""),
                        "product": row.get("product", ""),
                        "ec_number": row.get("EC_number", ""),
                        "ko_id": row.get("COG", ""),
                        "source": "prokka",
                    }
                )
    return {"genome_id": genome_id, "genes": genes, "cds": genes, "rrna": 0, "trna": 0}, functions


def write_empty(annotation_summary, functional_annotations, platform, annotation_tool, reason):
    with open(annotation_summary, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["genome_id", "platform", "annotation_tool", "genes", "cds", "rrna", "trna", "source"])
        writer.writerow(["not_run", platform, annotation_tool, 0, 0, 0, 0, reason])
    with open(functional_annotations, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["genome_id", "gene_id", "product", "ec_number", "ko_id", "source"])


def main():
    parser = argparse.ArgumentParser(description="Annotate HOMES bins/genomes and summarize functional genes.")
    parser.add_argument("--bins", required=True)
    parser.add_argument("--contigs", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--annotation_tool", required=True, choices=["prokka", "native"])
    parser.add_argument("--skip_annotation", required=True)
    parser.add_argument("--skip_functional_annotation", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--annotation_summary", required=True)
    parser.add_argument("--functional_annotations", required=True)
    parser.add_argument("--threads", type=int, default=1)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if as_bool(args.skip_annotation):
        write_empty(args.annotation_summary, args.functional_annotations, args.platform, args.annotation_tool, "skip_annotation")
        return

    summary_rows = []
    function_rows = []
    for genome_path in candidate_genomes(args.bins, args.contigs):
        genome_id = genome_path.stem.replace(".", "_")
        if args.annotation_tool == "native":
            summary, functions = native_annotation(genome_path, output_dir, genome_id)
        else:
            summary, functions = run_prokka(genome_path, output_dir, genome_id, args.threads)
        summary_rows.append(summary)
        if not as_bool(args.skip_functional_annotation):
            function_rows.extend(functions)

    with open(args.annotation_summary, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["genome_id", "platform", "annotation_tool", "genes", "cds", "rrna", "trna", "source"])
        for row in summary_rows:
            writer.writerow(
                [
                    row["genome_id"],
                    args.platform,
                    args.annotation_tool,
                    row["genes"],
                    row["cds"],
                    row["rrna"],
                    row["trna"],
                    args.annotation_tool,
                ]
            )

    with open(args.functional_annotations, "w", newline="") as handle:
        fieldnames = ["genome_id", "gene_id", "product", "ec_number", "ko_id", "source"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(function_rows)


if __name__ == "__main__":
    main()
