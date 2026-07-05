# HOMES_metagenomics Output

The workflow keeps the same top-level output groups for Illumina and Nanopore metagenomics.

## QC

```text
qc/
  <platform>.qc.summary.tsv
```

Nanopore QC records long-read read statistics. Illumina QC records short-read preprocessing and quality summaries. The HOMES QC table includes total reads, analysis-ready reads, mean/min/max read length, and mean read quality.

## Taxonomy

```text
taxonomy/
  <platform>.taxonomy.tsv
```

Nanopore taxonomy supports Kraken2 or Minimap2 classifier branches. Illumina taxonomy starts with Kraken2 classifier outputs.

## Abundance

```text
abundance/
  <platform>.abundance.tsv
  <platform>.relative_abundance.tsv
```

Nanopore and Illumina abundance outputs provide merged count and relative abundance tables, with Bracken support for Kraken2 classifications.

## Report

```text
report/
  HOMES_metagenomics.<platform>.report.html
```
