# HOMES

<p align="center">
  <img src="workflows/HOMES_amplicon/assets/homes_report_logo.svg" alt="HOMES: Harmonizing 'Omics for Managing Environmental Systems" width="720">
</p>

```text
----------------------------------------------------
   _   _  ___  __  __ _____ ____
  | | | |/ _ \|  \/  | ____/ ___|
  | |_| | | | | |\/| |  _| \___ \
  |  _  | |_| | |  | | |___ ___) |
  |_| |_|\___/|_|  |_|_____|____/
  HOMES workflow collection
----------------------------------------------------
```

HOMES (**Harmonizing 'Omics for Managing Environmental Systems**) is a public Nextflow workflow collection for wastewater and environmental microbiome monitoring. It is designed for utilities, testing laboratories, consultants, and researchers who need reproducible amplicon and shotgun metagenomic analysis across Illumina and Oxford Nanopore sequencing data.

The project focuses on wastewater-industry needs: consistent sample tracking, portable containerized execution, transparent quality-control outputs, taxonomic abundance tables, and HTML reports that can be shared with technical and non-technical stakeholders.

## Workflows

| Workflow | README | Platforms | Primary outputs |
| --- | --- | --- | --- |
| `HOMES_amplicon` | [workflows/HOMES_amplicon/README.md](workflows/HOMES_amplicon/README.md) | `--platform short`, `--platform nanopore` | QC, taxonomy, abundance, diversity, HTML report |
| `HOMES_metagenomics` | [workflows/HOMES_metagenomics/README.md](workflows/HOMES_metagenomics/README.md) | `--platform illumina`, `--platform nanopore` | QC, Kraken2 taxonomy, abundance, HTML report |
| `HOMES_assembly` | [workflows/HOMES_assembly/README.md](workflows/HOMES_assembly/README.md) | `--platform illumina`, `--platform nanopore` | Trim/QC, contigs, bins, genome annotation, functional genes, HTML report |

Workflow-level READMEs include samplesheet formats, test commands, output paths, database notes, and platform-specific options.

## Installation

HOMES workflows are run with [Nextflow](https://docs.seqera.io/nextflow/install) and software containers. For local runs, install Docker first; for shared servers/HPC, use the workflow-level `server_slurm` or `server_pbs` profiles with Singularity where available.

### Docker

Install Docker from the official Docker documentation:

- macOS / Windows / Linux Desktop: [Get Docker](https://docs.docker.com/get-started/get-docker/)
- Linux servers without Docker Desktop: use the Docker Engine instructions linked from the same page.

After installation, open Docker Desktop or start the Docker service, then check:

```bash
docker --version
docker run hello-world
```

### Nextflow

Nextflow requires Java 17 or later. Check Java first:

```bash
java -version
```

Install Nextflow with the official self-install command:

```bash
curl -s https://get.nextflow.io | bash
chmod +x nextflow
mkdir -p "$HOME/.local/bin"
mv nextflow "$HOME/.local/bin/"
export PATH="$PATH:$HOME/.local/bin"
nextflow info
```

Add `export PATH="$PATH:$HOME/.local/bin"` to `~/.zshrc` or `~/.bashrc` if `nextflow` is not found in a new terminal.

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
STORE="${PWD}/db"

nextflow run workflows/HOMES_metagenomics \
  -profile test_illumina,docker \
  --platform illumina \
  --database_set Standard-8 \
  --download_databases true \
  --skip_taxonomy false \
  --store_dir "$STORE" \
  --outdir results/HOMES_metagenomics_illumina_standard8 \
  -resume
```

Use `-profile test_nanopore,docker` with the same `--database_set Standard-8` options for the bundled tiny Nanopore test sample. The first run downloads the selected database into `--store_dir`; later runs reuse it.

## Assembly Module

`HOMES_assembly` is the public entry point for assembling Illumina and Oxford Nanopore reads and can continue into MAG-style binning, genome annotation, and functional gene annotation. It provides a laptop-friendly test mode and server/HPC profiles for real analyses that need more CPU, memory, and walltime.

```bash
nextflow run workflows/HOMES_assembly \
  -profile test_illumina,docker \
  --platform illumina \
  --assembler megahit \
  --outdir results/HOMES_assembly_illumina_test \
  -resume
```

```bash
nextflow run workflows/HOMES_assembly \
  -profile server_slurm \
  --platform nanopore \
  --assembler flye \
  --genome_size 100m \
  --input /path/to/nanopore_samplesheet.csv \
  --outdir /path/to/results/HOMES_assembly_nanopore \
  -resume
```

## Shared Outputs

Both modules are organized around a stable HOMES output contract:

- `qc/` for read-quality and preprocessing summaries.
- `taxonomy/` for classifier outputs and per-sample taxonomy tables.
- `abundance/` for count and relative-abundance matrices.
- `assembly/` for contigs and assembly statistics where applicable.
- `binning/` and `annotation/` for MAG-style genome recovery and functional gene annotation where applicable.
- `report/` for shareable HTML summaries.
- `pipeline_info/` for validated inputs, versions, and run metadata.

## Development Notes

Commit code, documentation, parameter templates, and small test datasets.

Do not commit:

- `work/`
- `results/`
- `.nextflow/`
- `db/`
- `.nextflow.log*`
- large raw sequencing datasets
- large reference databases
- Docker or Singularity cache files

## Acknowledgements

HOMES workflows are independent project workflows. Public workflow designs and documentation, including nf-core/ampliseq and Oxford Nanopore Technologies EPI2ME Labs wf-16s, are acknowledged where they informed workflow design. See workflow-level `ACKNOWLEDGEMENTS.md` files for details.
