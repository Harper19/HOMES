#!/usr/bin/env python3

import argparse
import gzip
from pathlib import Path


def open_text(path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("rt")


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


def read_ids(path):
    ids = set()
    with Path(path).open() as handle:
        for line in handle:
            value = line.strip()
            if value:
                ids.add(value)
    return ids


def read_id_from_fastq_name(name):
    return name[1:].split()[0] if name.startswith("@") else name.split()[0]


def main():
    parser = argparse.ArgumentParser(description="Filter FASTQ reads by read ID for HOMES_amplicon.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--exclude", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    excluded = read_ids(args.exclude)
    with Path(args.output).open("w") as out:
        for name, seq, plus, qual in iter_fastq(args.input):
            if read_id_from_fastq_name(name) not in excluded:
                out.write(f"{name}\n{seq}\n{plus}\n{qual}\n")


if __name__ == "__main__":
    main()
