process VALIDATE_ASSEMBLY_SAMPLESHEET {
    tag "$platform"

    publishDir "${params.outdir}/pipeline_info", mode: params.publish_dir_mode, pattern: "samplesheet.validated.csv"

    input:
    path samplesheet
    val platform
    val base_dir

    output:
    path "samplesheet.validated.csv", emit: samplesheet
    path "versions.yml"            , emit: versions

    script:
    """
    homes_assembly_validate_samplesheet.py \\
        --input ${samplesheet} \\
        --platform ${platform} \\
        --base_dir '${base_dir}' \\
        --output samplesheet.validated.csv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cat > samplesheet.validated.csv <<-END_SAMPLESHEET
    sample,fastq_1,fastq_2,read_layout,assembly_group
    stub_${platform},stub.fastq,,single,default
    END_SAMPLESHEET
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
    END_VERSIONS
    """
}
