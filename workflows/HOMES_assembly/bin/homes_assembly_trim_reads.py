#!/usr/bin/env python3

import argparse
import csv
import gzip
import shutil
from pathlib import Path


def as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def open_text(path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return open(path)


def resolve_staged(path):
    candidate = Path(path)
    if candidate.exists():
        return candidate
    staged = Path.cwd() / candidate.name
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
            plus = handle.readline()
            qual = handle.readline().strip()
            if seq:
                yield name.rstrip(), seq, plus.rstrip(), qual


def qtrim(seq, qual, min_quality):
    start = 0
    end = len(seq)
    while start < end and (ord(qual[start]) - 33) < min_quality:
        start += 1
    while end > start and (ord(qual[end - 1]) - 33) < min_quality:
        end -= 1
    return seq[start:end], qual[start:end]


def trim_one(read_path, output_path, adapter, enabled, min_quality, min_length):
    stats = {
        "input_reads": 0,
        "output_reads": 0,
        "input_bases": 0,
        "output_bases": 0,
        "adapter_trimmed_reads": 0,
        "quality_filtered_reads": 0,
        "length_filtered_reads": 0,
    }
    source = resolve_staged(read_path)
    with open(output_path, "w") as out:
        for name, seq, plus, qual in iter_fastq(source):
            stats["input_reads"] += 1
            stats["input_bases"] += len(seq)
            original_len = len(seq)
            if enabled and adapter and adapter in seq:
                cut = seq.find(adapter)
                seq = seq[:cut]
                qual = qual[:cut]
                stats["adapter_trimmed_reads"] += 1
            if enabled:
                seq, qual = qtrim(seq, qual, min_quality)
            if enabled and len(seq) < original_len and len(seq) < min_length:
                stats["quality_filtered_reads"] += 1
            if len(seq) < min_length:
                stats["length_filtered_reads"] += 1
                continue
            stats["output_reads"] += 1
            stats["output_bases"] += len(seq)
            out.write(f"{name}\n{seq}\n+\n{qual}\n")
    return stats


def read_samplesheet(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser(description="Trim/filter reads for HOMES assembly.")
    parser.add_argument("--samplesheet", required=True)
    parser.add_argument("--platform", required=True, choices=["illumina", "nanopore"])
    parser.add_argument("--enabled", required=True)
    parser.add_argument("--adapter_1", default="")
    parser.add_argument("--adapter_2", default="")
    parser.add_argument("--min_quality", type=int, default=10)
    parser.add_argument("--min_length", type=int, default=50)
    parser.add_argument("--output_samplesheet", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    enabled = as_bool(args.enabled)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_samplesheet(args.samplesheet)

    output_rows = []
    summary_rows = []
    for row in rows:
        sample = row["sample"]
        output_row = dict(row)
        reads = [("fastq_1", args.adapter_1 or ""), ("fastq_2", args.adapter_2 or "")]
        for read_column, adapter in reads:
            read_value = row.get(read_column, "").strip()
            if not read_value:
                continue
            suffix = "R1" if read_column == "fastq_1" else "R2"
            output_name = f"{sample}_{suffix}.trimmed.fastq"
            output_path = out_dir / output_name
            stats = trim_one(read_value, output_path, adapter, enabled, args.min_quality, args.min_length)
            output_row[read_column] = f"{out_dir.name}/{output_name}"
            summary_rows.append(
                {
                    "sample": sample,
                    "platform": args.platform,
                    "read": read_column,
                    "trim_enabled": str(enabled).lower(),
                    **stats,
                }
            )
        output_rows.append(output_row)

    fieldnames = ["sample", "fastq_1", "fastq_2", "read_layout", "assembly_group"]
    with open(args.output_samplesheet, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    with open(args.summary, "w", newline="") as handle:
        fieldnames = [
            "sample",
            "platform",
            "read",
            "trim_enabled",
            "input_reads",
            "output_reads",
            "input_bases",
            "output_bases",
            "adapter_trimmed_reads",
            "quality_filtered_reads",
            "length_filtered_reads",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(summary_rows)


if __name__ == "__main__":
    main()
