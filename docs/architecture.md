# HOMES Architecture

## Design Goal

HOMES should become one coherent GitHub repository that organizes multiple microbiome analysis modes while keeping each branch independently testable.

## Workflow Families

```text
unified samplesheet
  |
  v
input validation
  |
  v
workflow selection
  |
  +-- HOMES_Ampli_ShortSeq
  +-- HOMES_Ampli_LongSeq
  +-- HOMES_Meta_ShortSeq
  +-- HOMES_Meta_LongSeq
  +-- HOMES_rD_rQ
  |
  v
standardized outputs
  |
  v
summary reports
```

## Development Principle

Use mature external pipelines when they are reliable, but keep HOMES-specific choices in this repository:

- samplesheet conventions
- run scripts
- parameter files
- project documentation
- custom rD+rQ scripts
- custom Nextflow modules

## Why Not Copy All nf-core Code?

Copying all of `nf-core/ampliseq` makes future updates difficult. The cleaner first step is to call a pinned version:

```bash
nextflow run nf-core/ampliseq -r 2.18.0
```

If HOMES later needs deep internal changes, fork or vendor the relevant workflow deliberately.

