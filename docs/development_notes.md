# Development Notes

## Recommended Order

1. Keep `HOMES_Ampli_ShortSeq` running through `nf-core/ampliseq`.
2. Add real HOMES samplesheet and parameter templates.
3. Add custom rD+rQ scripts under `scripts/rd_rq/`.
4. Wrap rD+rQ as a Nextflow module under `modules/local/`.
5. Add long-read amplicon and metagenomic branches one at a time.

## Script Rules

Scripts should:

- accept command-line arguments
- avoid hard-coded absolute paths
- write clear output files
- print package/software versions where useful

