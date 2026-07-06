#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { HOMES_METAGENOMICS_ILLUMINA } from './workflows/illumina'
include { HOMES_METAGENOMICS_NANOPORE } from './workflows/nanopore'

workflow {

    main:
    platform = (params.platform ?: 'illumina').toString().toLowerCase()

    if (!['illumina', 'nanopore'].contains(platform)) {
        error "Invalid --platform '${params.platform}'. Choose one of: illumina, nanopore."
    }

    if (!params.input) {
        error "Missing required parameter: --input"
    }

    classifier = (params.classifier ?: 'kraken2').toString().toLowerCase()
    if (classifier != 'kraken2') {
        error "HOMES_metagenomics currently implements --classifier kraken2. The requested classifier '${params.classifier}' is not wired yet."
    }

    if (platform == 'illumina') {
        HOMES_METAGENOMICS_ILLUMINA()
    } else {
        HOMES_METAGENOMICS_NANOPORE()
    }
}
