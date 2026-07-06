#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { HOMES_ASSEMBLY_ILLUMINA } from './workflows/illumina'
include { HOMES_ASSEMBLY_NANOPORE } from './workflows/nanopore'

workflow {

    main:
    platform = (params.platform ?: 'illumina').toString().toLowerCase()

    if (!['illumina', 'nanopore'].contains(platform)) {
        error "Invalid --platform '${params.platform}'. Choose one of: illumina, nanopore."
    }

    if (!params.input) {
        error "Missing required parameter: --input"
    }

    assembler = (params.assembler ?: (platform == 'illumina' ? 'megahit' : 'flye')).toString().toLowerCase()
    binner = (params.binner ?: 'metabat2').toString().toLowerCase()
    annotation_tool = (params.annotation_tool ?: 'prokka').toString().toLowerCase()

    if (platform == 'illumina' && !['megahit'].contains(assembler)) {
        error "Invalid Illumina --assembler '${assembler}'. Choose one of: megahit."
    }

    if (platform == 'nanopore' && !['flye'].contains(assembler)) {
        error "Invalid Nanopore --assembler '${assembler}'. Choose one of: flye."
    }

    if (!['metabat2', 'native'].contains(binner)) {
        error "Invalid --binner '${params.binner}'. Choose one of: metabat2, native."
    }

    if (!['prokka', 'native'].contains(annotation_tool)) {
        error "Invalid --annotation_tool '${params.annotation_tool}'. Choose one of: prokka, native."
    }

    if (platform == 'illumina') {
        HOMES_ASSEMBLY_ILLUMINA(assembler)
    } else {
        HOMES_ASSEMBLY_NANOPORE(assembler)
    }
}
