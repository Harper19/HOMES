# HOMES_metagenomics Usage

## Illumina

```bash
nextflow run workflows/HOMES_metagenomics \
  --platform illumina \
  --input samplesheet.csv \
  --database_set Standard-8 \
  --download_databases true \
  --skip_taxonomy false \
  --outdir results/HOMES_metagenomics_illumina \
  -profile docker
```

Illumina mode is the short-read metagenomics branch. The current classifier is Kraken2 with optional Bracken abundance estimation.

## Database cache

Use an existing Kraken2 database:

```bash
nextflow run workflows/HOMES_metagenomics --kraken2_db /path/to/kraken2_db --skip_taxonomy false
```

Or download once and reuse later:

```bash
nextflow run workflows/HOMES_metagenomics --database_url https://example.org/kraken2_database.tar.gz --download_databases true --skip_taxonomy false --store_dir db
```

## Nanopore

```bash
nextflow run workflows/HOMES_metagenomics \
  --platform nanopore \
  --input samplesheet.csv \
  --database_set Standard-8 \
  --download_databases true \
  --skip_taxonomy false \
  --outdir results/HOMES_metagenomics_nanopore \
  -profile docker
```

Nanopore mode is the long-read metagenomics branch. The current classifier is Kraken2 with optional Bracken abundance estimation; Minimap2 remains a planned option for custom references.

## Functional Gene Annotation

Functional profiling is intentionally off by default. It is contig-based: first run `HOMES_assembly`, or provide another metagenome assembly FASTA with `--functional_contigs`. In real analysis mode HOMES uses Prodigal gene prediction, eggNOG-mapper functional annotation, and Minimap2 to count each sample's reads against the predicted genes.

```bash
EGGNOG_DB="$PWD/db/eggnog"

nextflow run workflows/HOMES_metagenomics \
  -profile docker \
  --platform nanopore \
  --input samplesheet.csv \
  --functional_contigs results/HOMES_assembly/assembly/HOMES_assembly.nanopore.contigs.fasta \
  --run_functional_annotation true \
  --functional_annotation_tool eggnog \
  --functional_mapping_tool minimap2 \
  --eggnog_data_dir "$EGGNOG_DB" \
  --download_functional_db true \
  --outdir results/HOMES_metagenomics_nanopore_functional \
  -resume
```

The first run downloads the eggNOG data into `EGGNOG_DB`; later runs reuse it. The core database is about 45 GB, so use a server profile and adequate disk/RAM for non-trivial metagenomes. After it has been downloaded, use `--download_functional_db false` or omit the flag.

## Stub tests

```bash
nextflow run workflows/HOMES_metagenomics -profile test_illumina,docker -stub-run
nextflow run workflows/HOMES_metagenomics -profile test_nanopore,docker -stub-run
```
