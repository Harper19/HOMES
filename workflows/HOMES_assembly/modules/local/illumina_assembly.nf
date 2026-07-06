process ILLUMINA_ASSEMBLY {
    tag "$assembler"
    container params.illumina_assembly_container

    publishDir "${params.outdir}/assembly", mode: params.publish_dir_mode, pattern: "*.contigs.fasta"
    publishDir "${params.outdir}/assembly", mode: params.publish_dir_mode, pattern: "*.assembly_stats.tsv"
    publishDir "${params.outdir}/pipeline_info", mode: params.publish_dir_mode, pattern: "*.assembly_command.txt"

    input:
    path samplesheet
    path read_files
    val assembler
    val min_contig_len

    output:
    path "HOMES_assembly.illumina.contigs.fasta"       , emit: contigs
    path "HOMES_assembly.illumina.assembly_stats.tsv"  , emit: stats
    path "HOMES_assembly.illumina.assembly_command.txt", emit: command
    path "versions.yml"                                , emit: versions

    script:
    """
    homes_assembly_run.py \\
        --samplesheet ${samplesheet} \\
        --platform illumina \\
        --assembler ${assembler} \\
        --threads ${task.cpus} \\
        --min_contig_len ${min_contig_len} \\
        --out_prefix HOMES_assembly.illumina

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        megahit: \$(command -v megahit >/dev/null && megahit --version 2>&1 | head -n 1 | sed 's/^/"/; s/\$/"/' || echo '"not_available"')
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cat > HOMES_assembly.illumina.contigs.fasta <<-END_FASTA
    >stub_illumina_contig_1 length=1200
    ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
    END_FASTA
    cat > HOMES_assembly.illumina.assembly_stats.tsv <<-END_STATS
    assembly	platform	assembler	contigs	total_bases	min_contig	max_contig	n50	gc_percent
    HOMES_assembly.illumina	illumina	${assembler}	1	40	40	40	40	50.00
    END_STATS
    echo "stub illumina assembly" > HOMES_assembly.illumina.assembly_command.txt
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        megahit: "stub"
        python: "stub"
    END_VERSIONS
    """
}
