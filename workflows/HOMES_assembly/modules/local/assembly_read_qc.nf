process ASSEMBLY_READ_QC {
    tag "$platform"

    publishDir "${params.outdir}/qc", mode: params.publish_dir_mode, pattern: "*.qc.summary.tsv"
    publishDir "${params.outdir}/qc", mode: params.publish_dir_mode, pattern: "*.length_distribution.tsv"
    publishDir "${params.outdir}/qc", mode: params.publish_dir_mode, pattern: "*.qvalue_distribution.tsv"

    input:
    path samplesheet
    val platform
    path read_files

    output:
    path "${platform}.qc.summary.tsv"          , emit: qc
    path "${platform}.length_distribution.tsv" , emit: length_distribution
    path "${platform}.qvalue_distribution.tsv" , emit: qvalue_distribution
    path "versions.yml"                        , emit: versions

    script:
    """
    homes_assembly_qc.py \\
        --samplesheet ${samplesheet} \\
        --platform ${platform} \\
        --qc ${platform}.qc.summary.tsv \\
        --length_distribution ${platform}.length_distribution.tsv \\
        --qvalue_distribution ${platform}.qvalue_distribution.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cat > ${platform}.qc.summary.tsv <<-END_QC
    sample	platform	read_layout	total_reads	total_bases	mean_read_length	min_read_length	max_read_length	n50_read_length	mean_read_quality
    stub_${platform}	${platform}	single	10	10000	1000	500	1500	1100	12
    END_QC
    cat > ${platform}.length_distribution.tsv <<-END_LEN
    sample	length_bin_start	length_bin_end	read_count	fraction
    stub_${platform}	0	499	1	0.1
    stub_${platform}	500	999	4	0.4
    stub_${platform}	1000	1499	5	0.5
    END_LEN
    cat > ${platform}.qvalue_distribution.tsv <<-END_Q
    sample	q_bin	read_count	fraction
    stub_${platform}	10	1	0.1
    stub_${platform}	12	5	0.5
    stub_${platform}	14	4	0.4
    END_Q
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
    END_VERSIONS
    """
}
