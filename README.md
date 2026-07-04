# HOMES

HOMES is a microbiome Nextflow project for coordinating five related analysis workflows:

1. `HOMES_Ampli_ShortSeq` - short-read amplicon workflow, currently wrapping `nf-core/ampliseq`
2. `HOMES_Ampli_LongSeq` - long-read amplicon workflow
3. `HOMES_Meta_ShortSeq` - short-read metagenomic workflow
4. `HOMES_Meta_LongSeq` - long-read metagenomic workflow
5. `HOMES_rD_rQ` - custom rD+rQ workflow

## Current Development Stage

The first working branch is `HOMES_Ampli_ShortSeq`, based on:

```text
project name : nf-core/ampliseq
repository   : https://github.com/nf-core/ampliseq
local path   : /Users/kbian8/.nextflow/assets/.repos/nf-core/ampliseq
main script  : main.nf
description  : Amplicon sequencing analysis workflow using DADA2 and QIIME2
```

This repository does not vendor the full nf-core source code. Instead, it keeps HOMES-specific parameters, samplesheets, run scripts, documentation, and future custom modules.

## Layout

```text
HOMES/
  README.md
  commands.md
  nextflow.config
  docs/
  workflows/
    HOMES_Ampli_ShortSeq/
    HOMES_Ampli_LongSeq/
    HOMES_Meta_ShortSeq/
    HOMES_Meta_LongSeq/
    HOMES_rD_rQ/
  samplesheets/
  scripts/
  modules/
  configs/
  assets/
  envs/
  tests/
```

## Quick Start: nf-core/ampliseq Test

From the HOMES repository root:

```bash
bash workflows/HOMES_Ampli_ShortSeq/run_nfcore_test_docker.sh
```

This runs:

```bash
nextflow run nf-core/ampliseq -r 2.18.0 -profile test,docker
```

with HOMES-specific local `work` and `tmp` directories.

## GitHub Rule

Commit code, documentation, parameter templates, and small samplesheet templates.

Do not commit:

- `work/`
- `results/`
- `.nextflow/`
- `.nextflow.log*`
- raw FASTQ files
- large reference databases
- Docker cache

