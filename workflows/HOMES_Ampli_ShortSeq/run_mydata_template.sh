#!/usr/bin/env bash
set -euo pipefail

HOMES_ROOT="/Users/kbian8/Documents/nextflow_work/HOMES"
WORK_DIR="/Users/kbian8/Documents/nextflow_work/HOMES_work/HOMES_Ampli_ShortSeq"
TMP_DIR="/Users/kbian8/Documents/nextflow_tmp"

mkdir -p "${WORK_DIR}" "${TMP_DIR}"
cd "${HOMES_ROOT}"

TMPDIR="${TMP_DIR}" \
NXF_TEMP="${TMP_DIR}" \
nextflow run nf-core/ampliseq \
  -r 2.18.0 \
  -profile docker \
  -params-file workflows/HOMES_Ampli_ShortSeq/params.mydata.template.yaml \
  -work-dir "${WORK_DIR}" \
  -resume

