# Usage

## Samplesheet

`HOMES_assembly` uses a CSV samplesheet:

| column | required | description |
| --- | --- | --- |
| `sample` | yes | Sample name. |
| `fastq_1` | yes | R1 FASTQ for Illumina or reads FASTQ for Nanopore. Plain or gzipped FASTQ is supported. |
| `fastq_2` | Illumina paired only | R2 FASTQ. Leave blank for Nanopore or single-end Illumina. |
| `read_layout` | yes | `paired` or `single` for Illumina; `single` for Nanopore. |
| `assembly_group` | no | Reserved for future grouped assemblies. Current default is one coassembly per run. |

## Illumina

```bash
nextflow run workflows/HOMES_assembly \
  -profile test_illumina,docker \
  --platform illumina \
  --assembler megahit \
  --input workflows/HOMES_assembly/assets/samplesheets/illumina_samplesheet.csv \
  --outdir results/HOMES_assembly_illumina_test \
  -resume
```

The `test_illumina` profile uses `--binner native --annotation_tool native` for fast local validation. For real MAG-style analysis use:

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

## Nanopore

```bash
nextflow run workflows/HOMES_assembly \
  -profile test_nanopore,docker \
  --platform nanopore \
  --assembler flye \
  --genome_size 100m \
  --input workflows/HOMES_assembly/assets/samplesheets/nanopore_samplesheet.csv \
  --outdir results/HOMES_assembly_nanopore_test \
  -resume
```

For real Nanopore assembly with downstream binning and annotation:

```bash
nextflow run workflows/HOMES_assembly \
  -profile docker \
  --platform nanopore \
  --assembler flye \
  --genome_size 100m \
  --binner metabat2 \
  --annotation_tool prokka \
  --input /path/to/nanopore_samplesheet.csv \
  --outdir results/HOMES_assembly_nanopore_MAGs \
  -resume
```

## Key Parameters

| parameter | default | description |
| --- | --- | --- |
| `--trim_reads` | `true` | Run HOMES native adapter/quality trimming before assembly. |
| `--min_read_quality` | `10` | Minimum end-trimming quality threshold. |
| `--min_read_length` | `50` | Minimum retained read length after trimming. |
| `--adapter_1`, `--adapter_2` | empty | Optional adapter sequences to clip from R1/R2 or Nanopore reads. |
| `--binner` | `metabat2` | Binning method. Use `metabat2` for real runs or `native` for lightweight validation. |
| `--skip_binning` | `false` | Skip external binning and pass contigs forward as a pseudo-bin. |
| `--annotation_tool` | `prokka` | Genome and functional annotation method. Use `prokka` for real runs or `native` for lightweight validation. |
| `--skip_annotation` | `false` | Skip genome annotation. |
| `--skip_functional_annotation` | `false` | Produce genome annotation summary but skip the functional gene table. |

## Server

Use `server_slurm` on a SLURM server:

```bash
nextflow run workflows/HOMES_assembly \
  -profile server_slurm \
  --platform nanopore \
  --assembler flye \
  --genome_size 100m \
  --binner metabat2 \
  --annotation_tool prokka \
  --input /path/to/nanopore_samplesheet.csv \
  --outdir /path/to/results/HOMES_assembly_nanopore \
  --server_queue normal \
  -resume
```

Use `server_pbs` on a PBS/Torque server:

```bash
nextflow run workflows/HOMES_assembly \
  -profile server_pbs \
  --platform illumina \
  --assembler megahit \
  --binner metabat2 \
  --annotation_tool prokka \
  --input /path/to/illumina_samplesheet.csv \
  --outdir /path/to/results/HOMES_assembly_illumina \
  -resume
```

The server profiles use Singularity by default because that is usually safer on shared HPC systems. If the server uses Docker instead, use `-profile docker` and configure the executor in your site config.
