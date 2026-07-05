#!/usr/bin/env python3

import argparse
import csv
import gzip
from pathlib import Path


def open_text(path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("rt")


def mean_quality(qual):
    if not qual:
        return 0.0
    return sum(ord(ch) - 33 for ch in qual) / len(qual)


def iter_fastq(path):
    with open_text(path) as handle:
        while True:
            name = handle.readline().rstrip()
            if not name:
                break
            seq = handle.readline().rstrip()
            plus = handle.readline().rstrip()
            qual = handle.readline().rstrip()
            if not qual:
                raise ValueError(f"Incomplete FASTQ record in {path}")
            yield name, seq, plus, qual


def load_sample_aliases(path):
    if not path:
        return {}
    aliases = {}
    sample_sheet = Path(path)
    with sample_sheet.open() as handle:
        dialect = csv.Sniffer().sniff(handle.read(4096), delimiters=",\t")
        handle.seek(0)
        reader = csv.DictReader(handle, dialect=dialect)
        for row in reader:
            clean = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if k is not None and v is not None}
            sample = clean.get("sample") or clean.get("sample_id") or clean.get("alias")
            for key in ("barcode", "barcode_id", "filename", "file", "fastq", "bam"):
                if clean.get(key) and sample:
                    aliases[Path(clean[key]).stem] = sample
                    aliases[clean[key]] = sample
    return aliases


def resolve_sample_name(input_path, default_sample, aliases):
    path = Path(input_path)
    candidates = [
        path.name,
        path.stem,
        path.with_suffix("").name,
        path.parent.name,
        default_sample,
    ]
    for candidate in candidates:
        if candidate in aliases:
            return aliases[candidate]
    return default_sample


def main():
    parser = argparse.ArgumentParser(description="Nanopore amplicon FASTQ QC and filtering for HOMES_amplicon.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--sample_sheet", default=None)
    parser.add_argument("--min_len", type=int, default=1000)
    parser.add_argument("--max_len", type=int, default=0)
    parser.add_argument("--min_read_qual", type=float, default=8.0)
    parser.add_argument("--out_prefix", required=True)
    args = parser.parse_args()

    aliases = load_sample_aliases(args.sample_sheet)
    sample_name = resolve_sample_name(args.input, args.sample, aliases)

    max_len = args.max_len if args.max_len and args.max_len > 0 else None
    stats_path = Path(f"{args.out_prefix}.read_stats.tsv")
    summary_path = Path(f"{args.out_prefix}.summary.tsv")
    filtered_path = Path(f"{args.out_prefix}.filtered.fastq")

    total = 0
    kept = 0
    total_bases = 0
    kept_bases = 0
    qualities = []

    with stats_path.open("w") as stats, filtered_path.open("w") as filtered:
        stats.write("sample\tread_id\tlength\tmean_q\tkept\n")
        for name, seq, plus, qual in iter_fastq(args.input):
            total += 1
            read_id = name[1:].split()[0] if name.startswith("@") else name.split()[0]
            length = len(seq)
            q = mean_quality(qual)
            total_bases += length
            qualities.append(q)
            passes = length >= args.min_len and q >= args.min_read_qual and (max_len is None or length <= max_len)
            if passes:
                kept += 1
                kept_bases += length
                filtered.write(f"{name}\n{seq}\n{plus}\n{qual}\n")
            stats.write(f"{sample_name}\t{read_id}\t{length}\t{q:.2f}\t{str(passes).lower()}\n")

    mean_q = sum(qualities) / len(qualities) if qualities else 0.0
    with summary_path.open("w") as summary:
        summary.write("sample\ttotal_reads\tkept_reads\ttotal_bases\tkept_bases\tmean_read_q\tmin_len\tmax_len\tmin_read_qual\n")
        summary.write(
            f"{sample_name}\t{total}\t{kept}\t{total_bases}\t{kept_bases}\t{mean_q:.2f}\t"
            f"{args.min_len}\t{max_len if max_len is not None else ''}\t{args.min_read_qual}\n"
        )


if __name__ == "__main__":
    main()
