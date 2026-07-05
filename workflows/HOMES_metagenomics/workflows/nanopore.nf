/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    HOMES Nanopore shotgun metagenomics branch
    Long-read QC, taxonomy, abundance, and report outputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { VALIDATE_METAGENOMICS_SAMPLESHEET } from '../modules/local/validate_metagenomics_samplesheet'
include { PREPARE_METAGENOMICS_DATABASE     } from '../modules/local/prepare_metagenomics_database'
include { METAGENOMICS_NORMALIZED_TABLES    } from '../modules/local/metagenomics_normalized_tables'
include { METAGENOMICS_HTML_REPORT          } from '../modules/local/metagenomics_html_report'

def homesMetagenomicsReadFiles(samplesheet_path) {
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
                if (value) {
                    def candidate = value.contains('://') || value.startsWith('/') ? value : "${base}/${value}"
                    if (value.contains('://')) {
                        paths << file(candidate)
                    } else {
                        paths << file(candidate, checkIfExists: true)
                    }
                }
            }
        }
    }
    return paths
}

def homesMetagenomicsDatabasePreset() {
    def presets = params.database_sets ?: [:]
    def selected = presets.get(params.database_set, null)
    if (!selected && !params.database_url && !params.kraken2_db) {
        throw new IllegalArgumentException("Unknown --database_set '${params.database_set}'. Available choices: ${presets.keySet().join(', ')}")
    }
    return selected ?: [:]
}

workflow HOMES_METAGENOMICS_NANOPORE {

    main:
    ch_samplesheet = Channel.fromPath(params.input, checkIfExists: true)
    ch_read_files = Channel.fromList(homesMetagenomicsReadFiles(params.input)).collect()
    database_preset = homesMetagenomicsDatabasePreset()
    resolved_database_url = params.database_url ?: (database_preset.database ?: '')
    resolved_taxonomy_url = params.taxonomy_url ?: (database_preset.taxonomy ?: '')
    resolved_reference_url = params.reference ?: (database_preset.reference ?: '')
    resolved_ref2taxid_url = params.ref2taxid ?: (database_preset.ref2taxid ?: '')
    resolved_database_name = params.database_name ?: params.database_set

    PREPARE_METAGENOMICS_DATABASE(
        params.database_set,
        resolved_database_url,
        resolved_taxonomy_url,
        resolved_reference_url,
        resolved_ref2taxid_url,
        resolved_database_name,
        params.store_dir,
        params.kraken2_db ?: '',
        params.bracken_db ?: '',
        params.taxonomy ?: '',
        params.download_databases
    )

    VALIDATE_METAGENOMICS_SAMPLESHEET(ch_samplesheet, 'nanopore')
    METAGENOMICS_NORMALIZED_TABLES(
        VALIDATE_METAGENOMICS_SAMPLESHEET.out.samplesheet,
        'nanopore',
        ch_read_files
    )
    METAGENOMICS_HTML_REPORT(
        'nanopore',
        METAGENOMICS_NORMALIZED_TABLES.out.qc,
        METAGENOMICS_NORMALIZED_TABLES.out.taxonomy,
        METAGENOMICS_NORMALIZED_TABLES.out.abundance,
        METAGENOMICS_NORMALIZED_TABLES.out.relative_abundance
    )

    emit:
    html = METAGENOMICS_HTML_REPORT.out.html
}
