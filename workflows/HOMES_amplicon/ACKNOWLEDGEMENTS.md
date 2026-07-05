# Acknowledgements

HOMES_amplicon is an independent HOMES workflow that provides one entry point for amplicon sequencing analyses.

The short-read Illumina branch is integrated directly into HOMES_amplicon. Its design is informed by public amplicon workflow practice, including nf-core/ampliseq.

The Nanopore branch is designed with awareness of Oxford Nanopore Technologies EPI2ME Labs wf-16s, a public workflow for Nanopore 16S/18S/ITS taxonomic profiling. HOMES_amplicon does not vendor wf-16s source code and is not an official EPI2ME Labs workflow.

Long-read amplicon mode in HOMES_amplicon is intentionally Nanopore-only. PacBio is excluded from this branch because its sequencing error profile and appropriate analysis choices differ.

Users should cite the relevant upstream tools, methods, databases, and workflows when they contribute to an analysis.
