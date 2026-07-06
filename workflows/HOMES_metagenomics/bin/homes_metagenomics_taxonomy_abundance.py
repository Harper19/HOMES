#!/usr/bin/env python3

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


TAXONOMY_FIELDS = ["sample", "classifier", "rank", "taxid", "taxon", "assigned_reads", "source_report"]
ABUNDANCE_FIELDS = ["sample", "rank", "taxid", "taxon", "reads"]
RELATIVE_FIELDS = ["sample", "rank", "taxid", "taxon", "relative_abundance"]
RANK_CODES = {
    "domain": "D",
    "kingdom": "K",
    "phylum": "P",
    "class": "C",
    "order": "O",
    "family": "F",
    "genus": "G",
    "species": "S",
}
RANK_NAMES = {value: key for key, value in RANK_CODES.items()}


def clean(value):
    return str(value or "").strip()


def truthy(value):
    return clean(value).lower() not in {"", "0", "false", "f", "no", "n", "none", "null"}


def read_csv(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_database_info(path):
    with Path(path).open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return rows[0] if rows else {}


def write_tsv(path, fieldnames, rows):
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def local_path(value):
    value = clean(value)
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        destination = Path(Path(urlparse(value).path).name)
        if not destination.exists():
            with urlopen(value) as response, destination.open("wb") as handle:
                shutil.copyfileobj(response, handle)
        return str(destination)
    path = Path(value)
    if path.exists():
        return str(path)
    staged = Path(path.name)
    if staged.exists():
        return str(staged)
    return value


def rank_code(value):
    value = clean(value)
    if not value:
        return "S"
    upper = value.upper()
    if upper in RANK_NAMES:
        return upper
    return RANK_CODES.get(value.lower(), upper)


def find_kraken_database(path):
    root = Path(path)
    if not root.exists():
        return None
    required = {"hash.k2d", "opts.k2d", "taxo.k2d"}
    candidates = [root] + [item for item in root.rglob("*") if item.is_dir()]
    for candidate in candidates:
        names = {item.name for item in candidate.iterdir() if item.is_file()}
        if required.issubset(names):
            return candidate
    return None


def require_command(name):
    if not shutil.which(name):
        raise RuntimeError(
            f"Required command '{name}' was not found. Install it locally, run with Docker/Singularity, "
            f"or disable this step with --skip_taxonomy true."
        )


def run_command(command):
    printable = " ".join(str(part) for part in command)
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.stdout:
        sys.stderr.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {printable}")


def kraken_rows(sample, report_path, desired_rank):
    rows = []
    rank = rank_code(desired_rank)
    rank_name = RANK_NAMES.get(rank, rank)
    with Path(report_path).open() as handle:
        for line in handle:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 6:
                continue
            try:
                percent = float(cols[0].strip())
                clade_reads = int(float(cols[1].strip()))
            except ValueError:
                continue
            kraken_rank = cols[3].strip()
            if kraken_rank != rank:
                continue
            taxid = cols[4].strip()
            taxon = cols[5].strip()
            rows.append(
                {
                    "sample": sample,
                    "rank": rank_name,
                    "taxid": taxid,
                    "taxon": taxon,
                    "reads": clade_reads,
                    "relative_abundance": round(percent / 100, 8),
                }
            )
    return sorted(rows, key=lambda row: row["relative_abundance"], reverse=True)


def bracken_rows(sample, bracken_path):
    rows = []
    with Path(bracken_path).open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            try:
                reads = int(float(row.get("new_est_reads", 0)))
                relative_abundance = float(row.get("fraction_total_reads", 0))
            except ValueError:
                continue
            rows.append(
                {
                    "sample": sample,
                    "rank": RANK_NAMES.get(clean(row.get("taxonomy_lvl")), clean(row.get("taxonomy_lvl"))),
                    "taxid": clean(row.get("taxonomy_id")),
                    "taxon": clean(row.get("name")),
                    "reads": reads,
                    "relative_abundance": round(relative_abundance, 8),
                }
            )
    return sorted(rows, key=lambda row: row["relative_abundance"], reverse=True)


def main():
    parser = argparse.ArgumentParser(description="Run Kraken2/Bracken and normalize HOMES metagenomics taxonomy tables.")
    parser.add_argument("--samplesheet", required=True)
    parser.add_argument("--database_info", required=True)
    parser.add_argument("--platform", required=True, choices=["illumina", "nanopore"])
    parser.add_argument("--taxonomic_rank", default="S")
    parser.add_argument("--bracken", default="false")
    parser.add_argument("--bracken_read_length", default="150")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--skip_taxonomy", default="false")
    parser.add_argument("--taxonomy", required=True)
    parser.add_argument("--abundance", required=True)
    parser.add_argument("--relative_abundance", required=True)
    args = parser.parse_args()

    if truthy(args.skip_taxonomy):
        write_tsv(args.taxonomy, TAXONOMY_FIELDS, [])
        write_tsv(args.abundance, ABUNDANCE_FIELDS, [])
        write_tsv(args.relative_abundance, RELATIVE_FIELDS, [])
        return 0

    database_info = read_database_info(args.database_info)
    status = clean(database_info.get("status"))
    database_path = clean(database_info.get("database_path"))
    if status in {"download_disabled", "not_configured"} and not Path(database_path).exists():
        raise RuntimeError(
            "No ready Kraken2 database is available. Re-run with --download_databases true, "
            "provide --kraken2_db, or use --skip_taxonomy true for QC/report-only testing."
        )

    kraken_database = find_kraken_database(database_path)
    if not kraken_database:
        raise RuntimeError(f"Could not find a Kraken2 database containing hash.k2d/opts.k2d/taxo.k2d under: {database_path}")

    require_command("kraken2")
    run_bracken = truthy(args.bracken)
    bracken_database = None
    if run_bracken:
        require_command("bracken")
        bracken_path = clean(database_info.get("bracken_path")) or database_path
        bracken_database = find_kraken_database(bracken_path)
        if not bracken_database:
            raise RuntimeError(
                f"Could not find a Bracken-compatible database containing Kraken2 files under: {bracken_path}"
            )

    taxonomy_rows = []
    abundance_rows = []
    relative_rows = []

    for sample in read_csv(args.samplesheet):
        sample_name = sample["sample"]
        fastq_1 = local_path(sample.get("fastq_1"))
        fastq_2 = local_path(sample.get("fastq_2"))
        layout = clean(sample.get("read_layout")).lower()
        report_path = Path(f"{sample_name}.kraken2.report")
        output_path = Path(f"{sample_name}.kraken2.output")

        command = [
            "kraken2",
            "--db",
            str(kraken_database),
            "--threads",
            str(max(args.threads, 1)),
            "--report",
            str(report_path),
            "--output",
            str(output_path),
        ]
        if layout == "paired" and fastq_2:
            command.extend(["--paired", fastq_1, fastq_2])
        else:
            command.append(fastq_1)
        run_command(command)

        source = str(report_path)
        normalized = kraken_rows(sample_name, report_path, args.taxonomic_rank)
        if run_bracken:
            bracken_path = Path(f"{sample_name}.bracken.tsv")
            bracken_report = Path(f"{sample_name}.bracken.report")
            run_command(
                [
                    "bracken",
                    "-d",
                    str(bracken_database),
                    "-i",
                    str(report_path),
                    "-o",
                    str(bracken_path),
                    "-w",
                    str(bracken_report),
                    "-r",
                    str(args.bracken_read_length),
                    "-l",
                    rank_code(args.taxonomic_rank),
                    "-t",
                    str(max(args.threads, 1)),
                ]
            )
            normalized = bracken_rows(sample_name, bracken_path)
            source = str(bracken_path)

        for row in normalized:
            taxonomy_rows.append(
                {
                    "sample": row["sample"],
                    "classifier": "bracken" if run_bracken else "kraken2",
                    "rank": row["rank"],
                    "taxid": row["taxid"],
                    "taxon": row["taxon"],
                    "assigned_reads": row["reads"],
                    "source_report": source,
                }
            )
            abundance_rows.append(
                {
                    "sample": row["sample"],
                    "rank": row["rank"],
                    "taxid": row["taxid"],
                    "taxon": row["taxon"],
                    "reads": row["reads"],
                }
            )
            relative_rows.append(
                {
                    "sample": row["sample"],
                    "rank": row["rank"],
                    "taxid": row["taxid"],
                    "taxon": row["taxon"],
                    "relative_abundance": row["relative_abundance"],
                }
            )

    write_tsv(args.taxonomy, TAXONOMY_FIELDS, taxonomy_rows)
    write_tsv(args.abundance, ABUNDANCE_FIELDS, abundance_rows)
    write_tsv(args.relative_abundance, RELATIVE_FIELDS, relative_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
