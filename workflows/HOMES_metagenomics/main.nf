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

    if (platform == 'illumina') {
        HOMES_METAGENOMICS_ILLUMINA()
    } else {
        HOMES_METAGENOMICS_NANOPORE()
    }
}
