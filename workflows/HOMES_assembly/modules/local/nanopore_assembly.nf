process NANOPORE_ASSEMBLY {
    tag "$assembler"
    container params.nanopore_assembly_container

    publishDir "${params.outdir}/assembly", mode: params.publish_dir_mode, pattern: "*.contigs.fasta"
    publishDir "${params.outdir}/assembly", mode: params.publish_dir_mode, pattern: "*.assembly_stats.tsv"
    publishDir "${params.outdir}/pipeline_info", mode: params.publish_dir_mode, pattern: "*.assembly_command.txt"

    input:
    path samplesheet
    path read_files
    val assembler
    val min_contig_len
    val genome_size
    val flye_mode

    output:
    path "HOMES_assembly.nanopore.contigs.fasta"       , emit: contigs
    path "HOMES_assembly.nanopore.assembly_stats.tsv"  , emit: stats
    path "HOMES_assembly.nanopore.assembly_command.txt", emit: command
    path "versions.yml"                                , emit: versions

    script:
    """
    homes_assembly_run.py \\
        --samplesheet ${samplesheet} \\
        --platform nanopore \\
        --assembler ${assembler} \\
        --threads ${task.cpus} \\
        --min_contig_len ${min_contig_len} \\
        --genome_size '${genome_size}' \\
        --flye_mode ${flye_mode} \\
        --out_prefix HOMES_assembly.nanopore

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        flye: \$(command -v flye >/dev/null && flye --version 2>&1 | head -n 1 | sed 's/^/"/; s/\$/"/' || echo '"not_available"')
        python: \$(python --version | sed 's/Python //')
    END_VERSIONS
    """

    stub:
    """
    cat > HOMES_assembly.nanopore.contigs.fasta <<-END_FASTA
    >stub_nanopore_contig_1 length=1200
    ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
    END_FASTA
    cat > HOMES_assembly.nanopore.assembly_stats.tsv <<-END_STATS
    assembly	platform	assembler	contigs	total_bases	min_contig	max_contig	n50	gc_percent
    HOMES_assembly.nanopore	nanopore	${assembler}	1	40	40	40	40	50.00
    END_STATS
    echo "stub nanopore assembly" > HOMES_assembly.nanopore.assembly_command.txt
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        flye: "stub"
        python: "stub"
    END_VERSIONS
    """
}
