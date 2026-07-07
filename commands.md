# HOMES Command Log

Use this file to record and reuse HOMES setup, test, and example run commands.

## Check Software

```bash
nextflow -version
docker --version
java -version
```

## Install Docker

Install Docker Desktop or Docker Engine from the official Docker documentation:

```text
https://docs.docker.com/get-started/get-docker/
```

After installation, start Docker and check:

```bash
docker --version
docker run hello-world
```

Commands that use a `,docker` profile require Docker Desktop or the Docker service to be running.

## Install Nextflow

Nextflow requires Java 17 or later.

```bash
java -version
curl -s https://get.nextflow.io | bash
chmod +x nextflow
mkdir -p "$HOME/.local/bin"
mv nextflow "$HOME/.local/bin/"
export PATH="$PATH:$HOME/.local/bin"
nextflow info
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

## Run HOMES_assembly Illumina Stub Test

```bash
nextflow run workflows/HOMES_assembly \
  -profile test_illumina,docker \
  --outdir results/HOMES_assembly_illumina_stub \
  -stub-run \
  -resume
```

## Run HOMES_assembly Nanopore Stub Test

```bash
nextflow run workflows/HOMES_assembly \
  -profile test_nanopore,docker \
  --outdir results/HOMES_assembly_nanopore_stub \
  -stub-run \
  -resume
```

## Run HOMES_assembly Illumina Tiny Test

```bash
nextflow run workflows/HOMES_assembly \
  -profile test_illumina,docker \
  --platform illumina \
  --assembler megahit \
  --outdir results/HOMES_assembly_illumina_test \
  -resume
```

## Run HOMES_assembly Nanopore Tiny Test

```bash
nextflow run workflows/HOMES_assembly \
  -profile test_nanopore,docker \
  --platform nanopore \
  --assembler flye \
  --genome_size 20k \
  --outdir results/HOMES_assembly_nanopore_test \
  -resume
```

## Run HOMES_assembly Illumina Real Data

```bash
nextflow run workflows/HOMES_assembly \
  -profile docker \
  --platform illumina \
  --assembler megahit \
  --binner metabat2 \
  --annotation_tool prokka \
  --input /path/to/illumina_samplesheet.csv \
  --outdir results/HOMES_assembly_illumina_MAGs \
  -resume
```

## Run HOMES_assembly Nanopore On SLURM

```bash
nextflow run workflows/HOMES_assembly \
  -profile server_slurm \
  --platform nanopore \
  --assembler flye \
  --genome_size 100m \
  --input /path/to/nanopore_samplesheet.csv \
  --outdir /path/to/results/HOMES_assembly_nanopore \
  --server_queue normal \
  -resume
```
