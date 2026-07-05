#!/usr/bin/env python3

import argparse
import re
from pathlib import Path


CIGAR_RE = re.compile(r"(\d+)([MIDNSHP=X])")


def parse_set(value):
    if not value:
        return set()
    return {item.strip() for item in value.replace(";", ",").split(",") if item.strip()}


def parse_taxid(reference):
    for pattern in (r"taxid[=|:]([0-9]+)", r"\|taxid\|([0-9]+)", r"kraken:taxid\|([0-9]+)"):
        match = re.search(pattern, reference)
        if match:
            return match.group(1)
    return ""


def cigar_lengths(cigar):
    query_aligned = 0
    query_total = 0
    aligned_bases = 0
    for count_text, op in CIGAR_RE.findall(cigar or ""):
        count = int(count_text)
        if op in "MIS=X":
            query_total += count
        if op in "MI=X":
            query_aligned += count
        if op in "M=X":
            aligned_bases += count
    return query_aligned, query_total, aligned_bases


def nm_tag(fields):
    for field in fields[11:]:
        if field.startswith("NM:i:"):
            return int(field.split(":")[-1])
    return 0


def main():
    parser = argparse.ArgumentParser(description="Parse minimap2 SAM into HOMES_amplicon read assignments.")
    parser.add_argument("--sam", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--min_mapq", type=float, default=0)
    parser.add_argument("--min_identity", type=float, default=0)
    parser.add_argument("--min_coverage", type=float, default=0)
    parser.add_argument("--filter_taxids", default="")
    parser.add_argument("--exclude_taxids", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    include_taxids = parse_set(args.filter_taxids)
    exclude_taxids = parse_set(args.exclude_taxids)

    with Path(args.output).open("w") as out, Path(args.sam).open() as sam:
        out.write("sample\tread_id\treference\ttaxid\tmapq\taligned_bases\tidentity\tquery_coverage\tpassed\n")
        for line in sam:
            if line.startswith("@"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 11:
                continue
            read_id, flag, reference, pos, mapq_text, cigar = fields[:6]
            mapq = float(mapq_text) if mapq_text.isdigit() else 0.0
            taxid = parse_taxid(reference)
            query_aligned, query_total, aligned_bases = cigar_lengths(cigar)
            edit_distance = nm_tag(fields)
            identity = max(0.0, (aligned_bases - edit_distance) / aligned_bases) if aligned_bases else 0.0
            coverage = query_aligned / query_total if query_total else 0.0
            passed = reference != "*" and mapq >= args.min_mapq and identity >= args.min_identity and coverage >= args.min_coverage
            if include_taxids and taxid not in include_taxids:
                passed = False
            if exclude_taxids and taxid in exclude_taxids:
                passed = False
            out.write(
                f"{args.sample}\t{read_id}\t{reference}\t{taxid}\t{mapq:.0f}\t{aligned_bases}\t"
                f"{identity:.6f}\t{coverage:.6f}\t{str(passed).lower()}\n"
            )


if __name__ == "__main__":
    main()
