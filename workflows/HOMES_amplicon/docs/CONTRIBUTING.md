# Contributing To HOMES_amplicon

Contributions should keep the workflow reproducible, documented, and testable.

## Development Checklist

Before opening or merging a change:

- keep workflow logic in `main.nf`, `workflows/`, `subworkflows/`, or `modules/`
- keep helper scripts in `bin/`
- update `nextflow_schema.json` when adding or changing user-facing parameters
- update `README.md` or `docs/` for user-visible behavior changes
- retain or add tests under `tests/` and `conf/test*.config`
- avoid committing `work/`, `results/`, raw FASTQ files, or large reference databases

## Coding Style

Prefer small, named processes and subworkflows. Avoid hard-coded absolute paths. Parameters should be exposed through `nextflow_schema.json` and documented with clear descriptions.

## Testing

At minimum, validate the minimal test profile:

```bash
nextflow run HOMES/workflows/HOMES_amplicon \
  -profile test,docker \
  --outdir HOMES/results/HOMES_amplicon_test \
  -resume
```

For changes to modules or subworkflows, add targeted tests where practical.
