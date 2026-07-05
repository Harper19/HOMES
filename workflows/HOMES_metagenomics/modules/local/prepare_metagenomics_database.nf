process PREPARE_METAGENOMICS_DATABASE {
    tag "$database_set"

    publishDir "${params.outdir}/pipeline_info", mode: params.publish_dir_mode, pattern: "database_info.tsv"

    input:
    val database_set
    val database_url
    val taxonomy_url
    val reference_url
    val ref2taxid_url
    val database_name
    val store_dir
    val kraken2_db
    val bracken_db
    val taxonomy
    val download_databases

    output:
    path "database_info.tsv", emit: database_info

    script:
    def dbUrl = database_url ?: ''
    def taxUrl = taxonomy_url ?: ''
    def refUrl = reference_url ?: ''
    def ref2taxidUrl = ref2taxid_url ?: ''
    def dbName = database_name ?: ''
    def kraken2Db = kraken2_db ?: ''
    def brackenDb = bracken_db ?: ''
    def taxonomyPath = taxonomy ?: ''
    """
    homes_metagenomics_prepare_database.py \\
        --database_set '${database_set}' \\
        --database_url '${dbUrl}' \\
        --taxonomy_url '${taxUrl}' \\
        --reference_url '${refUrl}' \\
        --ref2taxid_url '${ref2taxidUrl}' \\
        --database_name '${dbName}' \\
        --store_dir '${store_dir}' \\
        --kraken2_db '${kraken2Db}' \\
        --bracken_db '${brackenDb}' \\
        --taxonomy '${taxonomyPath}' \\
        --download_databases '${download_databases}' \\
        --output database_info.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    def status = kraken2_db ? 'provided' : (database_url || taxonomy_url ? (download_databases ? 'reused' : 'download_disabled') : 'not_configured')
    def dbPath = kraken2_db ?: (database_url ? "${store_dir}/${database_name ?: database_set}/kraken2" : '')
    def taxPath = taxonomy ?: (taxonomy_url ? "${store_dir}/${database_name ?: database_set}/taxonomy" : '')
    """
    cat > database_info.tsv <<-END_DB
    database_set	status	database_path	bracken_path	taxonomy_path	reference_url	ref2taxid_url	store_dir	database_url	taxonomy_url	message
    ${database_set}	${status}	${dbPath}	${dbPath}	${taxPath}	${reference_url ?: ''}	${ref2taxid_url ?: ''}	${store_dir}	${database_url ?: ''}	${taxonomy_url ?: ''}	stub database preparation
    END_DB

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
    END_VERSIONS
    """
}
