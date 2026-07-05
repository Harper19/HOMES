#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { AMPLISEQ                } from './workflows/ampliseq'
include { NANOPORE_AMPLICON       } from './workflows/nanopore'
include { PIPELINE_INITIALISATION } from './subworkflows/local/utils_homes_ampli_shortseq_pipeline'
include { PIPELINE_COMPLETION     } from './subworkflows/local/utils_homes_ampli_shortseq_pipeline'

workflow HOMES_AMPLICON_SHORT {

    main:
    AMPLISEQ(
        params.multiqc_config,
        params.multiqc_logo,
        params.multiqc_methods_description,
        params.outdir,
    )

    emit:
    multiqc_report = AMPLISEQ.out.multiqc_report
}

workflow {

    main:
    platform = (params.platform ?: 'short').toString().toLowerCase()

    if (!['short', 'nanopore'].contains(platform)) {
        error "Invalid --platform '${params.platform}'. Choose one of: short, nanopore."
    }

    if (platform == 'short') {
        PIPELINE_INITIALISATION(
            params.version,
            params.validate_params,
            params.monochrome_logs,
            args,
            params.outdir,
            [],
            params.help,
            params.help_full,
            params.show_hidden
        )

        HOMES_AMPLICON_SHORT()

        PIPELINE_COMPLETION(
            params.email,
            params.email_on_fail,
            params.plaintext_email,
            params.outdir,
            params.monochrome_logs,
            HOMES_AMPLICON_SHORT.out.multiqc_report
        )
    } else {
        NANOPORE_AMPLICON()
    }
}
