#!/usr/bin/env python3

import argparse
import csv
import gzip
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


def as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_table(path):
    with Path(path).open() as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def staged_path(value):
    candidate = Path(value)
    if candidate.exists():
        return candidate
    local = Path(candidate.name)
    if local.exists():
        return local
    raise FileNotFoundError(f"FASTQ declared in samplesheet is not staged: {value}")


def samples(samplesheet):
    with Path(samplesheet).open(newline="") as handle:
        for row in csv.DictReader(handle):
            reads = [staged_path(row["fastq_1"])]
            if row.get("fastq_2", "").strip():
                reads.append(staged_path(row["fastq_2"]))
            yield row["sample"], reads


def read_fastq_sequences(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as handle:
        while True:
            name = handle.readline()
            sequence = handle.readline()
            plus = handle.readline()
            quality = handle.readline()
            if not quality:
                break
            if name.startswith("@") and plus.startswith("+"):
                yield sequence.strip().upper()


def native_counts(genes, reads):
    gene_sequences = {}
    name = None
    seq = []
    with Path(genes).open() as handle:
        for line in handle:
            line = line.strip()
            if line.startswith(">"):
                if name:
                    gene_sequences[name] = "".join(seq).upper()
                name, seq = line[1:].split()[0], []
            else:
                seq.append(line)
        if name:
            gene_sequences[name] = "".join(seq).upper()
    counts = Counter()
    for read_path in reads:
        for read in read_fastq_sequences(read_path):
            for gene_id, sequence in gene_sequences.items():
                if read in sequence or sequence in read:
                    counts[gene_id] += 1
                    break
    return counts


def minimap2_counts(genes, reads, preset):
    if shutil.which("minimap2") is None:
        raise RuntimeError("minimap2 was not found in the selected functional mapping container.")
    command = ["minimap2", "-a", "-x", preset, str(genes)] + [str(path) for path in reads]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    counts = Counter()
    for line in process.stdout:
        if not line or line.startswith("@"):
            continue
        fields = line.rstrip("\n").split("\t")
        if len(fields) < 3:
            continue
        flag = int(fields[1])
        if flag & 4 or flag & 256 or flag & 2048 or fields[2] == "*":
            continue
        counts[fields[2]] += 1
    stderr = process.stderr.read()
    if process.wait() != 0:
        raise RuntimeError(f"minimap2 failed: {stderr}")
    return counts


def write_rows(path, header, rows):
    with Path(path).open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(header)
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Quantify sample reads against metagenomic functional genes.")
    parser.add_argument("--samplesheet", required=True)
    parser.add_argument("--genes", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--mapping_tool", required=True, choices=["minimap2", "native"])
    parser.add_argument("--gene_abundance", required=True)
    parser.add_argument("--ko_abundance", required=True)
    parser.add_argument("--ec_abundance", required=True)
    parser.add_argument("--pathway_abundance", required=True)
    args = parser.parse_args()

    headers = {
        "gene": ["sample", "gene_id", "mapped_reads", "source"],
        "ko": ["sample", "kegg_ko", "mapped_reads", "source"],
        "ec": ["sample", "ec_number", "mapped_reads", "source"],
        "pathway": ["sample", "kegg_pathway", "mapped_reads", "source"],
    }
    if not as_bool(args.run):
        write_rows(args.gene_abundance, headers["gene"], [])
        write_rows(args.ko_abundance, headers["ko"], [])
        write_rows(args.ec_abundance, headers["ec"], [])
        write_rows(args.pathway_abundance, headers["pathway"], [])
        return

    annotations = {row["gene_id"]: row for row in read_table(args.annotations)}
    gene_rows, term_counts = [], {"kegg_ko": defaultdict(Counter), "ec_numbers": defaultdict(Counter), "kegg_pathways": defaultdict(Counter)}
    preset = "map-ont" if args.platform == "nanopore" else "sr"
    source = "minimap2" if args.mapping_tool == "minimap2" else "native_test"
    for sample, reads in samples(args.samplesheet):
        counts = minimap2_counts(args.genes, reads, preset) if args.mapping_tool == "minimap2" else native_counts(args.genes, reads)
        for gene_id, count in sorted(counts.items()):
            gene_rows.append([sample, gene_id, count, source])
            annotation = annotations.get(gene_id, {})
            for field in term_counts:
                for term in annotation.get(field, "").replace(",", ";").split(";"):
                    term = term.strip()
                    if term and term != "-":
                        term_counts[field][sample][term] += count

    write_rows(args.gene_abundance, headers["gene"], gene_rows)
    write_rows(args.ko_abundance, headers["ko"], ([sample, term, count, source] for sample, terms in sorted(term_counts["kegg_ko"].items()) for term, count in sorted(terms.items())))
    write_rows(args.ec_abundance, headers["ec"], ([sample, term, count, source] for sample, terms in sorted(term_counts["ec_numbers"].items()) for term, count in sorted(terms.items())))
    write_rows(args.pathway_abundance, headers["pathway"], ([sample, term, count, source] for sample, terms in sorted(term_counts["kegg_pathways"].items()) for term, count in sorted(terms.items())))


if __name__ == "__main__":
    main()
