# HOMES_metagenomics Databases

HOMES_metagenomics supports a persistent database cache for Kraken2/Bracken-style databases.

## Use an existing local database

If a Kraken2/Bracken database already exists, pass the directory directly:

```bash
nextflow run workflows/HOMES_metagenomics \
  -profile test_nanopore,docker \
  --kraken2_db /path/to/kraken2_db \
  --bracken_db /path/to/kraken2_db \
  --outdir results/HOMES_metagenomics_nanopore
```

This writes `pipeline_info/database_info.tsv` with `status=provided`.

## Preset database sets

If `--kraken2_db` is not provided, HOMES resolves `--database_set` through the preset map in `nextflow.config`. The Nanopore presets mirror the wf-metagenomics database choices:

```text
Standard-8
PlusPF-8
PlusPFP-8
ncbi_16s_18s
ncbi_16s_18s_28s_ITS
SILVA_138_1
Greengenes2_plus
```

For example:

```bash
nextflow run workflows/HOMES_metagenomics \
  -profile test_nanopore,docker \
  --database_set Standard-8 \
  --outdir results/HOMES_metagenomics_nanopore
```

On the first completed run, HOMES downloads the preset Kraken2 database and taxonomy into the persistent cache. Later runs with the same `--database_set` reuse the completed cache.

By default, HOMES uses `~/.homes/metagenomics` as the persistent cache root:

```text
~/.homes/metagenomics/
  Standard-8/
    kraken2/
      .homes_metagenomics_database.complete
    taxonomy/
      .homes_metagenomics_database.complete
  _downloads/
    Standard-8/
```

Use `--store_dir` to put the cache on a project disk or shared filesystem.

## Status values

Each run writes `pipeline_info/database_info.tsv`. The `status` will be:

- `downloaded`: archive was downloaded or extracted in this run.
- `reused`: an existing completed cache was found.
- `provided`: `--kraken2_db` was supplied directly.
- `not_configured`: no local database path or database URL was supplied.
- `download_disabled`: a URL was supplied, but `--download_databases false` was set and no completed cache exists.

## Override with custom URLs

Use `--database_url` and `--taxonomy_url` to override the preset URLs while keeping the same first-download/reuse behavior:

```bash
nextflow run workflows/HOMES_metagenomics \
  -profile test_nanopore,docker \
  --database_name custom_kraken2 \
  --database_url https://example.org/custom_kraken2.tar.gz \
  --taxonomy_url https://example.org/custom_taxdump.zip
```

Use `--download_databases false` to require a completed cache and prevent automatic download.

## Minimap2 reference presets

Targeted presets such as `ncbi_16s_18s`, `SILVA_138_1`, and `Greengenes2_plus` also include `reference` and `ref2taxid` URLs. These are recorded in `database_info.tsv` for Minimap2-compatible branches. You can override them with:

```bash
nextflow run workflows/HOMES_metagenomics \
  -profile test_nanopore,docker \
  --classifier minimap2 \
  --reference /path/to/reference.fasta \
  --ref2taxid /path/to/ref2taxid.tsv
```

## GitHub note

Keep full Kraken2/Bracken databases outside GitHub because they are usually large. Commit only the workflow code, docs, samplesheets, and small test data. Use `--store_dir` for reusable local or shared database storage.
