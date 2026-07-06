process METAGENOMICS_TAXONOMY_ABUNDANCE {
    tag "$platform"

    publishDir "${params.outdir}/taxonomy", mode: params.publish_dir_mode, pattern: "*.taxonomy.tsv"
    publishDir "${params.outdir}/taxonomy", mode: params.publish_dir_mode, pattern: "*.kraken2.report"
    publishDir "${params.outdir}/taxonomy", mode: params.publish_dir_mode, pattern: "*.kraken2.output"
    publishDir "${params.outdir}/abundance", mode: params.publish_dir_mode, pattern: "*.abundance.tsv"
    publishDir "${params.outdir}/abundance", mode: params.publish_dir_mode, pattern: "*.relative_abundance.tsv"
    publishDir "${params.outdir}/abundance", mode: params.publish_dir_mode, pattern: "*.bracken.tsv"
    publishDir "${params.outdir}/abundance", mode: params.publish_dir_mode, pattern: "*.bracken.report"

    input:
    path samplesheet
    val platform
    path database_info
    path read_files
    val taxonomic_rank
    val bracken
    val bracken_read_length
    val skip_taxonomy

    output:
    path "${platform}.taxonomy.tsv"           , emit: taxonomy
    path "${platform}.abundance.tsv"          , emit: abundance
    path "${platform}.relative_abundance.tsv" , emit: relative_abundance
    path "*.kraken2.report"                   , emit: kraken2_reports, optional: true
    path "*.kraken2.output"                   , emit: kraken2_outputs, optional: true
    path "*.bracken.tsv"                      , emit: bracken_tables, optional: true
    path "*.bracken.report"                   , emit: bracken_reports, optional: true
    path "versions.yml"                       , emit: versions

    script:
    """
    homes_metagenomics_taxonomy_abundance.py \\
        --samplesheet ${samplesheet} \\
        --database_info ${database_info} \\
        --platform ${platform} \\
        --taxonomic_rank '${taxonomic_rank}' \\
        --bracken '${bracken}' \\
        --bracken_read_length '${bracken_read_length}' \\
        --threads ${task.cpus} \\
        --skip_taxonomy '${skip_taxonomy}' \\
        --taxonomy ${platform}.taxonomy.tsv \\
        --abundance ${platform}.abundance.tsv \\
        --relative_abundance ${platform}.relative_abundance.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        kraken2: \$(command -v kraken2 >/dev/null && kraken2 --version 2>/dev/null | head -n 1 | sed 's/^Kraken version //; s/^/"/; s/\$/"/' || echo '"not_available"')
        bracken: \$(command -v bracken >/dev/null && bracken -v 2>&1 | head -n 1 | sed 's/^/"/; s/\$/"/' || echo '"not_available"')
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cat > ${platform}.taxonomy.tsv <<-END_TAXONOMY
    sample	classifier	rank	taxid	taxon	assigned_reads	source_report
    stub_${platform}	kraken2	species	562	Escherichia coli	80	stub.kraken2.report
    END_TAXONOMY
    cat > ${platform}.abundance.tsv <<-END_ABUNDANCE
    sample	rank	taxid	taxon	reads
    stub_${platform}	species	562	Escherichia coli	80
    END_ABUNDANCE
    cat > ${platform}.relative_abundance.tsv <<-END_REL
    sample	rank	taxid	taxon	relative_abundance
    stub_${platform}	species	562	Escherichia coli	0.8
    END_REL
    cat > stub.kraken2.report <<-END_REPORT
     80.00	80	80	S	562	Escherichia coli
    END_REPORT

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        kraken2: "stub"
        bracken: "stub"
        python: "stub"
    END_VERSIONS
    """
}
