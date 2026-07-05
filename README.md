# HOMES

HOMES (**Harmonizing 'Omics for Managing Environmental Systems**) is a public Nextflow workflow collection for wastewater and environmental microbiome monitoring. It is designed for utilities, testing laboratories, consultants, and researchers who need reproducible amplicon and shotgun metagenomic analysis across Illumina and Oxford Nanopore sequencing data.

The project focuses on wastewater-industry needs: consistent sample tracking, portable containerized execution, transparent quality-control outputs, taxonomic abundance tables, and HTML reports that can be shared with technical and non-technical stakeholders.

## Workflows

```text
workflows/
  HOMES_amplicon/         # combined amplicon entry point: --platform short or --platform nanopore
  HOMES_metagenomics/     # combined metagenomic entry point: --platform illumina or --platform nanopore
```

## Amplicon Module

`HOMES_amplicon` is the public entry point for marker-gene microbiome analyses. It supports short-read amplicon workflows for 16S/18S/ITS-style datasets and a Nanopore-only long-read amplicon branch with QC, optional host removal, taxonomy classification, abundance tables, diversity summaries, and an HTML report.

```bash
nextflow run workflows/HOMES_amplicon \
  -profile test_short,docker \
  --platform short \
  --trunclenf 230 \
  --trunclenr 229 \
  --outdir results/HOMES_amplicon_short_test \
  -resume
```

```bash
nextflow run workflows/HOMES_amplicon \
  -profile nanopore_taxonomy_test,docker \
  --outdir results/HOMES_amplicon_nanopore_taxonomy_test \
  -resume
```

The Nanopore branch is intentionally Nanopore-only. PacBio is not included because PacBio and Nanopore reads have different error profiles and should not silently share the same assumptions.

## Metagenomics Module

`HOMES_metagenomics` is the public entry point for shotgun metagenomic analyses. It provides Illumina and Nanopore branches while keeping HOMES output names stable:

```bash
STORE="${HOME}/.homes/metagenomics"

nextflow run workflows/HOMES_metagenomics \
  -profile test_illumina,docker \
  --platform illumina \
  --database_set Standard-8 \
  --download_databases true \
  --store_dir "$STORE" \
  --outdir results/HOMES_metagenomics_illumina_standard8 \
  -resume
```

Use `-profile test_nanopore,docker` with the same `--database_set Standard-8` options for the bundled tiny Nanopore test sample. The first run downloads the selected database into `--store_dir`; later runs reuse it.

## Outputs

Both modules are organized around a stable HOMES output contract:

- `qc/` for read-quality and preprocessing summaries.
- `taxonomy/` for classifier outputs and per-sample taxonomy tables.
- `abundance/` for count and relative-abundance matrices.
- `report/` for shareable HTML summaries.
- `pipeline_info/` for validated inputs, versions, and run metadata.

## Development Notes

Commit code, documentation, parameter templates, and small test datasets.

Do not commit:

- `work/`
- `results/`
- `.nextflow/`
- `.nextflow.log*`
- large raw sequencing datasets
- large reference databases
- Docker or Singularity cache files

## Acknowledgements

HOMES workflows are independent project workflows. Public workflow designs and documentation, including nf-core/ampliseq and Oxford Nanopore Technologies EPI2ME Labs wf-16s, are acknowledged where they informed workflow design. See workflow-level `ACKNOWLEDGEMENTS.md` files for details.
