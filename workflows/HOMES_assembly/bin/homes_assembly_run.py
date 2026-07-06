#!/usr/bin/env python3

import argparse
import csv
import shutil
import subprocess
from pathlib import Path


def resolve_staged(path):
    candidate = Path(path)
    if candidate.exists():
        return candidate
    staged = Path.cwd() / candidate.name
    if staged.exists():
        return staged
    raise FileNotFoundError(f"Cannot find read file: {path}")


def read_samplesheet(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def require_command(command):
    if shutil.which(command) is None:
        raise RuntimeError(
            f"Required command '{command}' was not found. Run with Docker/Singularity "
            "or install the assembler on the host."
        )


def run_command(command, command_file):
    command_file.write_text(" ".join(str(part) for part in command) + "\n")
    subprocess.run(command, check=True)


def read_fasta_lengths(path):
    lengths = []
    gc = 0
    total = 0
    current = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current:
                    seq = "".join(current).upper()
                    lengths.append(len(seq))
                    gc += seq.count("G") + seq.count("C")
                    total += len(seq)
                    current = []
            else:
                current.append(line)
        if current:
            seq = "".join(current).upper()
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


def write_stats(contigs, output, assembly_name, platform, assembler):
    lengths, gc, total = read_fasta_lengths(contigs)
    gc_percent = round(gc / total * 100, 2) if total else 0
    with open(output, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "assembly",
                "platform",
                "assembler",
                "contigs",
                "total_bases",
                "min_contig",
                "max_contig",
                "n50",
                "gc_percent",
            ]
        )
        writer.writerow(
            [
                assembly_name,
                platform,
                assembler,
                len(lengths),
                total,
                min(lengths) if lengths else 0,
                max(lengths) if lengths else 0,
                n50(lengths),
                gc_percent,
            ]
        )


def run_megahit(rows, args):
    require_command("megahit")
    out_dir = Path("megahit_out")
    r1_files = []
    r2_files = []
    single_files = []
    for row in rows:
        if row["read_layout"] == "paired":
            r1_files.append(str(resolve_staged(row["fastq_1"])))
            r2_files.append(str(resolve_staged(row["fastq_2"])))
        else:
            single_files.append(str(resolve_staged(row["fastq_1"])))

    command = ["megahit", "-t", str(args.threads), "-o", str(out_dir), "--min-contig-len", str(args.min_contig_len)]
    if r1_files:
        command.extend(["-1", ",".join(r1_files), "-2", ",".join(r2_files)])
    if single_files:
        command.extend(["-r", ",".join(single_files)])
    run_command(command, Path(f"{args.out_prefix}.assembly_command.txt"))
    shutil.copyfile(out_dir / "final.contigs.fa", f"{args.out_prefix}.contigs.fasta")


def run_flye(rows, args):
    require_command("flye")
    read_files = [str(resolve_staged(row["fastq_1"])) for row in rows]
    out_dir = Path("flye_out")
    command = [
        "flye",
        "--nano-raw",
        *read_files,
        "--out-dir",
        str(out_dir),
        "--threads",
        str(args.threads),
        "--genome-size",
        args.genome_size,
    ]
    if args.flye_mode == "meta":
        command.append("--meta")
    run_command(command, Path(f"{args.out_prefix}.assembly_command.txt"))
    shutil.copyfile(out_dir / "assembly.fasta", f"{args.out_prefix}.contigs.fasta")


def main():
    parser = argparse.ArgumentParser(description="Run HOMES reads assembly.")
    parser.add_argument("--samplesheet", required=True)
    parser.add_argument("--platform", required=True, choices=["illumina", "nanopore"])
    parser.add_argument("--assembler", required=True)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--min_contig_len", type=int, default=1000)
    parser.add_argument("--genome_size", default="100m")
    parser.add_argument("--flye_mode", default="meta", choices=["meta", "isolate"])
    parser.add_argument("--out_prefix", required=True)
    args = parser.parse_args()

    rows = read_samplesheet(args.samplesheet)
    if args.platform == "illumina":
        run_megahit(rows, args)
    elif args.platform == "nanopore":
        run_flye(rows, args)
    else:
        raise ValueError(args.platform)

    write_stats(
        Path(f"{args.out_prefix}.contigs.fasta"),
        Path(f"{args.out_prefix}.assembly_stats.tsv"),
        args.out_prefix,
        args.platform,
        args.assembler,
    )


if __name__ == "__main__":
    main()
