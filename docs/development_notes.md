# Development Notes

## Recommended Order

1. Keep `HOMES_amplicon` as the single amplicon entry point.
2. Add real HOMES samplesheet and parameter templates.
3. Keep `HOMES_metagenomics` as the single shotgun metagenomics entry point.
4. Add metagenomics modules in this order: QC, host filtering, taxonomy, abundance normalization, HTML report.

## Script Rules

Scripts should:

- accept command-line arguments
- avoid hard-coded absolute paths
- write clear output files
- print package/software versions where useful
