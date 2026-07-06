process METAGENOME_BINNING {
    tag "$binner"
    container params.binning_container

    publishDir "${params.outdir}/binning", mode: params.publish_dir_mode, pattern: "bins/*"
    publishDir "${params.outdir}/binning", mode: params.publish_dir_mode, pattern: "*.binning_summary.tsv"

    input:
    path contigs
    val platform
    val binner
    val min_contig_len

    output:
    path "bins"                              , emit: bins
    path "HOMES_assembly.${platform}.binning_summary.tsv", emit: summary
    path "versions.yml"                      , emit: versions

    script:
    """
    homes_assembly_binning.py \\
        --contigs ${contigs} \\
        --platform ${platform} \\
        --binner ${binner} \\
        --skip '${params.skip_binning}' \\
        --min_contig_len ${min_contig_len} \\
        --output_dir bins \\
        --summary HOMES_assembly.${platform}.binning_summary.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        metabat2: \$(command -v metabat2 >/dev/null && metabat2 --version 2>&1 | head -n 1 | sed 's/^/"/; s/\$/"/' || echo '"not_available"')
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    mkdir -p bins
    cat > bins/HOMES_assembly.${platform}.bin.001.fasta <<-END_FASTA
    >stub_${platform}_bin_001_contig_1
    ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
    END_FASTA
    cat > HOMES_assembly.${platform}.binning_summary.tsv <<-END_SUMMARY
    bin_id	platform	binner	contigs	total_bases	n50	gc_percent	source
    HOMES_assembly.${platform}.bin.001	${platform}	${binner}	1	40	40	50.00	stub
    END_SUMMARY
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        metabat2: "stub"
        python: "stub"
    END_VERSIONS
    """
}
