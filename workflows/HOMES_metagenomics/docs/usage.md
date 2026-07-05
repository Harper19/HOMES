# HOMES_metagenomics Usage

## Illumina

```bash
nextflow run workflows/HOMES_metagenomics \
  --platform illumina \
  --input samplesheet.csv \
  --outdir results/HOMES_metagenomics_illumina \
  -profile docker
```

Illumina mode is the short-read metagenomics branch. The first classifier target is Kraken2 with optional Bracken abundance estimation.

## Database cache

Use an existing Kraken2 database:

```bash
nextflow run workflows/HOMES_metagenomics --kraken2_db /path/to/kraken2_db
```

Or download once and reuse later:

```bash
nextflow run workflows/HOMES_metagenomics --database_url https://example.org/kraken2_database.tar.gz --store_dir /path/to/HOMES_metagenomics_store
```

## Nanopore

```bash
nextflow run workflows/HOMES_metagenomics \
  --platform nanopore \
  --input samplesheet.csv \
  --outdir results/HOMES_metagenomics_nanopore \
  -profile docker
```

Nanopore mode is the long-read metagenomics branch. The first classifier target is Kraken2 with optional Bracken abundance estimation; Minimap2 remains a planned option for custom references.

## Stub tests

```bash
nextflow run workflows/HOMES_metagenomics -profile test_illumina,docker -stub-run
nextflow run workflows/HOMES_metagenomics -profile test_nanopore,docker -stub-run
```
