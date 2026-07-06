#!/usr/bin/env python3

import argparse
import csv
import shutil
import subprocess
from pathlib import Path


def as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def require_command(command):
    if shutil.which(command) is None:
        raise RuntimeError(
            f"Required command '{command}' was not found. Run with Docker/Singularity "
            "or disable binning with --skip_binning true."
        )


def read_fasta(path):
    name = None
    seq = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name:
                    yield name, "".join(seq)
                name = line[1:].split()[0]
                seq = []
            else:
                seq.append(line)
        if name:
            yield name, "".join(seq)


def write_fasta(records, path):
    with open(path, "w") as handle:
        for name, seq in records:
            handle.write(f">{name}\n")
            for index in range(0, len(seq), 80):
                handle.write(seq[index : index + 80] + "\n")


def fasta_stats(path):
    lengths = []
    gc = 0
    total = 0
    for _, seq in read_fasta(path):
        seq = seq.upper()
        lengths.append(len(seq))
        gc += seq.count("G") + seq.count("C")
        total += len(seq)
    return lengths, gc, total


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


def summarize_bins(bin_paths, summary_path, platform, binner, source):
    with open(summary_path, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["bin_id", "platform", "binner", "contigs", "total_bases", "n50", "gc_percent", "source"])
        for bin_path in sorted(bin_paths):
            lengths, gc, total = fasta_stats(bin_path)
            gc_percent = round(gc / total * 100, 2) if total else 0
            writer.writerow([bin_path.stem, platform, binner, len(lengths), total, n50(lengths), gc_percent, source])


def native_single_bin(contigs, output_dir, platform, min_contig_len):
    records = [(name, seq) for name, seq in read_fasta(contigs) if len(seq) >= min_contig_len]
    if not records:
        records = list(read_fasta(contigs))
    bin_path = output_dir / f"HOMES_assembly.{platform}.bin.001.fasta"
    write_fasta(records, bin_path)
    return [bin_path]


def run_metabat2(contigs, output_dir, platform):
    require_command("metabat2")
    prefix = output_dir / f"HOMES_assembly.{platform}.bin"
    subprocess.run(["metabat2", "-i", str(contigs), "-o", str(prefix)], check=True)
    return sorted(output_dir.glob(f"HOMES_assembly.{platform}.bin.*.fa*"))


def main():
    parser = argparse.ArgumentParser(description="Run or summarize HOMES metagenome binning.")
    parser.add_argument("--contigs", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--binner", required=True, choices=["metabat2", "native"])
    parser.add_argument("--skip", required=True)
    parser.add_argument("--min_contig_len", type=int, default=1500)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    contigs = Path(args.contigs)

    if as_bool(args.skip):
        bin_paths = native_single_bin(contigs, output_dir, args.platform, 0)
        summarize_bins(bin_paths, args.summary, args.platform, args.binner, "contigs_passthrough_skip_binning")
    elif args.binner == "native":
        bin_paths = native_single_bin(contigs, output_dir, args.platform, args.min_contig_len)
        summarize_bins(bin_paths, args.summary, args.platform, args.binner, "native_single_bin")
    else:
        bin_paths = run_metabat2(contigs, output_dir, args.platform)
        summarize_bins(bin_paths, args.summary, args.platform, args.binner, "metabat2")


if __name__ == "__main__":
    main()
