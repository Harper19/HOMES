process METAGENOMICS_NORMALIZED_TABLES {
    tag "$platform"

    publishDir "${params.outdir}/qc", mode: params.publish_dir_mode, pattern: "*.qc.summary.tsv"
    publishDir "${params.outdir}/qc", mode: params.publish_dir_mode, pattern: "*.length_distribution.tsv"
    publishDir "${params.outdir}/qc", mode: params.publish_dir_mode, pattern: "*.qvalue_distribution.tsv"
    publishDir "${params.outdir}/pipeline_info", mode: params.publish_dir_mode, pattern: "*.plan.tsv"

    input:
    path samplesheet
    val platform
    path read_files

    output:
    path "${platform}.qc.summary.tsv"          , emit: qc
    path "${platform}.length_distribution.tsv" , emit: length_distribution
    path "${platform}.qvalue_distribution.tsv" , emit: qvalue_distribution
    path "homes_metagenomics.${platform}.plan.tsv", emit: plan
    path "versions.yml"                        , emit: versions

    script:
    """
    homes_metagenomics_tables.py \\
        --samplesheet ${samplesheet} \\
        --platform ${platform} \\
        --qc ${platform}.qc.summary.tsv \\
        --length_distribution ${platform}.length_distribution.tsv \\
        --qvalue_distribution ${platform}.qvalue_distribution.tsv

    cat > homes_metagenomics.${platform}.plan.tsv <<-END_PLAN
    platform	analysis_design	qc	taxonomy	abundance	report
    ${platform}	${platform == 'nanopore' ? 'nanopore_long_read_metagenomics' : 'illumina_short_read_metagenomics'}	read_length_quality_qc	kraken2	bracken_or_kraken2_report	homes_html_report
    END_PLAN

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cat > ${platform}.qc.summary.tsv <<-END_QC
    sample	platform	read_layout	analysis_design	input_1	input_2	host_filtering	total_reads	analysis_ready_reads	mean_read_length	min_read_length	max_read_length	n50_read_length	mean_read_quality
    stub_${platform}	${platform}	single	stub	stub			not_configured	100	80	1000	500	1500	1100	12
    END_QC
    cat > ${platform}.length_distribution.tsv <<-END_LEN
    sample	length_bin_start	length_bin_end	read_count	fraction
    stub_${platform}	0	499	10	0.1
    stub_${platform}	500	999	40	0.4
    stub_${platform}	1000	1499	50	0.5
    END_LEN
    cat > ${platform}.qvalue_distribution.tsv <<-END_Q
    sample	q_bin	read_count	fraction
    stub_${platform}	10	10	0.1
    stub_${platform}	12	50	0.5
    stub_${platform}	14	40	0.4
    END_Q
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
