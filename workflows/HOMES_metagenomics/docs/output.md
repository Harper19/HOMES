# HOMES_metagenomics Output

The workflow keeps the same top-level output groups for Illumina and Nanopore metagenomics.

## QC

```text
qc/
  <platform>.qc.summary.tsv
```

Nanopore QC records long-read read statistics. Illumina QC records short-read preprocessing and quality summaries. The HOMES QC table includes total reads, analysis-ready reads, mean/min/max read length, N50 read length, and mean read quality.

## Taxonomy

```text
taxonomy/
  <platform>.taxonomy.tsv
  <sample>.kraken2.report
  <sample>.kraken2.output
```

Nanopore and Illumina taxonomy currently use Kraken2 classifier outputs.

## Abundance

```text
abundance/
  <platform>.abundance.tsv
  <platform>.relative_abundance.tsv
  <sample>.bracken.tsv
  <sample>.bracken.report
```

Nanopore and Illumina abundance outputs provide merged count and relative abundance tables from the Kraken2 report. Bracken outputs are also published when `--bracken true`.

## Report

```text
report/
  HOMES_metagenomics.<platform>.report.html
```
