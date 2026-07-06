# Output

`HOMES_assembly` writes the following directories:

| directory | contents |
| --- | --- |
| `trimmed_reads/` | Trimmed/filtered FASTQ files used for assembly. |
| `qc/` | Trim summary, read QC summary, read length distribution, and Q value distribution tables. |
| `assembly/` | Assembled contigs FASTA and assembly statistics table. |
| `binning/` | Genome bins and binning summary table. |
| `annotation/` | Genome annotation outputs, annotation summary, and functional gene annotation table. |
| `report/` | Shareable HOMES HTML assembly report. |
| `pipeline_info/` | Validated samplesheet, assembler command, and versions files. |

Important files:

| file | description |
| --- | --- |
| `qc/<platform>.trim.summary.tsv` | Per-read-file trimming/filtering summary. |
| `assembly/HOMES_assembly.<platform>.contigs.fasta` | Final contigs FASTA. |
| `assembly/HOMES_assembly.<platform>.assembly_stats.tsv` | Contig count, total bases, min/max contig length, N50, and GC percent. |
| `binning/HOMES_assembly.<platform>.binning_summary.tsv` | Bin count and size metrics for recovered bins. |
| `annotation/HOMES_assembly.<platform>.annotation_summary.tsv` | Per-bin genome annotation summary. |
| `annotation/HOMES_assembly.<platform>.functional_gene_annotations.tsv` | Functional gene annotation table with gene IDs, product names, EC numbers, KO IDs where available, and source. |
| `qc/<platform>.qc.summary.tsv` | Per-sample read count, base count, read N50, and mean read quality. |
| `report/HOMES_assembly.<platform>.report.html` | HTML summary report. |
