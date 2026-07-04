# HOMES_rD_rQ

Custom rD+rQ workflow.

Migration plan:

1. Place original R/Python/shell scripts under `scripts/rd_rq/`.
2. Remove hard-coded paths from scripts.
3. Add command-line arguments.
4. Wrap stable steps as Nextflow processes under `modules/local/`.
5. Connect rD+rQ outputs to HOMES summary reports.

