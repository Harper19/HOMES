# HOMES Architecture

## Design Goal

HOMES (**Harmonizing 'Omics for Managing Environmental Systems**) is organized as one coherent GitHub repository with three independently testable wastewater microbiome workflow modules.

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
  +-- HOMES_amplicon (--platform short)
  +-- HOMES_amplicon (--platform nanopore)
  +-- HOMES_metagenomics (--platform illumina)
  +-- HOMES_metagenomics (--platform nanopore)
  +-- HOMES_assembly (--platform illumina)
  +-- HOMES_assembly (--platform nanopore)
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
- custom Nextflow modules

## Amplicon Integration

The amplicon branch is now integrated into one Nextflow entry point:

```bash
nextflow run workflows/HOMES_amplicon --platform short
nextflow run workflows/HOMES_amplicon --platform nanopore
```

Short-read and Nanopore amplicon analyses share project-level documentation and output conventions while keeping platform-specific assumptions separate.

## Metagenomics Integration

The metagenomics branch follows the same single-entry-point pattern:

```bash
nextflow run workflows/HOMES_metagenomics --platform illumina
nextflow run workflows/HOMES_metagenomics --platform nanopore
```

The public HOMES output contract is:

- `qc/` for read quality and preprocessing summaries.
- `taxonomy/` for classifier reports and per-sample taxonomy tables.
- `abundance/` for count and relative-abundance matrices.
- `report/` for HTML summaries.

## Assembly Integration

The assembly branch follows the same platform-selection pattern:

```bash
nextflow run workflows/HOMES_assembly --platform illumina
nextflow run workflows/HOMES_assembly --platform nanopore
```

The public HOMES assembly output contract is:

- `qc/` for read trimming/filtering summaries.
- `assembly/` for contigs and assembly metrics.
- `binning/` for MAG-style genome bins and bin summaries.
- `annotation/` for genome and functional annotation tables.
- `report/` for HTML summaries.
