process METAGENOMICS_NORMALIZED_TABLES {
    tag "$platform"

    publishDir "${params.outdir}/qc", mode: params.publish_dir_mode, pattern: "*.qc.summary.tsv"
    publishDir "${params.outdir}/taxonomy", mode: params.publish_dir_mode, pattern: "*.taxonomy.tsv"
    publishDir "${params.outdir}/abundance", mode: params.publish_dir_mode, pattern: "*.abundance.tsv"
    publishDir "${params.outdir}/abundance", mode: params.publish_dir_mode, pattern: "*.relative_abundance.tsv"
    publishDir "${params.outdir}/pipeline_info", mode: params.publish_dir_mode, pattern: "*.plan.tsv"

    input:
    path samplesheet
    val platform
    path read_files

    output:
    path "${platform}.qc.summary.tsv"          , emit: qc
    path "${platform}.taxonomy.tsv"            , emit: taxonomy
    path "${platform}.abundance.tsv"           , emit: abundance
    path "${platform}.relative_abundance.tsv"  , emit: relative_abundance
    path "homes_metagenomics.${platform}.plan.tsv", emit: plan
    path "versions.yml"                        , emit: versions

    script:
    """
    homes_metagenomics_tables.py \\
        --samplesheet ${samplesheet} \\
        --platform ${platform} \\
        --qc ${platform}.qc.summary.tsv \\
        --taxonomy ${platform}.taxonomy.tsv \\
        --abundance ${platform}.abundance.tsv \\
        --relative_abundance ${platform}.relative_abundance.tsv

    cat > homes_metagenomics.${platform}.plan.tsv <<-END_PLAN
    platform	analysis_design	qc	taxonomy	abundance	report
    ${platform}	${platform == 'nanopore' ? 'nanopore_long_read_metagenomics' : 'illumina_short_read_metagenomics'}	pending_real_qc_modules	pending_real_taxonomy_modules	pending_real_abundance_modules	pending_homes_html_report
    END_PLAN

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cat > ${platform}.qc.summary.tsv <<-END_QC
    sample	platform	read_layout	analysis_design	input_1	input_2	host_filtering	total_reads	analysis_ready_reads	mean_read_length	min_read_length	max_read_length	mean_read_quality
    stub_${platform}	${platform}	single	stub	stub			not_configured	100	80	1000	500	1500	12
    END_QC
    cat > ${platform}.taxonomy.tsv <<-END_TAXONOMY
    sample	classifier	rank	taxid	taxon	assigned_reads	source_report
    stub_${platform}	kraken2	species	562	Escherichia coli	80	stub
    END_TAXONOMY
    cat > ${platform}.abundance.tsv <<-END_ABUNDANCE
    sample	rank	taxid	taxon	reads
    stub_${platform}	species	562	Escherichia coli	80
    END_ABUNDANCE
    cat > ${platform}.relative_abundance.tsv <<-END_REL
    sample	rank	taxid	taxon	relative_abundance
    stub_${platform}	species	562	Escherichia coli	0.8
    END_REL
    cat > homes_metagenomics.${platform}.plan.tsv <<-END_PLAN
    platform	analysis_design	qc	taxonomy	abundance	report
    ${platform}	stub	stub	stub	stub	stub
    END_PLAN
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
    END_VERSIONS
    """
}
