# HOMES_amplicon

HOMES_amplicon is the amplicon sequencing workflow in HOMES (**Harmonizing 'Omics for Managing Environmental Systems**).

It provides one public entry point with two platform modes:

- `--platform short`: Illumina paired-end or single-end short-read amplicon analysis with DADA2 and an R-native downstream path.
- `--platform nanopore`: Nanopore-only long-read amplicon analysis with QC/filtering, optional host removal, minimap2 or Kraken2 classification, optional Bracken abundance estimation, relative abundance tables, diversity tables, and an HTML report.

PacBio is intentionally not included in the long-read branch because PacBio and Nanopore have different error models and should not silently share the same assumptions.

## Quick Start

Run the Illumina short-read test:

```bash
nextflow run workflows/HOMES_amplicon \
  -profile test_short,docker \
  --outdir results/HOMES_amplicon_short_test \
  --trunclenf 230 \
  --trunclenr 229 \
  --skip_qiime true \
  -resume
```

Run the Nanopore QC test:

```bash
nextflow run workflows/HOMES_amplicon \
  -profile nanopore_test,docker \
  --outdir results/HOMES_amplicon_nanopore_test \
  -resume
```

Run the Nanopore taxonomy test with the bundled tiny reference:

```bash
nextflow run workflows/HOMES_amplicon \
  -profile nanopore_taxonomy_test,docker \
  --outdir results/HOMES_amplicon_nanopore_taxonomy_test \
  -resume
```

## Illumina Short-Read Mode

```bash
nextflow run workflows/HOMES_amplicon \
  -profile docker \
  --platform short \
  --input data/illumina/samplesheet.tsv \
  --metadata data/illumina/metadata.tsv \
  --FW_primer GTGYCAGCMGCCGCGGTAA \
  --RV_primer GGACTACNVGGGTWTCTAAT \
  --trunclenf 230 \
  --trunclenr 229 \
  --tax_abundance_levels all \
  --skip_qiime true \
  --outdir results/HOMES_amplicon_short \
  -resume
```

Short-read mode is R-native by default. Taxonomy uses DADA2 `assignTaxonomy()` unless another non-QIIME2 classifier is explicitly selected. Diversity, ordination, differential abundance and PERMANOVA should stay in the R path using packages such as `phyloseq`, `vegan`, `DESeq2` and R Markdown reporting. QIIME2 is not enabled by default.

The short-read HTML report includes HOMES branding and an explicit Illumina short-read platform label. Taxonomic relative abundance can be reported for every available taxonomy rank with `--tax_abundance_levels all`, or limited to selected ranks such as `--tax_abundance_levels Genus` or `--tax_abundance_levels Family,Genus,Species`.

The bundled `test_short` profile runs DADA2 denoising, DADA2 taxonomy, R-native abundance summaries, MultiQC and the summary report. For speed and reproducibility, the test profile uses a tiny bundled DADA2 custom taxonomy reference. For real analyses, provide an appropriate full marker reference with `--dada_ref_taxonomy` or `--dada_ref_tax_custom`.

### Short-Read Marker Types

Short-read mode can be used for common Illumina amplicon marker datasets, including:

- `16S`: bacterial/archaeal rRNA amplicons; use suitable 16S primers and a compatible reference such as SILVA, GTDB, RDP, or Greengenes.
- `18S`: eukaryotic rRNA amplicons; use suitable 18S primers and a compatible reference such as PR2 or SILVA.
- `ITS`: fungal/eukaryotic ITS amplicons; use ITS primers and a compatible reference such as UNITE. ITS regions often have variable length, so consider `--illumina_pe_its` and `--cut_its itsx`.

Example ITS run:

```bash
nextflow run workflows/HOMES_amplicon \
  -profile docker \
  --platform short \
  --input data/illumina_its/samplesheet.tsv \
  --metadata data/illumina_its/metadata.tsv \
  --FW_primer YOUR_ITS_FORWARD_PRIMER \
  --RV_primer YOUR_ITS_REVERSE_PRIMER \
  --illumina_pe_its \
  --cut_its itsx \
  --dada_ref_taxonomy "unite-fungi=10.0" \
  --skip_qiime true \
  --outdir results/HOMES_amplicon_short_its \
  -resume
```

## Nanopore Mode

QC/filtering only:

```bash
nextflow run workflows/HOMES_amplicon \
  -profile docker \
  --platform nanopore \
  --target_marker 16S \
  --fastq "data/nanopore_fastq/*.fastq.gz" \
  --classifier none \
  --nanopore_min_len 1000 \
  --min_read_qual 8 \
  --outdir results/HOMES_amplicon_nanopore_qc \
  -resume
```

minimap2 taxonomy with relative abundance at genus level:

```bash
nextflow run workflows/HOMES_amplicon \
  -profile docker \
  --platform nanopore \
  --target_marker 16S \
  --fastq "data/nanopore_fastq/*.fastq.gz" \
  --classifier minimap2 \
  --reference refs/16s_reference.fasta \
  --tax_level all \
  --minimap2_min_mapq 0 \
  --minimap2_min_identity 0.8 \
  --minimap2_min_coverage 0.8 \
  --abundance_threshold 0.001 \
  --outdir results/HOMES_amplicon_nanopore_minimap2 \
  -resume
```

Custom minimap2 reference FASTA:

- `--reference` expects a FASTA file. HOMES_amplicon builds the alignment directly from that FASTA at run time; a separate minimap2 index is not required.
- The FASTA header is also used to recover taxonomy. For best results, include taxonomy in each sequence header using one of these styles:

```text
>ref001 k__Bacteria;p__Proteobacteria;c__Gammaproteobacteria;o__Enterobacterales;f__Enterobacteriaceae;g__Escherichia;s__Escherichia coli
>ref002;kingdom=Bacteria;phylum=Firmicutes;class=Bacilli;order=Lactobacillales;family=Lactobacillaceae;genus=Lactobacillus;species=Lactobacillus fermentum
>ref003;region=16S;species=Veillonella_rogosae
```

- If only `species=Genus_species` is present, the workflow will infer genus from the first species word.
- If no parseable taxonomy is present, use `--tax_level reference`; otherwise genus/species abundance may be reported as the full reference identifier or `Unclassified`.
- Use `--tax_level all` to create abundance tables for all available taxonomy levels and enable the taxonomy-level dropdown in the Nanopore HTML report. Use a single level such as `--tax_level genus` when only one level is needed.
- Optional `taxid=12345`, `taxid:12345`, `|taxid|12345`, or `kraken:taxid|12345` text in the header can be used with `--minimap2_filter_taxids` and `--minimap2_exclude_taxids`.
- No separate taxonomy TSV is currently required for minimap2 mode.

Kraken2 taxonomy:

```bash
nextflow run workflows/HOMES_amplicon \
  -profile docker \
  --platform nanopore \
  --target_marker 16S \
  --fastq "data/nanopore_fastq/*.fastq.gz" \
  --classifier kraken2 \
  --kraken2_db refs/kraken2_db \
  --tax_level all \
  --outdir results/HOMES_amplicon_nanopore_kraken2 \
  -resume
```

Custom Kraken2 reference database:

- `--kraken2_db` must point to an already built Kraken2 database directory, not a raw FASTA file.
- The runtime directory should contain Kraken2 database files such as `hash.k2d`, `opts.k2d`, and `taxo.k2d`.
- Files such as `seqid2taxid.map`, `nodes.dmp`, and `names.dmp` are used when building the database; they are not passed separately to this workflow once the database is built.
- If `--bracken true` is used, `--bracken_db` must point to a Bracken-compatible database built for the expected read length. Set that length with `--bracken_read_length`.

Kraken2 followed by Bracken:

```bash
nextflow run workflows/HOMES_amplicon \
  -profile docker \
  --platform nanopore \
  --fastq "data/nanopore_fastq/*.fastq.gz" \
  --classifier kraken2 \
  --kraken2_db refs/kraken2_db \
  --bracken true \
  --bracken_db refs/kraken2_db \
  --bracken_read_length 1500 \
  --bracken_level G \
  --tax_level genus \
  --outdir results/HOMES_amplicon_nanopore_bracken \
  -resume
```

Optional host removal:

```bash
nextflow run workflows/HOMES_amplicon \
  -profile docker \
  --platform nanopore \
  --fastq "data/nanopore_fastq/*.fastq.gz" \
  --host_reference refs/host_genome_or_amplicon_targets.fasta \
  --classifier minimap2 \
  --reference refs/16s_reference.fasta \
  --outdir results/HOMES_amplicon_nanopore_host_removed \
  -resume
```

Optional barcode/sample aliases:

```csv
barcode,sample
barcode01,Sample_A
barcode02,Sample_B
```

Use it with:

```bash
nextflow run workflows/HOMES_amplicon \
  -profile docker \
  --platform nanopore \
  --fastq data/nanopore_run \
  --sample_sheet data/nanopore_samples.csv \
  --classifier minimap2 \
  --reference refs/16s_reference.fasta \
  --outdir results/HOMES_amplicon_nanopore_samples \
  -resume
```

## Nanopore Outputs

```text
nanopore/qc/
nanopore/filtered_fastq/
nanopore/host_removal/
nanopore/minimap2/
nanopore/kraken2/
nanopore/bracken/
nanopore/abundance/
nanopore/report/homes_nanopore_report.html
```

The abundance folder contains:

- `*.counts.<tax_level>.tsv`
- `*.relative_abundance.<tax_level>.tsv`
- `*.diversity.<tax_level>.tsv`

The HTML reports show abundance as a separate section. Relative abundance tables are displayed as matrices with taxa as rows and sample IDs as columns. A taxonomy-level dropdown is shown when more than one level is available.

Nanopore mode is designed with reference to EPI2ME Labs `wf-16s` concepts while remaining a HOMES workflow. It supports Nanopore amplicon analysis for `16S`, `18S`, or `ITS` marker labels via `--target_marker`; minimap2 alignment-based classification; kraken2 k-mer classification; optional Bracken abundance estimation; taxonomic profile tables; top-taxa bar plots; and lineage exploration in the HTML report using sankey and sunburst views.

## HTML Reports

Short-read mode writes two HTML reports when reporting steps are enabled:

- `multiqc/multiqc_report.html`: FastQC, Cutadapt, DADA2 and software summary.
- `summary_report/summary_report.html`: QC, DADA2 denoising, taxonomy, abundance, diversity and downstream summaries.
- `summary_report/dada2_relative_abundance_top_taxa_<level>.svg`: R-native DADA2 taxonomic relative abundance plots for each requested taxonomy level.

Nanopore mode writes:

- `nanopore/report/homes_nanopore_report.html`: read QC, taxonomy-derived top taxa, relative abundance and diversity.
- The Nanopore report carries HOMES branding, a visible Nanopore platform label, marker label, classifier, taxonomic level, top-taxa bar plot, lineage sankey, and lineage sunburst.

## Workflow Diagrams

- `docs/images/homes_amplicon_shortread_overview.svg`
- `docs/images/homes_amplicon_nanopore_overview.svg`

## Ethics And Provenance

HOMES_amplicon is an independent workflow. Its short-read branch was built by adapting ideas and workflow structure from nf-core/ampliseq, and its Nanopore branch was designed with reference to EPI2ME Labs wf-16s concepts. See `ACKNOWLEDGEMENTS.md` and `CITATIONS.md` for attribution.
