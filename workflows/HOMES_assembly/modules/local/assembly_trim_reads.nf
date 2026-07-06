process TRIM_ASSEMBLY_READS {
    tag "$platform"

    publishDir "${params.outdir}/trimmed_reads", mode: params.publish_dir_mode, pattern: "trimmed_reads/*"
    publishDir "${params.outdir}/qc", mode: params.publish_dir_mode, pattern: "*.trim.summary.tsv"
    publishDir "${params.outdir}/pipeline_info", mode: params.publish_dir_mode, pattern: "samplesheet.trimmed.csv"

    input:
    path samplesheet
    val platform
    path read_files

    output:
    path "samplesheet.trimmed.csv", emit: samplesheet
    path "trimmed_reads"         , emit: reads
    path "${platform}.trim.summary.tsv", emit: summary
    path "versions.yml"          , emit: versions

    script:
    """
    homes_assembly_trim_reads.py \\
        --samplesheet ${samplesheet} \\
        --platform ${platform} \\
        --enabled '${params.trim_reads}' \\
        --adapter_1 '${params.adapter_1 ?: ''}' \\
        --adapter_2 '${params.adapter_2 ?: ''}' \\
        --min_quality ${params.min_read_quality} \\
        --min_length ${params.min_read_length} \\
        --output_samplesheet samplesheet.trimmed.csv \\
        --output_dir trimmed_reads \\
        --summary ${platform}.trim.summary.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    mkdir -p trimmed_reads
    cat > trimmed_reads/stub_${platform}.fastq <<-END_FASTQ
    @stub_${platform}
    ACGTACGTACGT
    +
    IIIIIIIIIIII
    END_FASTQ
    cat > samplesheet.trimmed.csv <<-END_SAMPLESHEET
    sample,fastq_1,fastq_2,read_layout,assembly_group
    stub_${platform},trimmed_reads/stub_${platform}.fastq,,single,default
    END_SAMPLESHEET
    cat > ${platform}.trim.summary.tsv <<-END_SUMMARY
    sample	platform	read	trim_enabled	input_reads	output_reads	input_bases	output_bases	adapter_trimmed_reads	quality_filtered_reads	length_filtered_reads
    stub_${platform}	${platform}	fastq_1	true	1	1	12	12	0	0	0
    END_SUMMARY
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
    END_VERSIONS
    """
}
