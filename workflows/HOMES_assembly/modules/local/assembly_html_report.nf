process ASSEMBLY_HTML_REPORT {
    tag "$platform"

    publishDir "${params.outdir}/report", mode: params.publish_dir_mode

    input:
    val platform
    path trim_summary
    path qc
    path length_distribution
    path qvalue_distribution
    path assembly_stats
    path contigs
    path binning_summary
    path annotation_summary
    path functional_annotations
    path command
    path report_logo

    output:
    path "HOMES_assembly.${platform}.report.html", emit: html
    path "versions.yml"                         , emit: versions

    script:
    """
    homes_assembly_report.py \\
        --platform ${platform} \\
        --trim_summary ${trim_summary} \\
        --qc ${qc} \\
        --length_distribution ${length_distribution} \\
        --qvalue_distribution ${qvalue_distribution} \\
        --assembly_stats ${assembly_stats} \\
        --contigs ${contigs} \\
        --binning_summary ${binning_summary} \\
        --annotation_summary ${annotation_summary} \\
        --functional_annotations ${functional_annotations} \\
        --command ${command} \\
        --logo ${report_logo} \\
        --output HOMES_assembly.${platform}.report.html

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cat > HOMES_assembly.${platform}.report.html <<-END_REPORT
    <!doctype html><html><head><meta charset="utf-8"><title>HOMES_assembly ${platform} report</title></head><body><h1>HOMES_assembly ${platform} report</h1><p>Stub report for trimming, read QC, assembly, binning, genome annotation, functional gene annotation, N50, length distribution, and Q value distribution outputs.</p></body></html>
    END_REPORT
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "stub"
    END_VERSIONS
    """
}
