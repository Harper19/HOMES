# HOMES_Ampli_ShortSeq

Short-read amplicon workflow for Illumina amplicon data.

Current implementation:

```text
wrapper around nf-core/ampliseq v2.18.0
```

Run the official test:

```bash
bash workflows/HOMES_Ampli_ShortSeq/run_nfcore_test_docker.sh
```

Run real data after preparing a samplesheet:

```bash
bash workflows/HOMES_Ampli_ShortSeq/run_mydata_template.sh
```

Before using real data, edit:

```text
workflows/HOMES_Ampli_ShortSeq/params.mydata.template.yaml
workflows/HOMES_Ampli_ShortSeq/samplesheet.template.csv
```

