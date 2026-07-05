# Citations

Please cite the tools, methods, databases, and workflows used in each analysis.

Core workflow infrastructure:

- Nextflow: Di Tommaso et al. Nextflow enables reproducible computational workflows. Nature Biotechnology. 2017.
- Bioconda and BioContainers when using containerized or Conda software environments.

Short-read Illumina mode:

- Cite the HOMES_amplicon workflow and the methods/tools used in that branch, including DADA2, QIIME2, Cutadapt, FastQC, MultiQC, and any reference databases used.
- Acknowledge nf-core/ampliseq when its public workflow design or documentation informs the analysis or reporting.

Nanopore mode:

- Cite Oxford Nanopore Technologies and relevant basecalling/demultiplexing software used before this workflow.
- Cite minimap2 when `--classifier minimap2` is used.
- Cite Kraken2 when `--classifier kraken2` is used.
- Acknowledge epi2me-labs/wf-16s when its public workflow design or documentation informs the analysis or reporting.
