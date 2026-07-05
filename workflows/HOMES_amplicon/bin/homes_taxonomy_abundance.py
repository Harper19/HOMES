#!/usr/bin/env python3

import argparse
import csv
import math
from collections import Counter
from pathlib import Path


RANKS = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]
PREFIX_TO_RANK = {
    "d": "kingdom",
    "k": "kingdom",
    "p": "phylum",
    "c": "class",
    "o": "order",
    "f": "family",
    "g": "genus",
    "s": "species",
}
KRAKEN_RANK_TO_LEVEL = {
    "D": "kingdom",
    "K": "kingdom",
    "P": "phylum",
    "C": "class",
    "O": "order",
    "F": "family",
    "G": "genus",
    "S": "species",
}


def clean_taxon(value):
    value = (value or "").strip()
    if not value:
        return "Unclassified"
    if "__" in value and len(value.split("__", 1)[0]) <= 2:
        value = value.split("__", 1)[1]
    return value.strip() or "Unclassified"


def readable_taxon(value):
    return clean_taxon(value).replace("_", " ")


def genus_from_species(species):
    species = readable_taxon(species)
    if species == "Unclassified":
        return species
    return species.split()[0] if species.split() else species


def taxonomy_from_reference(reference):
    reference = (reference or "").strip()
    if not reference or reference == "*":
        return {}
    taxonomy_text = reference.split(maxsplit=1)[1] if " " in reference else reference
    taxonomy_text = taxonomy_text.replace("|", ";")
    parts = [part.strip() for part in taxonomy_text.split(";") if part.strip()]
    taxonomy = {}
    positional = []
    saw_key_value = False
    for part in parts:
        if "=" in part:
            saw_key_value = True
            key, value = part.split("=", 1)
            key = key.strip().lower()
            if key in RANKS:
                taxonomy[key] = readable_taxon(value)
            continue
        if "__" in part:
            prefix, value = part.split("__", 1)
            rank = PREFIX_TO_RANK.get(prefix[-1:].lower())
            if rank:
                taxonomy[rank] = clean_taxon(value)
                continue
        positional.append(part)
    if not saw_key_value:
        for rank, value in zip(RANKS, positional):
            taxonomy.setdefault(rank, clean_taxon(value))
    if taxonomy.get("species") and not taxonomy.get("genus"):
        taxonomy["genus"] = genus_from_species(taxonomy["species"])
    taxonomy["reference"] = reference
    return taxonomy


def summarize_counts(sample, counts, tax_level, threshold, out_prefix):
    total = sum(counts.values())
    count_path = Path(f"{out_prefix}.counts.{tax_level}.tsv")
    rel_path = Path(f"{out_prefix}.relative_abundance.{tax_level}.tsv")
    div_path = Path(f"{out_prefix}.diversity.{tax_level}.tsv")

    rows = []
    for taxon, reads in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        relative = reads / total if total else 0.0
        if relative >= threshold:
            rows.append((taxon, reads, relative))

    with count_path.open("w") as handle:
        handle.write("sample\ttax_level\ttaxon\treads\n")
        for taxon, reads, _relative in rows:
            handle.write(f"{sample}\t{tax_level}\t{taxon}\t{reads}\n")

    with rel_path.open("w") as handle:
        handle.write("sample\ttax_level\ttaxon\treads\trelative_abundance\n")
        for taxon, reads, relative in rows:
            handle.write(f"{sample}\t{tax_level}\t{taxon}\t{reads}\t{relative:.8f}\n")

    proportions = [reads / total for reads in counts.values()] if total else []
    shannon = -sum(p * math.log(p) for p in proportions if p > 0)
    simpson = 1 - sum(p * p for p in proportions)
    with div_path.open("w") as handle:
        handle.write("sample\ttax_level\ttotal_classified_reads\trichness\tshannon\tsimpson\n")
        handle.write(f"{sample}\t{tax_level}\t{total}\t{len(counts)}\t{shannon:.8f}\t{simpson:.8f}\n")


def abundance_from_minimap2(path, tax_level):
    sample = Path(path).stem.replace(".classification", "")
    counts = Counter()
    with Path(path).open() as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if row.get("sample"):
                sample = row["sample"]
            if row.get("passed", "true").lower() != "true":
                continue
            taxonomy = taxonomy_from_reference(row.get("reference", ""))
            if tax_level == "reference":
                taxon = taxonomy.get("reference") or "Unclassified"
            else:
                taxon = taxonomy.get(tax_level) or "Unclassified"
            counts[clean_taxon(taxon)] += 1
    return sample, counts


def abundance_from_kraken2_report(path, tax_level):
    sample = Path(path).name.replace(".kraken2.report.txt", "").replace(".report.txt", "")
    counts = Counter()
    wanted_rank = {level: rank for rank, level in KRAKEN_RANK_TO_LEVEL.items()}.get(tax_level)
    with Path(path).open() as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 6:
                fields = line.split(maxsplit=5)
            if len(fields) < 6:
                continue
            _pct, clade_reads, _taxon_reads, rank, _taxid, name = fields[:6]
            rank = rank.strip()
            if rank == wanted_rank:
                counts[clean_taxon(name)] += int(clade_reads)
    return sample, counts


def abundance_from_bracken(path, tax_level):
    sample = Path(path).name.replace(".bracken.tsv", "")
    counts = Counter()
    with Path(path).open() as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            name = row.get("name") or row.get("taxonomy_id") or row.get("taxon")
            reads = row.get("new_est_reads") or row.get("fraction_total_reads") or row.get("kraken_assigned_reads")
            if not name or not reads:
                continue
            try:
                counts[clean_taxon(name)] += int(round(float(reads)))
            except ValueError:
                continue
    return sample, counts


def write_empty(tax_level, out_prefix):
    summarize_counts("no_taxonomy", Counter(), tax_level, 0.0, out_prefix)


def main():
    parser = argparse.ArgumentParser(description="Create counts, relative abundance, and diversity tables for HOMES_amplicon.")
    parser.add_argument("--mode", choices=["none", "minimap2", "kraken2", "bracken"], required=True)
    parser.add_argument("--input")
    parser.add_argument("--tax_level", default="genus")
    parser.add_argument("--abundance_threshold", type=float, default=0.0)
    parser.add_argument("--out_prefix", required=True)
    args = parser.parse_args()

    tax_level = args.tax_level.lower()
    if tax_level not in RANKS + ["reference", "all"]:
        raise SystemExit(f"Unsupported tax_level: {args.tax_level}")

    if tax_level == "all":
        if args.mode == "minimap2":
            tax_levels = RANKS + ["reference"]
        elif args.mode == "kraken2":
            tax_levels = RANKS
        elif args.mode == "bracken":
            tax_levels = ["genus"]
        else:
            tax_levels = RANKS
    else:
        tax_levels = [tax_level]

    if args.mode == "none":
        for level in tax_levels:
            write_empty(level, args.out_prefix)
        return

    if not args.input:
        raise SystemExit("--input is required unless --mode none")

    for level in tax_levels:
        if args.mode == "minimap2":
            sample, counts = abundance_from_minimap2(args.input, level)
        elif args.mode == "kraken2":
            sample, counts = abundance_from_kraken2_report(args.input, level)
        else:
            sample, counts = abundance_from_bracken(args.input, level)
        summarize_counts(sample, counts, level, args.abundance_threshold, args.out_prefix)


if __name__ == "__main__":
    main()
