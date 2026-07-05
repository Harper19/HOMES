process METAGENOMICS_HTML_REPORT {
    tag "$platform"

    publishDir "${params.outdir}/report", mode: params.publish_dir_mode

    input:
    val platform
    path qc
    path taxonomy
    path abundance
    path relative_abundance

    output:
    path "HOMES_metagenomics.${platform}.report.html", emit: html
    path "versions.yml"                              , emit: versions

    script:
    """
    homes_metagenomics_report.py \\
        --platform ${platform} \\
        --qc ${qc} \\
        --taxonomy ${taxonomy} \\
        --abundance ${abundance} \\
        --relative_abundance ${relative_abundance} \\
        --output HOMES_metagenomics.${platform}.report.html

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cat > HOMES_metagenomics.${platform}.report.html <<-END_REPORT
    <!doctype html><html><head><meta charset="utf-8"><title>HOMES_metagenomics ${platform} report</title></head><body><h1>HOMES_metagenomics ${platform} report</h1><p>Stub report for QC, taxonomy, and abundance outputs.</p></body></html>
    END_REPORT

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
    END_VERSIONS
    """
}
