#!/usr/bin/env python3

import argparse
import csv
import gzip
from collections import Counter, defaultdict
from pathlib import Path


def open_text(path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return open(path)


def resolve_staged(path):
    candidate = Path(path)
    if candidate.exists():
        return candidate
    basename = Path(path).name
    staged = Path.cwd() / basename
    if staged.exists():
        return staged
    raise FileNotFoundError(f"Cannot find read file: {path}")


def iter_fastq(path):
    with open_text(path) as handle:
        while True:
            name = handle.readline()
            if not name:
                break
            seq = handle.readline().strip()
            handle.readline()
            qual = handle.readline().strip()
            if seq:
                yield seq, qual


def n50(lengths):
    if not lengths:
        return 0
    half = sum(lengths) / 2
    running = 0
    for length in sorted(lengths, reverse=True):
        running += length
        if running >= half:
            return length
    return 0


def q_bin(mean_q):
    return int(mean_q // 2 * 2)


def length_bin(length):
    width = 500
    start = (length // width) * width
    return start, start + width - 1


def summarize_sample(row):
    files = [row["fastq_1"]]
    if row.get("fastq_2"):
        files.append(row["fastq_2"])

    lengths = []
    qualities = []
    length_counts = Counter()
    q_counts = Counter()

    for read_path in files:
        for seq, qual in iter_fastq(resolve_staged(read_path)):
            length = len(seq)
            mean_q = sum(ord(char) - 33 for char in qual) / len(qual) if qual else 0
            lengths.append(length)
            qualities.append(mean_q)
            length_counts[length_bin(length)] += 1
            q_counts[q_bin(mean_q)] += 1

    total_reads = len(lengths)
    total_bases = sum(lengths)
    return {
        "sample": row["sample"],
        "read_layout": row["read_layout"],
        "total_reads": total_reads,
        "total_bases": total_bases,
        "mean_read_length": round(total_bases / total_reads, 2) if total_reads else 0,
        "min_read_length": min(lengths) if lengths else 0,
        "max_read_length": max(lengths) if lengths else 0,
        "n50_read_length": n50(lengths),
        "mean_read_quality": round(sum(qualities) / len(qualities), 2) if qualities else 0,
        "length_counts": length_counts,
        "q_counts": q_counts,
    }


def read_samplesheet(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser(description="Generate HOMES assembly read QC tables.")
    parser.add_argument("--samplesheet", required=True)
    parser.add_argument("--platform", required=True, choices=["illumina", "nanopore"])
    parser.add_argument("--qc", required=True)
    parser.add_argument("--length_distribution", required=True)
    parser.add_argument("--qvalue_distribution", required=True)
    args = parser.parse_args()

    summaries = [summarize_sample(row) for row in read_samplesheet(args.samplesheet)]

    with open(args.qc, "w", newline="") as handle:
        fieldnames = [
            "sample",
            "platform",
            "read_layout",
            "total_reads",
            "total_bases",
            "mean_read_length",
            "min_read_length",
            "max_read_length",
            "n50_read_length",
            "mean_read_quality",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for summary in summaries:
            writer.writerow({key: summary.get(key) for key in fieldnames} | {"platform": args.platform})

    with open(args.length_distribution, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["sample", "length_bin_start", "length_bin_end", "read_count", "fraction"])
        for summary in summaries:
            total = summary["total_reads"] or 1
            for (start, end), count in sorted(summary["length_counts"].items()):
                writer.writerow([summary["sample"], start, end, count, round(count / total, 6)])

    with open(args.qvalue_distribution, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["sample", "q_bin", "read_count", "fraction"])
        for summary in summaries:
            total = summary["total_reads"] or 1
            for qvalue, count in sorted(summary["q_counts"].items()):
                writer.writerow([summary["sample"], qvalue, count, round(count / total, 6)])


if __name__ == "__main__":
    main()
