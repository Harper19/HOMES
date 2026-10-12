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

## Functional Annotation

When `--run_functional_annotation true`, HOMES predicts genes from the supplied contig FASTA, annotates proteins with eggNOG-mapper, and maps each sample's reads back to the predicted genes. `native` outputs are only used by the bundled lightweight test profiles and are not biological annotations.

```text
functional_annotation/
  HOMES_metagenomics.<platform>.genes.fna
  HOMES_metagenomics.<platform>.proteins.faa
  HOMES_metagenomics.<platform>.functional_annotations.tsv
  HOMES_metagenomics.<platform>.functional_ko_summary.tsv
  HOMES_metagenomics.<platform>.functional_ec_summary.tsv
  HOMES_metagenomics.<platform>.functional_pathway_summary.tsv
  HOMES_metagenomics.<platform>.functional_gene_abundance.tsv
  HOMES_metagenomics.<platform>.functional_ko_abundance.tsv
  HOMES_metagenomics.<platform>.functional_ec_abundance.tsv
  HOMES_metagenomics.<platform>.functional_pathway_abundance.tsv
```

The annotation table includes gene-level COG, GO, EC, KEGG KO, KEGG pathway, and CAZy fields when eggNOG returns them. Abundance tables contain mapped-read counts; they are not relative abundance percentages.

## Report

```text
report/
  HOMES_metagenomics.<platform>.report.html
```
