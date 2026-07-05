process VALIDATE_METAGENOMICS_SAMPLESHEET {
    tag "$platform"

    publishDir "${params.outdir}/pipeline_info", mode: params.publish_dir_mode

    input:
    path samplesheet
    val platform

    output:
    path "samplesheet.validated.csv", emit: samplesheet
    path "versions.yml"             , emit: versions

    script:
    """
    homes_metagenomics_validate_samplesheet.py \\
        --input ${samplesheet} \\
        --platform ${platform} \\
        --output samplesheet.validated.csv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cp ${samplesheet} samplesheet.validated.csv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
    END_VERSIONS
    """
}
