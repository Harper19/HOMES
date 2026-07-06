#!/usr/bin/env python3

import argparse
import csv
import gzip
from pathlib import Path
from statistics import mean
from urllib.parse import urlparse
from urllib.request import urlopen


def read_samples(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_tsv(path, fieldnames, rows):
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def basename_no_fastq(path):
    if is_url(path):
        name = Path(urlparse(path).path).name
    else:
        name = Path(path).name
    for suffix in [".fastq.gz", ".fq.gz", ".fastq", ".fq"]:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return Path(path).stem


def is_url(value):
    return str(value).startswith(("http://", "https://"))


def open_maybe_gzip(path):
    if is_url(path):
        staged = Path(Path(urlparse(path).path).name)
        if staged.exists():
            return gzip.open(staged, "rt") if staged.suffix == ".gz" else staged.open()
        response = urlopen(path)
        if str(path).endswith(".gz"):
            return gzip.open(response, "rt")
        return response

    path = Path(path)
    if not path.exists() and Path(path.name).exists():
        path = Path(path.name)
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open()


def n50(lengths):
    if not lengths:
        return 0
    half_total = sum(lengths) / 2
    running = 0
    for length in sorted(lengths, reverse=True):
        running += length
        if running >= half_total:
            return length
    return 0


def length_bin_size(max_length):
    if max_length <= 500:
        return 25
    if max_length <= 2000:
        return 100
    if max_length <= 10000:
        return 500
    return 1000


def binned_lengths(lengths):
    if not lengths:
        return []
    bin_size = length_bin_size(max(lengths))
    counts = {}
    for length in lengths:
        start = (length // bin_size) * bin_size
        counts[start] = counts.get(start, 0) + 1
    total = len(lengths)
    return [
        {
            "length_bin_start": start,
            "length_bin_end": start + bin_size - 1,
            "read_count": count,
            "fraction": round(count / total, 6),
        }
        for start, count in sorted(counts.items())
    ]


def binned_qvalues(read_mean_qualities):
    if not read_mean_qualities:
        return []
    counts = {}
    for qvalue in read_mean_qualities:
        q_bin = int(qvalue)
        counts[q_bin] = counts.get(q_bin, 0) + 1
    total = len(read_mean_qualities)
    return [
        {
            "q_bin": q_bin,
            "read_count": count,
            "fraction": round(count / total, 6),
        }
        for q_bin, count in sorted(counts.items())
    ]


def fastq_stats(paths):
    read_lengths = []
    read_mean_qualities = []
    quality_sum = 0
    quality_count = 0

    for raw_path in paths:
        if not raw_path:
            continue
        path_label = raw_path
        with open_maybe_gzip(raw_path) as handle:
            record_line = 0
            header = sequence = plus = quality = None
            for line_number, line in enumerate(handle, start=1):
                if isinstance(line, bytes):
                    line = line.decode()
                value = line.rstrip("\n")
                record_line = (line_number - 1) % 4
                if record_line == 0:
                    header = value
                elif record_line == 1:
                    sequence = value
                elif record_line == 2:
                    plus = value
                else:
                    quality = value
                    if not header or not header.startswith("@"):
                        raise ValueError(f"{path_label}: invalid FASTQ header near line {line_number - 3}")
                    if plus != "+":
                        raise ValueError(f"{path_label}: invalid FASTQ separator near line {line_number - 1}")
                    if len(sequence) != len(quality):
                        raise ValueError(
                            f"{path_label}: sequence and quality lengths differ near line {line_number}"
                        )
                    q_values = [ord(char) - 33 for char in quality]
                    read_lengths.append(len(sequence))
                    read_mean_qualities.append(mean(q_values) if q_values else 0)
                    quality_sum += sum(q_values)
                    quality_count += len(q_values)

            if record_line != 3:
                raise ValueError(f"{path_label}: incomplete FASTQ record at end of file")

    if not read_lengths:
        return {
            "total_reads": 0,
            "mean_read_length": 0,
            "min_read_length": 0,
            "max_read_length": 0,
            "n50_read_length": 0,
            "mean_read_quality": 0,
            "length_distribution": [],
            "qvalue_distribution": [],
        }

    return {
        "total_reads": len(read_lengths),
        "mean_read_length": round(mean(read_lengths), 2),
        "min_read_length": min(read_lengths),
        "max_read_length": max(read_lengths),
        "n50_read_length": n50(read_lengths),
        "mean_read_quality": round(quality_sum / quality_count, 2) if quality_count else 0,
        "length_distribution": binned_lengths(read_lengths),
        "qvalue_distribution": binned_qvalues(read_mean_qualities),
    }


def main():
    parser = argparse.ArgumentParser(description="Create HOMES metagenomics read QC tables.")
    parser.add_argument("--samplesheet", required=True)
    parser.add_argument("--platform", required=True, choices=["illumina", "nanopore"])
    parser.add_argument("--qc", required=True)
    parser.add_argument("--length_distribution", required=True)
    parser.add_argument("--qvalue_distribution", required=True)
    args = parser.parse_args()

    samples = read_samples(args.samplesheet)

    qc_rows = []
    length_distribution_rows = []
    qvalue_distribution_rows = []

    for sample in samples:
        sample_name = sample["sample"]
        read_layout = sample["read_layout"]
        host_filtering = "planned" if sample.get("host_ref") else "not_configured"
        analysis_design = (
            "nanopore_long_read_metagenomics"
            if args.platform == "nanopore"
            else "illumina_short_read_metagenomics"
        )
        read_stats = fastq_stats([sample.get("fastq_1"), sample.get("fastq_2")])
        total_reads = read_stats["total_reads"]

        qc_rows.append(
            {
                "sample": sample_name,
                "platform": args.platform,
                "read_layout": read_layout,
                "analysis_design": analysis_design,
                "input_1": basename_no_fastq(sample["fastq_1"]),
                "input_2": basename_no_fastq(sample["fastq_2"]) if sample.get("fastq_2") else "",
                "host_filtering": host_filtering,
                "total_reads": total_reads,
                "analysis_ready_reads": total_reads,
                "mean_read_length": read_stats["mean_read_length"],
                "min_read_length": read_stats["min_read_length"],
                "max_read_length": read_stats["max_read_length"],
                "n50_read_length": read_stats["n50_read_length"],
                "mean_read_quality": read_stats["mean_read_quality"],
            }
        )

        for row in read_stats["length_distribution"]:
            length_distribution_rows.append({"sample": sample_name, **row})

        for row in read_stats["qvalue_distribution"]:
            qvalue_distribution_rows.append({"sample": sample_name, **row})

    write_tsv(
        args.qc,
        [
            "sample",
            "platform",
            "read_layout",
            "analysis_design",
            "input_1",
            "input_2",
            "host_filtering",
            "total_reads",
            "analysis_ready_reads",
            "mean_read_length",
            "min_read_length",
            "max_read_length",
            "n50_read_length",
            "mean_read_quality",
        ],
        qc_rows,
    )
    write_tsv(
        args.length_distribution,
        ["sample", "length_bin_start", "length_bin_end", "read_count", "fraction"],
        length_distribution_rows,
    )
    write_tsv(
        args.qvalue_distribution,
        ["sample", "q_bin", "read_count", "fraction"],
        qvalue_distribution_rows,
    )


if __name__ == "__main__":
    main()
