#!/usr/bin/env python3

import argparse
import csv
import sys
from pathlib import Path


REQUIRED_COLUMNS = ["sample", "fastq_1", "fastq_2", "read_layout"]
OUTPUT_COLUMNS = ["sample", "fastq_1", "fastq_2", "read_layout", "assembly_group"]
VALID_LAYOUTS = {"illumina": {"paired", "single"}, "nanopore": {"single"}}


def clean(value):
    return str(value or "").strip()


def fail(errors):
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    sys.exit(1)


def resolve_path(value, base_dir):
    value = clean(value)
    if not value or "://" in value:
        return value
    path = Path(value)
    return str(path if path.is_absolute() else (base_dir / path).resolve())


def validate_rows(rows, platform):
    errors = []
    seen = set()

    if not rows:
        return ["samplesheet contains no samples"]

    for line_number, row in enumerate(rows, start=2):
        sample = clean(row.get("sample"))
        fastq_1 = clean(row.get("fastq_1"))
        fastq_2 = clean(row.get("fastq_2"))
        read_layout = clean(row.get("read_layout")).lower()
        label = sample or f"line {line_number}"

        if not sample:
            errors.append(f"line {line_number}: missing sample")
        elif sample in seen:
            errors.append(f"{label}: duplicate sample")
        else:
            seen.add(sample)

        if not fastq_1:
            errors.append(f"{label}: missing fastq_1")

        if read_layout not in VALID_LAYOUTS[platform]:
            allowed = ", ".join(sorted(VALID_LAYOUTS[platform]))
            errors.append(f"{label}: read_layout must be one of {allowed} for platform {platform}")

        if platform == "illumina" and read_layout == "paired" and not fastq_2:
            errors.append(f"{label}: paired Illumina samples require fastq_2")

        if platform == "nanopore" and fastq_2:
            errors.append(f"{label}: Nanopore samples must leave fastq_2 blank")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate a HOMES assembly samplesheet.")
    parser.add_argument("--input", required=True, help="Input samplesheet CSV.")
    parser.add_argument("--platform", required=True, choices=["illumina", "nanopore"])
    parser.add_argument("--base_dir", required=True, help="Directory used to resolve relative read paths.")
    parser.add_argument("--output", required=True, help="Validated samplesheet CSV.")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    with open(args.input, newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            fail([f"samplesheet is missing required columns: {', '.join(missing)}"])
        rows = list(reader)

    errors = validate_rows(rows, args.platform)
    if errors:
        fail(errors)

    with open(args.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "sample": clean(row.get("sample")),
                    "fastq_1": resolve_path(row.get("fastq_1"), base_dir),
                    "fastq_2": resolve_path(row.get("fastq_2"), base_dir),
                    "read_layout": clean(row.get("read_layout")).lower(),
                    "assembly_group": clean(row.get("assembly_group")) or "default",
                }
            )

    print(f"Validated {len(rows)} {args.platform} assembly sample(s).", file=sys.stderr)


if __name__ == "__main__":
    main()
