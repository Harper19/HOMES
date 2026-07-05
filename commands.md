# HOMES Command Log

Use this file to record commands that were actually run.

## Check Software

```bash
nextflow -version
docker --version
java -version
```

## Run HOMES_amplicon Short-Read Full Report Test

```bash
nextflow run workflows/HOMES_amplicon \
  -profile test_short,docker \
  --platform short \
  --trunclenf 230 \
  --trunclenr 229 \
  --skip_qiime true \
  --outdir results/HOMES_amplicon_short_test \
  -resume
```

## Run HOMES_amplicon Nanopore Taxonomy Test

```bash
nextflow run workflows/HOMES_amplicon \
  -profile nanopore_taxonomy_test,docker \
  --outdir results/HOMES_amplicon_nanopore_taxonomy_test \
  -resume
```

## Run HOMES_metagenomics Illumina Stub Test

```bash
nextflow run workflows/HOMES_metagenomics \
  -profile test_illumina,docker \
  --platform illumina \
  --outdir results/HOMES_metagenomics_illumina_test \
  -stub-run \
  -resume
```

## Run HOMES_metagenomics Nanopore Stub Test

```bash
nextflow run workflows/HOMES_metagenomics \
  -profile test_nanopore,docker \
  --platform nanopore \
  --outdir results/HOMES_metagenomics_nanopore_test \
  -stub-run \
  -resume
```
