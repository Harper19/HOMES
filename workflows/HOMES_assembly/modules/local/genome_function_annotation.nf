process GENOME_FUNCTION_ANNOTATION {
    tag "$annotation_tool"
    container params.annotation_container

    publishDir "${params.outdir}/annotation", mode: params.publish_dir_mode, pattern: "annotation/*"
    publishDir "${params.outdir}/annotation", mode: params.publish_dir_mode, pattern: "*.annotation_summary.tsv"
    publishDir "${params.outdir}/annotation", mode: params.publish_dir_mode, pattern: "*.functional_gene_annotations.tsv"

    input:
    path bins
    path contigs
    val platform
    val annotation_tool

    output:
    path "annotation"                                      , emit: annotation_dir
    path "HOMES_assembly.${platform}.annotation_summary.tsv", emit: annotation_summary
    path "HOMES_assembly.${platform}.functional_gene_annotations.tsv", emit: functional_annotations
    path "versions.yml"                                    , emit: versions

    script:
    """
    homes_assembly_annotate.py \\
        --bins ${bins} \\
        --contigs ${contigs} \\
        --platform ${platform} \\
        --annotation_tool ${annotation_tool} \\
        --skip_annotation '${params.skip_annotation}' \\
        --skip_functional_annotation '${params.skip_functional_annotation}' \\
        --output_dir annotation \\
        --annotation_summary HOMES_assembly.${platform}.annotation_summary.tsv \\
        --functional_annotations HOMES_assembly.${platform}.functional_gene_annotations.tsv \\
        --threads ${task.cpus}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        prokka: \$(command -v prokka >/dev/null && prokka --version 2>&1 | head -n 1 | sed 's/^/"/; s/\$/"/' || echo '"not_available"')
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    mkdir -p annotation/HOMES_assembly.${platform}.bin.001
    cat > annotation/HOMES_assembly.${platform}.bin.001/HOMES_assembly.${platform}.bin.001.gff <<-END_GFF
    ##gff-version 3
    stub_contig	HOMES	CDS	1	30	.	+	0	ID=stub_gene_1;product=hypothetical protein
    END_GFF
    cat > HOMES_assembly.${platform}.annotation_summary.tsv <<-END_SUMMARY
    genome_id	platform	annotation_tool	genes	cds	rrna	trna	source
    HOMES_assembly.${platform}.bin.001	${platform}	${annotation_tool}	1	1	0	0	stub
    END_SUMMARY
    cat > HOMES_assembly.${platform}.functional_gene_annotations.tsv <<-END_FUNCTIONS
    genome_id	gene_id	product	ec_number	ko_id	source
    HOMES_assembly.${platform}.bin.001	stub_gene_1	hypothetical protein			stub
    END_FUNCTIONS
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        prokka: "stub"
        python: "stub"
    END_VERSIONS
    """
}
