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


def fastq_stats(paths):
    read_lengths = []
    quality_values = []

    for raw_path in paths:
        if not raw_path:
            continue
        path_label = raw_path
        with open_maybe_gzip(raw_path) as handle:
            record_line = 0
            header = sequence = plus = quality = None
            for line_number, line in enumerate(handle, start=1):
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
                    read_lengths.append(len(sequence))
                    quality_values.extend(ord(char) - 33 for char in quality)

            if record_line != 3:
                raise ValueError(f"{path_label}: incomplete FASTQ record at end of file")

    if not read_lengths:
        return {
            "total_reads": 0,
            "mean_read_length": 0,
            "min_read_length": 0,
            "max_read_length": 0,
            "mean_read_quality": 0,
        }

    return {
        "total_reads": len(read_lengths),
        "mean_read_length": round(mean(read_lengths), 2),
        "min_read_length": min(read_lengths),
        "max_read_length": max(read_lengths),
        "mean_read_quality": round(mean(quality_values), 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Create HOMES metagenomics normalized scaffold tables.")
    parser.add_argument("--samplesheet", required=True)
    parser.add_argument("--platform", required=True, choices=["illumina", "nanopore"])
    parser.add_argument("--qc", required=True)
    parser.add_argument("--taxonomy", required=True)
    parser.add_argument("--abundance", required=True)
    parser.add_argument("--relative_abundance", required=True)
    args = parser.parse_args()

    samples = read_samples(args.samplesheet)

    qc_rows = []
    taxonomy_rows = []
    abundance_rows = []
    relative_rows = []

    for index, sample in enumerate(samples, start=1):
        sample_name = sample["sample"]
        read_layout = sample["read_layout"]
        host_filtering = "planned" if sample.get("host_ref") else "not_configured"
        analysis_design = "nanopore_long_read_metagenomics" if args.platform == "nanopore" else "illumina_short_read_metagenomics"
        read_stats = fastq_stats([sample.get("fastq_1"), sample.get("fastq_2")])
        classifier = "kraken2"
        total_reads = read_stats["total_reads"]
        assigned_reads = int(total_reads * 0.8)

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
                "mean_read_quality": read_stats["mean_read_quality"],
            }
        )

        taxonomy_rows.append(
            {
                "sample": sample_name,
                "classifier": classifier,
                "rank": "species",
                "taxid": "562",
                "taxon": "Escherichia coli",
                "assigned_reads": assigned_reads,
                "source_report": "pending_real_classifier_report",
            }
        )

        abundance_rows.append(
            {
                "sample": sample_name,
                "rank": "species",
                "taxid": "562",
                "taxon": "Escherichia coli",
                "reads": assigned_reads,
            }
        )

        relative_rows.append(
            {
                "sample": sample_name,
                "rank": "species",
                "taxid": "562",
                "taxon": "Escherichia coli",
                "relative_abundance": assigned_reads / total_reads,
            }
        )

    write_tsv(args.qc, ["sample", "platform", "read_layout", "analysis_design", "input_1", "input_2", "host_filtering", "total_reads", "analysis_ready_reads", "mean_read_length", "min_read_length", "max_read_length", "mean_read_quality"], qc_rows)
    write_tsv(args.taxonomy, ["sample", "classifier", "rank", "taxid", "taxon", "assigned_reads", "source_report"], taxonomy_rows)
    write_tsv(args.abundance, ["sample", "rank", "taxid", "taxon", "reads"], abundance_rows)
    write_tsv(args.relative_abundance, ["sample", "rank", "taxid", "taxon", "relative_abundance"], relative_rows)


if __name__ == "__main__":
    main()
