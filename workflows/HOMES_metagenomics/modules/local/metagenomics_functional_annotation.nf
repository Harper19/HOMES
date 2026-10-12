process METAGENOMICS_FUNCTIONAL_ANNOTATION {
    tag "$platform"
    container params.functional_annotation_container

    publishDir "${params.outdir}/functional_annotation", mode: params.publish_dir_mode, pattern: "*.genes.fna"
    publishDir "${params.outdir}/functional_annotation", mode: params.publish_dir_mode, pattern: "*.proteins.faa"
    publishDir "${params.outdir}/functional_annotation", mode: params.publish_dir_mode, pattern: "*.functional_annotations.tsv"
    publishDir "${params.outdir}/functional_annotation", mode: params.publish_dir_mode, pattern: "*.functional_*.tsv"

    input:
    path contigs
    val platform
    val run_functional_annotation
    val functional_annotation_tool
    val eggnog_data_dir
    val download_functional_db

    output:
    path "HOMES_metagenomics.${platform}.genes.fna", emit: genes_fna
    path "HOMES_metagenomics.${platform}.proteins.faa", emit: proteins_faa
    path "HOMES_metagenomics.${platform}.functional_annotations.tsv", emit: annotations
    path "HOMES_metagenomics.${platform}.functional_ko_summary.tsv", emit: ko_summary
    path "HOMES_metagenomics.${platform}.functional_ec_summary.tsv", emit: ec_summary
    path "HOMES_metagenomics.${platform}.functional_pathway_summary.tsv", emit: pathway_summary
    path "eggnog_raw", emit: raw
    path "versions.yml", emit: versions

    script:
    """
    homes_metagenomics_functional_annotation.py \\
        --contigs ${contigs} \\
        --run '${run_functional_annotation}' \\
        --tool ${functional_annotation_tool} \\
        --eggnog_data_dir ${eggnog_data_dir} \\
        --download_eggnog_data '${download_functional_db}' \\
        --threads ${task.cpus} \\
        --genes_fna HOMES_metagenomics.${platform}.genes.fna \\
        --proteins_faa HOMES_metagenomics.${platform}.proteins.faa \\
        --annotations HOMES_metagenomics.${platform}.functional_annotations.tsv \\
        --ko_summary HOMES_metagenomics.${platform}.functional_ko_summary.tsv \\
        --ec_summary HOMES_metagenomics.${platform}.functional_ec_summary.tsv \\
        --pathway_summary HOMES_metagenomics.${platform}.functional_pathway_summary.tsv \\
        --raw_dir eggnog_raw

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        eggnog_mapper: \$(command -v emapper.py >/dev/null && emapper.py --version 2>/dev/null | head -n 1 | sed 's/^/"/; s/\$/"/' || echo '"not_run"')
        prodigal: \$(command -v prodigal >/dev/null && prodigal -v 2>&1 | head -n 1 | sed 's/^/"/; s/\$/"/' || echo '"not_run"')
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    mkdir -p eggnog_raw
    cat > HOMES_metagenomics.${platform}.genes.fna <<-END_GENES
    >stub_gene_1
    ATGAAATAG
    END_GENES
    cat > HOMES_metagenomics.${platform}.proteins.faa <<-END_PROTEINS
    >stub_gene_1
    MK
    END_PROTEINS
    cat > HOMES_metagenomics.${platform}.functional_annotations.tsv <<-END_ANNOTATIONS
    gene_id\tdescription\tcog_category\tgo_terms\tec_numbers\tkegg_ko\tkegg_pathways\tcazy\tsource
    stub_gene_1\tstub protein\tS\t\t\tK00001\tmap00010\t\tstub
    END_ANNOTATIONS
    cat > HOMES_metagenomics.${platform}.functional_ko_summary.tsv <<-END_KO
    kegg_ko\tannotated_genes
    K00001\t1
    END_KO
    cat > HOMES_metagenomics.${platform}.functional_ec_summary.tsv <<-END_EC
    ec_number\tannotated_genes
    END_EC
    cat > HOMES_metagenomics.${platform}.functional_pathway_summary.tsv <<-END_PATHWAY
    kegg_pathway\tannotated_genes
    map00010\t1
    END_PATHWAY
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        eggnog_mapper: "stub"
        prodigal: "stub"
        python: "stub"
    END_VERSIONS
    """
}
