/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    HOMES Nanopore-only amplicon branch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { DOWNLOAD_REFERENCE } from '../modules/local/download_reference'

workflow NANOPORE_AMPLICON {

    main:
    banner = """
-\033[2m----------------------------------------------------\033[0m-
\033[0;36m   _   _  ___  __  __ _____ ____  \033[0m
\033[0;36m  | | | |/ _ \\|  \\/  | ____/ ___| \033[0m
\033[0;36m  | |_| | | | | |\\/| |  _| \\___ \\ \033[0m
\033[0;36m  |  _  | |_| | |  | | |___ ___) |\033[0m
\033[0;36m  |_| |_|\\___/|_|  |_|_____|____/ \033[0m
\033[0;35m  HOMES_amplicon ${workflow.manifest.version}\033[0m
-\033[2m----------------------------------------------------\033[0m-
"""
    log.info(params.monochrome_logs ? banner.replaceAll(/\033\[[0-9;]*m/, '') : banner)

    if ((params.platform ?: '').toString().toLowerCase() != 'nanopore') {
        error "NANOPORE_AMPLICON was called with --platform '${params.platform}'. Use --platform nanopore."
    }

    if (!params.fastq && !params.bam) {
        error "Nanopore mode requires --fastq or --bam."
    }

    if (params.fastq && params.bam) {
        error "Use only one Nanopore input mode: --fastq or --bam."
    }

    if (params.pacbio) {
        error "HOMES_amplicon long-read mode is Nanopore-only. PacBio is intentionally not supported here because error models differ."
    }

    tax_level = (params.tax_level ?: 'all').toString().toLowerCase()
    if (!['all', 'kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species', 'reference'].contains(tax_level)) {
        error "Invalid --tax_level '${params.tax_level}'. Choose one of: all, kingdom, phylum, class, order, family, genus, species, reference."
    }

    classifier = (params.classifier ?: 'none').toString().toLowerCase()
    if (!['none', 'minimap2', 'kraken2'].contains(classifier)) {
        error "Invalid --classifier '${params.classifier}'. Choose one of: none, minimap2, kraken2."
    }

    target_marker = (params.target_marker ?: '16S').toString()
    if (!['16S', '18S', 'ITS'].contains(target_marker.toUpperCase())) {
        error "Invalid --target_marker '${params.target_marker}'. Choose one of: 16S, 18S, ITS."
    }

    ch_reads = Channel.empty()
    if (params.fastq) {
        fastq_input = params.fastq.toString()
        fastq_is_dir = !fastq_input.contains('*') && java.nio.file.Files.isDirectory(java.nio.file.Paths.get(fastq_input))
        fastq_glob = fastq_is_dir ? "${fastq_input}/**/*.{fastq,fq,fastq.gz,fq.gz}" : fastq_input
        ch_reads = Channel.fromPath(fastq_glob, checkIfExists: true)
    } else {
        ch_bam = Channel.fromPath(params.bam, checkIfExists: true)
        BAM_TO_FASTQ(ch_bam)
        ch_reads = BAM_TO_FASTQ.out.fastq
    }

    ch_reads_for_qc = ch_reads
    if (params.host_reference) {
        ch_host_reference = Channel.value(file(params.host_reference, checkIfExists: true))
        HOST_REMOVAL(ch_reads, ch_host_reference)
        ch_reads_for_qc = HOST_REMOVAL.out.fastq
    }

    NANOPORE_QC(ch_reads_for_qc)

    ch_relative_abundance = Channel.empty()
    ch_diversity = Channel.empty()

    if (classifier == 'minimap2') {
        if (!params.reference) {
            error "--classifier minimap2 requires --reference."
        }
        ch_reference = Channel.value(file(params.reference, checkIfExists: true))
        MINIMAP2_ALIGN(NANOPORE_QC.out.filtered_fastq, ch_reference)
        if (params.keep_bam) {
            SAM_TO_SORTED_BAM(MINIMAP2_ALIGN.out.sam)
            IGV_SESSION(ch_reference, SAM_TO_SORTED_BAM.out.bam.collect(), SAM_TO_SORTED_BAM.out.bai.collect())
        }
        MINIMAP2_CLASSIFY(MINIMAP2_ALIGN.out.sam)
        MINIMAP2_ABUNDANCE(MINIMAP2_CLASSIFY.out.classification)
        ch_relative_abundance = MINIMAP2_ABUNDANCE.out.relative_abundance
        ch_diversity = MINIMAP2_ABUNDANCE.out.diversity
    } else if (classifier == 'kraken2') {
        if (params.kraken2_db && params.kraken2_ref_taxonomy) {
            error "Use only one Nanopore Kraken2 database mode: --kraken2_db or --kraken2_ref_taxonomy."
        }

        selected_kraken2_ref_taxonomy = params.kraken2_ref_taxonomy ?: (!params.kraken2_db ? 'silva' : null)
        if (params.kraken2_db) {
            ch_kraken2_db = Channel.value(file(params.kraken2_db, checkIfExists: true))
        } else {
            if (!params.kraken2_ref_databases || !params.kraken2_ref_databases.containsKey(selected_kraken2_ref_taxonomy)) {
                error "Kraken2 reference database '${selected_kraken2_ref_taxonomy}' not found. Available keys: ${params.kraken2_ref_databases ? params.kraken2_ref_databases.keySet().join(', ') : 'none'}"
            }
            ch_kraken2_ref_taxonomy_url = Channel.fromList(params.kraken2_ref_databases[selected_kraken2_ref_taxonomy]['file'])
            DOWNLOAD_REFERENCE(ch_kraken2_ref_taxonomy_url)
            PREPARE_NANOPORE_KRAKEN2_DB(
                selected_kraken2_ref_taxonomy.replace('=','_').replace('.','_'),
                DOWNLOAD_REFERENCE.out.db.collect()
            )
            ch_kraken2_db = PREPARE_NANOPORE_KRAKEN2_DB.out.db
        }
        KRAKEN2_CLASSIFY(NANOPORE_QC.out.filtered_fastq, ch_kraken2_db)
        if (params.bracken) {
            ch_bracken_db = params.bracken_db ? Channel.value(file(params.bracken_db, checkIfExists: true)) : ch_kraken2_db
            BRACKEN_ABUNDANCE(KRAKEN2_CLASSIFY.out.report, ch_bracken_db)
            BRACKEN_ABUNDANCE_SUMMARY(BRACKEN_ABUNDANCE.out.bracken)
            ch_relative_abundance = BRACKEN_ABUNDANCE_SUMMARY.out.relative_abundance
            ch_diversity = BRACKEN_ABUNDANCE_SUMMARY.out.diversity
        } else {
            KRAKEN2_ABUNDANCE(KRAKEN2_CLASSIFY.out.report)
            ch_relative_abundance = KRAKEN2_ABUNDANCE.out.relative_abundance
            ch_diversity = KRAKEN2_ABUNDANCE.out.diversity
        }
    } else {
        NO_TAXONOMY_REPORT(NANOPORE_QC.out.summary.collect())
        ch_relative_abundance = NO_TAXONOMY_REPORT.out.relative_abundance
        ch_diversity = NO_TAXONOMY_REPORT.out.diversity
    }

    ch_report_logo = Channel.value(file("${projectDir}/assets/homes_report_logo.svg", checkIfExists: true))
    NANOPORE_HTML_REPORT(
        NANOPORE_QC.out.summary.collect(),
        ch_relative_abundance.collect(),
        ch_diversity.collect(),
        ch_report_logo
    )
}

process BAM_TO_FASTQ {
    tag "$bam.simpleName"
    label 'process_medium'

    container 'quay.io/biocontainers/samtools:1.20--h50ea8bc_1'

    publishDir "${params.outdir}/nanopore/converted_fastq", mode: params.publish_dir_mode

    input:
    path bam

    output:
    path "${bam.simpleName}.fastq", emit: fastq

    script:
    """
    samtools fastq "$bam" > "${bam.simpleName}.fastq"
    """
}

process HOST_REMOVAL {
    tag "$reads.simpleName"
    label 'process_medium'

    container 'quay.io/biocontainers/minimap2:2.28--he4a0461_3'

    publishDir "${params.outdir}/nanopore/host_removal", mode: params.publish_dir_mode

    input:
    path reads
    path host_reference

    output:
    path "*.host_removed.fastq", emit: fastq
    path "*.host_mapped_read_ids.txt", emit: mapped_ids
    path "*.host.sam", emit: sam

    script:
    """
    minimap2 -x map-ont -a "$host_reference" "$reads" > "${reads.simpleName}.host.sam"
    awk 'BEGIN{OFS="\\t"} \$1 !~ /^@/ && \$3 != "*" {print \$1}' "${reads.simpleName}.host.sam" | sort -u > "${reads.simpleName}.host_mapped_read_ids.txt"
    homes_filter_fastq_by_read_ids.py \\
        --input "$reads" \\
        --exclude "${reads.simpleName}.host_mapped_read_ids.txt" \\
        --output "${reads.simpleName}.host_removed.fastq"
    """
}

process NANOPORE_QC {
    tag "$reads.simpleName"
    label 'process_medium'

    container 'docker.io/library/python:3.11'

    publishDir "${params.outdir}/nanopore/qc", mode: params.publish_dir_mode
    publishDir "${params.outdir}/nanopore/filtered_fastq", mode: params.publish_dir_mode, pattern: "*.filtered.fastq"

    input:
    path reads

    output:
    path "*.read_stats.tsv", emit: read_stats
    path "*.summary.tsv", emit: summary
    path "*.filtered.fastq", emit: filtered_fastq

    script:
    sample_sheet_arg = params.sample_sheet ? "--sample_sheet \"${params.sample_sheet}\"" : ''
    """
    homes_nanopore_qc.py \\
        --input "$reads" \\
        --sample "$reads.simpleName" \\
        ${sample_sheet_arg} \\
        --min_len ${params.nanopore_min_len} \\
        --max_len ${params.nanopore_max_len ?: 0} \\
        --min_read_qual ${params.min_read_qual} \\
        --out_prefix "$reads.simpleName"
    """
}

process PREPARE_NANOPORE_KRAKEN2_DB {
    tag "$ref_name"
    label 'process_single'

    container 'docker.io/library/python:3.11'

    publishDir "${params.outdir}/nanopore/reference", mode: params.publish_dir_mode

    input:
    val ref_name
    path archives

    output:
    path "${db_dir}", emit: db

    script:
    db_dir = "kraken2_${ref_name}".replaceAll(/[^A-Za-z0-9_.-]/, '_')
    archive_paths = archives instanceof List ? archives : [archives]
    archive_args = archive_paths.collect { "\"${it}\"" }.join(' ')
    """
    mkdir -p unpack "${db_dir}"

    for archive in ${archive_args}; do
        tar -xzf "\$archive" -C unpack
    done

    db_hash_path=\$(find unpack -type f -name hash.k2d -print -quit)
    if [ -z "\$db_hash_path" ]; then
        echo "Could not find hash.k2d in downloaded Kraken2 archive(s)." >&2
        exit 1
    fi

    db_path=\$(dirname "\$db_hash_path")
    cp -R "\$db_path"/. "${db_dir}/"
    test -f "${db_dir}/hash.k2d"
    """
}

process MINIMAP2_ALIGN {
    tag "$reads.simpleName"
    label 'process_medium'

    container 'quay.io/biocontainers/minimap2:2.28--he4a0461_3'

    publishDir "${params.outdir}/nanopore/minimap2", mode: params.publish_dir_mode

    input:
    path reads
    path reference

    output:
    path "*.sam", emit: sam

    script:
    """
    minimap2 -x map-ont -a "$reference" "$reads" > "${reads.simpleName}.sam"
    """
}

process MINIMAP2_CLASSIFY {
    tag "$sam.simpleName"
    label 'process_single'

    container 'docker.io/library/python:3.11'

    publishDir "${params.outdir}/nanopore/minimap2", mode: params.publish_dir_mode

    input:
    path sam

    output:
    path "*.classification.tsv", emit: classification

    script:
    sample_name = sam.simpleName
    """
    homes_minimap2_classify.py \\
        --sam "$sam" \\
        --sample "${sample_name}" \\
        --min_mapq ${params.minimap2_min_mapq} \\
        --min_identity ${params.minimap2_min_identity} \\
        --min_coverage ${params.minimap2_min_coverage} \\
        --filter_taxids "${params.minimap2_filter_taxids ?: ''}" \\
        --exclude_taxids "${params.minimap2_exclude_taxids ?: ''}" \\
        --output "${sample_name}.classification.tsv"
    """
}

process MINIMAP2_ABUNDANCE {
    tag "$classification.simpleName"
    label 'process_single'

    container 'docker.io/library/python:3.11'

    publishDir "${params.outdir}/nanopore/abundance", mode: params.publish_dir_mode

    input:
    path classification

    output:
    path "*.counts.*.tsv", emit: counts
    path "*.relative_abundance.*.tsv", emit: relative_abundance
    path "*.diversity.*.tsv", emit: diversity

    script:
    """
    homes_taxonomy_abundance.py \\
        --mode minimap2 \\
        --input "$classification" \\
        --tax_level ${params.tax_level} \\
        --abundance_threshold ${params.abundance_threshold} \\
        --out_prefix "$classification.simpleName"
    """
}

process SAM_TO_SORTED_BAM {
    tag "$sam.simpleName"
    label 'process_medium'

    container 'quay.io/biocontainers/samtools:1.20--h50ea8bc_1'

    publishDir "${params.outdir}/nanopore/minimap2_bam", mode: params.publish_dir_mode

    input:
    path sam

    output:
    path "*.sorted.bam", emit: bam
    path "*.sorted.bam.bai", emit: bai

    script:
    """
    samtools sort -@ ${task.cpus} -o "${sam.simpleName}.sorted.bam" "$sam"
    samtools index "${sam.simpleName}.sorted.bam"
    """
}

process IGV_SESSION {
    tag 'igv-session'
    label 'process_single'

    container 'docker.io/library/python:3.11'

    publishDir "${params.outdir}/nanopore/igv", mode: params.publish_dir_mode

    input:
    path reference
    path bams
    path bais

    output:
    path "igv_session.xml", emit: session

    script:
    """
    homes_make_igv_session.py \\
        --reference "$reference" \\
        --bam ${bams.join(' ')} \\
        --output igv_session.xml
    """
}

process KRAKEN2_CLASSIFY {
    tag "$reads.simpleName"
    label 'process_high'

    container 'docker.io/staphb/kraken2:2.1.3'

    publishDir "${params.outdir}/nanopore/kraken2", mode: params.publish_dir_mode

    input:
    path reads
    path kraken2_db

    output:
    path "*.kraken2.output.txt", emit: output
    path "*.kraken2.report.txt", emit: report

    script:
    """
    kraken2 \\
        --db "$kraken2_db" \\
        --threads ${task.cpus} \\
        --report "${reads.simpleName}.kraken2.report.txt" \\
        --output "${reads.simpleName}.kraken2.output.txt" \\
        "$reads"
    """
}

process KRAKEN2_ABUNDANCE {
    tag "$report.simpleName"
    label 'process_single'

    container 'docker.io/library/python:3.11'

    publishDir "${params.outdir}/nanopore/abundance", mode: params.publish_dir_mode

    input:
    path report

    output:
    path "*.counts.*.tsv", emit: counts
    path "*.relative_abundance.*.tsv", emit: relative_abundance
    path "*.diversity.*.tsv", emit: diversity

    script:
    """
    homes_taxonomy_abundance.py \\
        --mode kraken2 \\
        --input "$report" \\
        --tax_level ${params.tax_level} \\
        --abundance_threshold ${params.abundance_threshold} \\
        --out_prefix "$report.simpleName"
    """
}

process BRACKEN_ABUNDANCE {
    tag "$report.simpleName"
    label 'process_medium'

    container 'docker.io/staphb/bracken:2.9'

    publishDir "${params.outdir}/nanopore/bracken", mode: params.publish_dir_mode

    input:
    path report
    path bracken_db

    output:
    path "*.bracken.tsv", emit: bracken

    script:
    """
    bracken \\
        -d "$bracken_db" \\
        -i "$report" \\
        -o "${report.simpleName}.bracken.tsv" \\
        -r ${params.bracken_read_length} \\
        -l ${params.bracken_level}
    """
}

process BRACKEN_ABUNDANCE_SUMMARY {
    tag "$bracken.simpleName"
    label 'process_single'

    container 'docker.io/library/python:3.11'

    publishDir "${params.outdir}/nanopore/abundance", mode: params.publish_dir_mode

    input:
    path bracken

    output:
    path "*.counts.*.tsv", emit: counts
    path "*.relative_abundance.*.tsv", emit: relative_abundance
    path "*.diversity.*.tsv", emit: diversity

    script:
    """
    homes_taxonomy_abundance.py \\
        --mode bracken \\
        --input "$bracken" \\
        --tax_level ${params.tax_level} \\
        --abundance_threshold ${params.abundance_threshold} \\
        --out_prefix "$bracken.simpleName"
    """
}

process NO_TAXONOMY_REPORT {
    tag 'classification-disabled'
    label 'process_single'

    container 'docker.io/library/python:3.11'

    publishDir "${params.outdir}/nanopore", mode: params.publish_dir_mode
    publishDir "${params.outdir}/nanopore/abundance", mode: params.publish_dir_mode, pattern: "*.tsv"

    input:
    path summaries

    output:
    path "classification_not_run.txt", emit: note
    path "*.relative_abundance.*.tsv", emit: relative_abundance
    path "*.diversity.*.tsv", emit: diversity

    script:
    """
    cat > classification_not_run.txt <<'END_NOTE'
Nanopore read QC and filtering completed.
Taxonomic classification was not run because --classifier none was selected.
Use --classifier minimap2 with --reference, or --classifier kraken2 with --kraken2_db.
END_NOTE

    homes_taxonomy_abundance.py \\
        --mode none \\
        --tax_level ${params.tax_level} \\
        --out_prefix no_taxonomy
    """
}

process NANOPORE_HTML_REPORT {
    tag 'nanopore-report'
    label 'process_single'

    container 'docker.io/library/python:3.11'

    publishDir "${params.outdir}/nanopore/report", mode: params.publish_dir_mode

    input:
    path summaries
    path relative_abundance
    path diversity
    path logo

    output:
    path "homes_nanopore_report.html", emit: html

    script:
    """
    homes_nanopore_report.py \\
        --qc ${summaries.join(' ')} \\
        --relative_abundance ${relative_abundance.join(' ')} \\
        --diversity ${diversity.join(' ')} \\
        --classifier ${params.classifier ?: 'none'} \\
        --target_marker ${params.target_marker ?: '16S'} \\
        --tax_level ${params.tax_level} \\
        --top_taxa ${params.top_taxa} \\
        --logo "$logo" \\
        --output homes_nanopore_report.html
    """
}
