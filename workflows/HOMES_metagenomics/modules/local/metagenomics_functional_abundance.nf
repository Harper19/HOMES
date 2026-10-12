process METAGENOMICS_FUNCTIONAL_ABUNDANCE {
    tag "$platform"
    container params.functional_mapping_container

    publishDir "${params.outdir}/functional_annotation", mode: params.publish_dir_mode, pattern: "*.functional_*abundance.tsv"

    input:
    path genes_fna
    path annotations
    path samplesheet
    val platform
    path read_files
    val run_functional_annotation
    val functional_mapping_tool

    output:
    path "HOMES_metagenomics.${platform}.functional_gene_abundance.tsv", emit: gene_abundance
    path "HOMES_metagenomics.${platform}.functional_ko_abundance.tsv", emit: ko_abundance
    path "HOMES_metagenomics.${platform}.functional_ec_abundance.tsv", emit: ec_abundance
    path "HOMES_metagenomics.${platform}.functional_pathway_abundance.tsv", emit: pathway_abundance
    path "versions.yml", emit: versions

    script:
    """
    homes_metagenomics_functional_abundance.py \\
        --samplesheet ${samplesheet} \\
        --genes ${genes_fna} \\
        --annotations ${annotations} \\
        --platform ${platform} \\
        --run '${run_functional_annotation}' \\
        --mapping_tool ${functional_mapping_tool} \\
        --gene_abundance HOMES_metagenomics.${platform}.functional_gene_abundance.tsv \\
        --ko_abundance HOMES_metagenomics.${platform}.functional_ko_abundance.tsv \\
        --ec_abundance HOMES_metagenomics.${platform}.functional_ec_abundance.tsv \\
        --pathway_abundance HOMES_metagenomics.${platform}.functional_pathway_abundance.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        minimap2: \$(command -v minimap2 >/dev/null && minimap2 --version 2>/dev/null | head -n 1 | sed 's/^/"/; s/\$/"/' || echo '"not_run"')
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cat > HOMES_metagenomics.${platform}.functional_gene_abundance.tsv <<-END_GENES
    sample\tgene_id\tmapped_reads\tsource
    stub_${platform}\tstub_gene_1\t10\tstub
    END_GENES
    cat > HOMES_metagenomics.${platform}.functional_ko_abundance.tsv <<-END_KO
    sample\tkegg_ko\tmapped_reads\tsource
    stub_${platform}\tK00001\t10\tstub
    END_KO
    cat > HOMES_metagenomics.${platform}.functional_ec_abundance.tsv <<-END_EC
    sample\tec_number\tmapped_reads\tsource
    END_EC
    cat > HOMES_metagenomics.${platform}.functional_pathway_abundance.tsv <<-END_PATHWAY
    sample\tkegg_pathway\tmapped_reads\tsource
    stub_${platform}\tmap00010\t10\tstub
    END_PATHWAY
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        minimap2: "stub"
        python: "stub"
    END_VERSIONS
    """
}
