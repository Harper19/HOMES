/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    HOMES Illumina reads assembly branch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { VALIDATE_ASSEMBLY_SAMPLESHEET } from '../modules/local/validate_assembly_samplesheet'
include { TRIM_ASSEMBLY_READS           } from '../modules/local/assembly_trim_reads'
include { ASSEMBLY_READ_QC              } from '../modules/local/assembly_read_qc'
include { ILLUMINA_ASSEMBLY             } from '../modules/local/illumina_assembly'
include { METAGENOME_BINNING            } from '../modules/local/metagenome_binning'
include { GENOME_FUNCTION_ANNOTATION    } from '../modules/local/genome_function_annotation'
include { ASSEMBLY_HTML_REPORT          } from '../modules/local/assembly_html_report'

def homesAssemblyReadFiles(samplesheet_path) {
    def sheet = file(samplesheet_path)
    def base = sheet.parent
    def lines = sheet.readLines().findAll { it.trim() }
    if (lines.size() < 2) {
        return []
    }
    def header = lines[0].split(',', -1) as List
    def fastq_1_idx = header.indexOf('fastq_1')
    def fastq_2_idx = header.indexOf('fastq_2')
    def paths = []
    lines.drop(1).each { line ->
        def cols = line.split(',', -1)
        [fastq_1_idx, fastq_2_idx].each { idx ->
            if (idx >= 0 && idx < cols.size()) {
                def value = cols[idx].trim()
                if (value && !value.contains('://')) {
                    def candidate = value.startsWith('/') ? value : "${base}/${value}"
                    paths << file(candidate, checkIfExists: true)
                }
            }
        }
    }
    return paths
}

workflow HOMES_ASSEMBLY_ILLUMINA {
    take:
    assembler

    main:
    ch_samplesheet = Channel.fromPath(params.input, checkIfExists: true)
    ch_read_files = Channel.value(homesAssemblyReadFiles(params.input))
    base_dir = file(params.input).parent.toString()

    VALIDATE_ASSEMBLY_SAMPLESHEET(ch_samplesheet, 'illumina', base_dir)
    TRIM_ASSEMBLY_READS(
        VALIDATE_ASSEMBLY_SAMPLESHEET.out.samplesheet,
        'illumina',
        ch_read_files
    )
    ASSEMBLY_READ_QC(TRIM_ASSEMBLY_READS.out.samplesheet, 'illumina', TRIM_ASSEMBLY_READS.out.reads)
    ILLUMINA_ASSEMBLY(
        TRIM_ASSEMBLY_READS.out.samplesheet,
        TRIM_ASSEMBLY_READS.out.reads,
        assembler,
        params.min_contig_len
    )
    METAGENOME_BINNING(
        ILLUMINA_ASSEMBLY.out.contigs,
        'illumina',
        params.binner,
        params.binning_min_contig_len
    )
    GENOME_FUNCTION_ANNOTATION(
        METAGENOME_BINNING.out.bins,
        ILLUMINA_ASSEMBLY.out.contigs,
        'illumina',
        params.annotation_tool
    )
    ASSEMBLY_HTML_REPORT(
        'illumina',
        TRIM_ASSEMBLY_READS.out.summary,
        ASSEMBLY_READ_QC.out.qc,
        ASSEMBLY_READ_QC.out.length_distribution,
        ASSEMBLY_READ_QC.out.qvalue_distribution,
        ILLUMINA_ASSEMBLY.out.stats,
        ILLUMINA_ASSEMBLY.out.contigs,
        METAGENOME_BINNING.out.summary,
        GENOME_FUNCTION_ANNOTATION.out.annotation_summary,
        GENOME_FUNCTION_ANNOTATION.out.functional_annotations,
        ILLUMINA_ASSEMBLY.out.command,
        file("${projectDir}/assets/homes_report_logo.svg", checkIfExists: true)
    )

    emit:
    contigs = ILLUMINA_ASSEMBLY.out.contigs
    html = ASSEMBLY_HTML_REPORT.out.html
}
