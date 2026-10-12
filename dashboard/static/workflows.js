/*
 * HOMES workflow catalogue used by the dashboard forms.
 *
 * Each field becomes one form control and, when it has a value that differs
 * from the workflow default, one `--key value` argument on the Nextflow
 * command line. Keep defaults in sync with workflows/<name>/nextflow.config.
 *
 * Field keys:
 *   key        Nextflow parameter name (without --)
 *   label      short label shown in the form
 *   help       one-sentence plain-language explanation
 *   type       text | number | path | select | bool
 *   options    for select: [value, label] pairs
 *   suggest    for text: suggested values shown as a dropdown list
 *   default    workflow default (field is omitted from the command when unchanged)
 *   platforms  only show for these platform ids
 *   advanced   hide under "Advanced options"
 *   required   must be filled for a real-data run
 *   showIf     {key: value | [values]} show only when another field matches
 *   pick       for path: "file" | "folder" | "any" (file browser mode)
 *   samplesheet  for path: the field the samplesheet builder fills in
 *   emit       always write it to the command line
 */
window.HOMES_WORKFLOWS = [
  {
    id: "HOMES_amplicon",
    title: "Amplicon",
    subtitle: "16S / 18S / ITS marker genes",
    question: "Which microbes are in my samples?",
    description:
      "Profiles microbial communities from marker-gene (amplicon) sequencing. Produces quality control, taxonomy, abundance tables, diversity summaries and a shareable HTML report.",
    figure: "HOMES_amplicon/assets/homes_report_logo.svg",
    platforms: [
      {
        id: "short",
        label: "Illumina (short reads)",
        desc: "Paired-end or single-end Illumina amplicons, denoised with DADA2.",
        test: { profile: "test_short", params: { trunclenf: 230, trunclenr: 229, skip_qiime: true } },
        samplesheet: "amplicon_short",
      },
      {
        id: "nanopore",
        label: "Oxford Nanopore (long reads)",
        desc: "Full-length Nanopore amplicons with QC, optional host removal and minimap2 / Kraken2 classification.",
        test: { profile: "nanopore_taxonomy_test", params: {} },
        samplesheet: "amplicon_nanopore",
      },
    ],
    engines: ["docker", "singularity", "apptainer", "podman", "conda"],
    fields: [
      // ---- Illumina short read
      { key: "input", label: "Samplesheet", type: "path", pick: "file", samplesheet: true, required: true, platforms: ["short"],
        help: "CSV/TSV listing each sample and its FASTQ files (columns: sample, fastq_1, fastq_2, run). Use the Samplesheet tab to make one." },
      { key: "metadata", label: "Sample metadata", type: "path", pick: "file", platforms: ["short"],
        help: "Optional TSV with extra information per sample (site, date, treatment…) used to group samples in the report." },
      { key: "FW_primer", label: "Forward primer", type: "text", required: true, platforms: ["short"],
        suggest: [["GTGYCAGCMGCCGCGGTAA", "515F (16S V4)"], ["CCTACGGGNGGCWGCAG", "341F (16S V3-V4)"], ["CTTGGTCATTTAGAGGAAGTAA", "ITS1F"]],
        help: "Forward PCR primer sequence used for library preparation; it is trimmed from the reads." },
      { key: "RV_primer", label: "Reverse primer", type: "text", required: true, platforms: ["short"],
        suggest: [["GGACTACNVGGGTWTCTAAT", "806R (16S V4)"], ["GACTACHVGGGTATCTAATCC", "785R (16S V3-V4)"], ["GCTGCGTTCTTCATCGATGC", "ITS2"]],
        help: "Reverse PCR primer sequence." },
      { key: "trunclenf", label: "Trim forward reads to (bp)", type: "number", platforms: ["short"],
        help: "Cut forward reads to this length where quality drops. Leave empty to let HOMES choose from the quality profile." },
      { key: "trunclenr", label: "Trim reverse reads to (bp)", type: "number", platforms: ["short"],
        help: "Cut reverse reads to this length. Reverse reads usually lose quality earlier than forward reads." },
      { key: "dada_ref_taxonomy", label: "Reference database", type: "text", default: "sbdi-gtdb=R11-RS232-1", platforms: ["short"],
        suggest: [["sbdi-gtdb=R11-RS232-1", "GTDB (bacteria & archaea, default)"], ["silva=138", "SILVA 138 (16S/18S)"], ["unite-fungi=10.0", "UNITE (fungal ITS)"], ["pr2=5.0.0", "PR2 (protists, 18S)"]],
        help: "Taxonomy reference used to name the sequences. Downloaded automatically on first use." },
      { key: "tax_abundance_levels", label: "Abundance table levels", type: "text", default: "all", platforms: ["short"],
        suggest: [["all", "All ranks"], ["Genus", "Genus only"], ["Family,Genus,Species", "Family, Genus, Species"]],
        help: "Which taxonomic ranks get relative-abundance tables in the report." },
      { key: "illumina_pe_its", label: "Paired-end ITS mode", type: "bool", default: false, advanced: true, platforms: ["short"],
        help: "Turn on for fungal ITS amplicons, whose length varies a lot." },
      { key: "cut_its", label: "Extract ITS region", type: "select", default: "none", advanced: true, platforms: ["short"],
        options: [["none", "No"], ["full", "Full ITS"], ["its1", "ITS1"], ["its2", "ITS2"]],
        help: "Use ITSx to keep only the ITS region before taxonomy." },
      { key: "skip_qiime", label: "Skip QIIME2", type: "bool", default: true, advanced: true, platforms: ["short"],
        help: "HOMES uses an R-native downstream path by default. Leave on unless you specifically need QIIME2 outputs." },

      // ---- Nanopore
      { key: "fastq", label: "Nanopore reads", type: "path", pick: "any", required: true, platforms: ["nanopore"],
        help: "A FASTQ file, a folder of FASTQ files (e.g. a MinKNOW fastq_pass folder) or a pattern like data/*.fastq.gz." },
      { key: "sample_sheet", label: "Barcode → sample names", type: "path", pick: "file", samplesheet: true, platforms: ["nanopore"],
        help: "Optional CSV with columns barcode,sample to give barcodes friendly sample names." },
      { key: "target_marker", label: "Marker gene", type: "select", default: "16S", platforms: ["nanopore"],
        options: [["16S", "16S (bacteria & archaea)"], ["18S", "18S (eukaryotes)"], ["ITS", "ITS (fungi)"]],
        help: "Which gene was amplified." },
      { key: "classifier", label: "Taxonomy method", type: "select", default: "minimap2", emit: true, platforms: ["nanopore"],
        options: [["minimap2", "minimap2 – align to a reference FASTA"], ["kraken2", "Kraken2 – k-mer database"], ["none", "None – QC only"]],
        help: "How reads are assigned to taxa. Choose 'None' to only check read quality." },
      { key: "reference", label: "Reference FASTA", type: "path", pick: "file", platforms: ["nanopore"], showIf: { classifier: "minimap2" }, required: true,
        help: "16S/18S/ITS reference sequences with taxonomy in the headers. No index needs to be built." },
      { key: "kraken2_ref_taxonomy", label: "Download Kraken2 database", type: "select", default: "", platforms: ["nanopore"], showIf: { classifier: "kraken2" },
        options: [["", "No – I have my own"], ["silva", "SILVA (pre-built, downloaded once)"]],
        help: "Let HOMES download a ready-made SILVA Kraken2 database, or point to your own below." },
      { key: "kraken2_db", label: "Kraken2 database folder", type: "path", pick: "folder", platforms: ["nanopore"], showIf: { classifier: "kraken2" },
        help: "Folder containing hash.k2d, opts.k2d and taxo.k2d." },
      { key: "ref_taxonomy_storage", label: "Database cache folder", type: "path", pick: "folder", platforms: ["nanopore"], showIf: { classifier: "kraken2" }, advanced: true,
        help: "Where downloaded databases are kept so later runs reuse them." },
      { key: "tax_level", label: "Report taxonomy level", type: "select", default: "all", platforms: ["nanopore"],
        options: [["all", "All levels (dropdown in report)"], ["phylum", "Phylum"], ["class", "Class"], ["order", "Order"], ["family", "Family"], ["genus", "Genus"], ["species", "Species"], ["reference", "Reference ID"]],
        help: "Taxonomic level(s) used for abundance tables." },
      { key: "host_reference", label: "Host genome to remove", type: "path", pick: "file", platforms: ["nanopore"],
        help: "Optional FASTA (e.g. human genome). Matching reads are removed before analysis." },
      { key: "nanopore_min_len", label: "Minimum read length (bp)", type: "number", default: 1000, platforms: ["nanopore"], advanced: true,
        help: "Shorter reads are discarded. ~1000 bp suits full-length 16S." },
      { key: "nanopore_max_len", label: "Maximum read length (bp)", type: "number", platforms: ["nanopore"], advanced: true,
        help: "Longer reads (chimeras, concatemers) are discarded." },
      { key: "min_read_qual", label: "Minimum read quality (Q)", type: "number", default: 8, platforms: ["nanopore"], advanced: true,
        help: "Reads with lower mean quality are discarded." },
      { key: "minimap2_min_identity", label: "Min. identity", type: "number", default: 0.0, platforms: ["nanopore"], showIf: { classifier: "minimap2" }, advanced: true,
        help: "Fraction of matching bases needed to accept an alignment (0–1). 0.8 is a good starting point." },
      { key: "minimap2_min_coverage", label: "Min. coverage", type: "number", default: 0.0, platforms: ["nanopore"], showIf: { classifier: "minimap2" }, advanced: true,
        help: "Fraction of the read that must align (0–1). 0.8 is a good starting point." },
      { key: "bracken", label: "Bracken abundance re-estimation", type: "bool", default: false, platforms: ["nanopore"], showIf: { classifier: "kraken2" }, advanced: true,
        help: "Refine Kraken2 abundances with Bracken. The database must contain Bracken files." },
      { key: "bracken_db", label: "Bracken database folder", type: "path", pick: "folder", platforms: ["nanopore"], showIf: { bracken: true }, advanced: true,
        help: "Usually the same folder as the Kraken2 database." },
      { key: "bracken_read_length", label: "Bracken read length", type: "number", default: 1500, platforms: ["nanopore"], showIf: { bracken: true }, advanced: true,
        help: "Read length the Bracken files were built for." },
      { key: "abundance_threshold", label: "Hide taxa below (fraction)", type: "number", default: 0.0, platforms: ["nanopore"], advanced: true,
        help: "E.g. 0.001 hides taxa under 0.1 % relative abundance." },
      { key: "top_taxa", label: "Taxa in bar plots", type: "number", default: 20, platforms: ["nanopore"], advanced: true,
        help: "How many of the most abundant taxa are shown individually in plots." },
    ],
  },

  {
    id: "HOMES_metagenomics",
    title: "Metagenomics",
    subtitle: "Shotgun sequencing",
    question: "Which organisms (and functions) are in my samples?",
    description:
      "Classifies shotgun metagenomic reads with Kraken2, builds abundance tables and an HTML report. Optionally annotates genes (COG / GO / EC / KEGG) from an assembly.",
    platforms: [
      {
        id: "illumina",
        label: "Illumina (short reads)",
        desc: "Paired-end or single-end shotgun reads with fastp QC.",
        test: { profile: "test_illumina", params: {} },
        samplesheet: "metagenomics",
      },
      {
        id: "nanopore",
        label: "Oxford Nanopore (long reads)",
        desc: "Nanopore shotgun reads.",
        test: { profile: "test_nanopore", params: {} },
        samplesheet: "metagenomics",
      },
    ],
    engines: ["docker", "singularity"],
    testNote:
      "Test profiles skip taxonomy and database downloads so they finish in minutes. They check that your installation works.",
    fields: [
      { key: "input", label: "Samplesheet", type: "path", pick: "file", samplesheet: true, required: true,
        help: "CSV with columns sample, fastq_1, fastq_2, read_layout, host_ref. Use the Samplesheet tab to make one." },
      { key: "database_set", label: "Kraken2 database", type: "select", default: "Standard-8", emit: true,
        options: [["Standard-8", "Standard-8 (bacteria, archaea, viruses, human – 8 GB)"], ["PlusPF-8", "PlusPF-8 (+ protozoa & fungi – 8 GB)"], ["PlusPFP-8", "PlusPFP-8 (+ plants – 8 GB)"], ["ncbi_16s_18s", "NCBI 16S/18S"], ["ncbi_16s_18s_28s_ITS", "NCBI 16S/18S/28S/ITS"], ["SILVA_138_1", "SILVA 138.1"], ["Greengenes2_plus", "Greengenes2+"]],
        help: "Pre-built database. Downloaded once into the database cache folder and reused." },
      { key: "download_databases", label: "Download database if missing", type: "bool", default: true, emit: true,
        help: "Allow HOMES to download the selected database the first time (several GB)." },
      { key: "skip_taxonomy", label: "Skip taxonomy (QC only)", type: "bool", default: false, emit: true,
        help: "Only run quality control and the report, without classification." },
      { key: "store_dir", label: "Database cache folder", type: "path", pick: "folder", default: "db",
        help: "Where downloaded databases are stored. Defaults to the db/ folder in the HOMES repository." },
      { key: "kraken2_db", label: "Use my own Kraken2 database", type: "path", pick: "folder", advanced: true,
        help: "Folder containing hash.k2d, opts.k2d, taxo.k2d. Overrides the database choice above." },
      { key: "taxonomic_rank", label: "Abundance rank", type: "select", default: "S", advanced: true,
        options: [["S", "Species"], ["G", "Genus"], ["F", "Family"], ["O", "Order"], ["C", "Class"], ["P", "Phylum"]],
        help: "Taxonomic rank used for abundance tables." },
      { key: "bracken", label: "Bracken abundance re-estimation", type: "bool", default: false, advanced: true,
        help: "Refine Kraken2 abundances with Bracken (database must include Bracken files)." },
      { key: "bracken_read_length", label: "Bracken read length", type: "number", default: 150, advanced: true, showIf: { bracken: true },
        help: "Typical read length of your data (e.g. 150 for Illumina)." },
      { key: "min_len", label: "Minimum read length (bp)", type: "number", platforms: ["nanopore"], advanced: true,
        help: "Discard shorter reads." },
      { key: "min_read_qual", label: "Minimum read quality (Q)", type: "number", platforms: ["nanopore"], advanced: true,
        help: "Discard reads with lower mean quality." },
      { key: "skip_host_filtering", label: "Skip host read removal", type: "bool", default: false, platforms: ["illumina"], advanced: true,
        help: "Keep all reads even if a host_ref is given in the samplesheet." },
      { key: "run_functional_annotation", label: "Functional profiling (genes)", type: "bool", default: false,
        help: "Annotate genes from an assembly with eggNOG-mapper and quantify them per sample. Needs ~45 GB of database." },
      { key: "functional_contigs", label: "Assembly contigs FASTA", type: "path", pick: "file", showIf: { run_functional_annotation: true }, required: true,
        help: "Contigs to annotate, e.g. the contigs from a HOMES_assembly run." },
      { key: "download_functional_db", label: "Download eggNOG database", type: "bool", default: false, showIf: { run_functional_annotation: true },
        help: "Allow downloading the eggNOG database (~45 GB) the first time." },
      { key: "eggnog_data_dir", label: "eggNOG database folder", type: "path", pick: "folder", showIf: { run_functional_annotation: true }, advanced: true,
        help: "Where the eggNOG database lives. Defaults to db/eggnog." },
    ],
  },

  {
    id: "HOMES_assembly",
    title: "Assembly & MAGs",
    subtitle: "Genomes from metagenomes",
    question: "Can I reconstruct genomes and find their genes?",
    description:
      "Assembles reads into contigs, bins them into metagenome-assembled genomes (MAGs) and annotates genes and functions. Produces assembly statistics and an HTML report.",
    platforms: [
      {
        id: "illumina",
        label: "Illumina (short reads)",
        desc: "Assembled with MEGAHIT.",
        test: { profile: "test_illumina", params: { assembler: "megahit" } },
        samplesheet: "assembly",
      },
      {
        id: "nanopore",
        label: "Oxford Nanopore (long reads)",
        desc: "Assembled with Flye in metagenome mode.",
        test: { profile: "test_nanopore", params: { assembler: "flye", genome_size: "20k" } },
        samplesheet: "assembly",
      },
    ],
    engines: ["docker", "singularity", "server_slurm", "server_pbs"],
    testNote: "Test profiles use small bundled reads and lightweight binning/annotation so they run on a laptop.",
    fields: [
      { key: "input", label: "Samplesheet", type: "path", pick: "file", samplesheet: true, required: true,
        help: "CSV with columns sample, fastq_1, fastq_2, read_layout, assembly_group. All samples are co-assembled." },
      { key: "assembler", label: "Assembler", type: "select", emit: true, platformDefault: { illumina: "megahit", nanopore: "flye" },
        options: [["megahit", "MEGAHIT (Illumina)"], ["flye", "Flye (Nanopore)"]],
        help: "Program that joins reads into contigs." },
      { key: "genome_size", label: "Estimated metagenome size", type: "text", default: "100m", platforms: ["nanopore"],
        help: "Rough total size for Flye, e.g. 100m or 1g." },
      { key: "min_contig_len", label: "Minimum contig length (bp)", type: "number", default: 1000,
        help: "Shorter contigs are dropped from the final assembly." },
      { key: "binner", label: "Binning method", type: "select", default: "metabat2",
        options: [["metabat2", "MetaBAT2 (recommended)"], ["native", "Lightweight (testing only)"]],
        help: "How contigs are grouped into genomes (bins)." },
      { key: "annotation_tool", label: "Genome annotation", type: "select", default: "prokka",
        options: [["prokka", "Prokka (recommended)"], ["native", "Lightweight (testing only)"]],
        help: "How genes are predicted and named in each bin." },
      { key: "trim_reads", label: "Trim / filter reads first", type: "bool", default: true, advanced: true,
        help: "Remove low-quality bases and short reads before assembly." },
      { key: "min_read_quality", label: "Minimum read quality (Q)", type: "number", default: 10, advanced: true, help: "" },
      { key: "min_read_length", label: "Minimum read length (bp)", type: "number", default: 50, advanced: true, help: "" },
      { key: "flye_mode", label: "Flye mode", type: "select", default: "meta", platforms: ["nanopore"], advanced: true,
        options: [["meta", "Metagenome"], ["isolate", "Single isolate genome"]], help: "" },
      { key: "skip_binning", label: "Skip binning", type: "bool", default: false, advanced: true, help: "Stop after assembly." },
      { key: "skip_annotation", label: "Skip genome annotation", type: "bool", default: false, advanced: true, help: "" },
      { key: "skip_functional_annotation", label: "Skip functional genes table", type: "bool", default: false, advanced: true, help: "" },
      { key: "server_queue", label: "Cluster queue / partition", type: "text", engines: ["server_slurm", "server_pbs"],
        help: "Name of the SLURM partition or PBS queue to submit jobs to." },
      { key: "server_cluster_options", label: "Extra scheduler options", type: "text", engines: ["server_slurm", "server_pbs"], advanced: true,
        help: "E.g. --account=myproject" },
    ],
  },
];

window.HOMES_ENGINES = {
  docker: { label: "Docker", desc: "Laptop / workstation with Docker Desktop.", tool: "docker" },
  singularity: { label: "Singularity", desc: "Shared Linux server or HPC.", tool: "singularity" },
  apptainer: { label: "Apptainer", desc: "Newer name for Singularity.", tool: "apptainer" },
  podman: { label: "Podman", desc: "Docker alternative.", tool: null },
  conda: { label: "Conda", desc: "No containers; installs software with conda.", tool: null },
  server_slurm: { label: "SLURM cluster", desc: "Submit each step as a SLURM job (uses Singularity).", tool: "sbatch" },
  server_pbs: { label: "PBS / Torque cluster", desc: "Submit each step as a PBS job (uses Singularity).", tool: "qsub" },
};

/* Samplesheet layouts for the builder. */
window.HOMES_SAMPLESHEETS = {
  amplicon_short: {
    title: "Amplicon – Illumina",
    ext: "tsv",
    columns: [
      { key: "sample", label: "sample", required: true, help: "Unique ID: starts with a letter; letters, numbers, _ only" },
      { key: "fastq_1", label: "fastq_1", required: true, path: true, help: "R1 .fastq.gz" },
      { key: "fastq_2", label: "fastq_2", path: true, help: "R2 .fastq.gz (blank for single-end)" },
      { key: "run", label: "run", help: "Sequencing run ID (optional)" },
    ],
    strictIds: true,
    gzOnly: true,
  },
  amplicon_nanopore: {
    title: "Amplicon – Nanopore barcode names",
    ext: "csv",
    columns: [
      { key: "barcode", label: "barcode", required: true, help: "e.g. barcode01" },
      { key: "sample", label: "sample", required: true, help: "Friendly sample name" },
    ],
  },
  metagenomics: {
    title: "Metagenomics",
    ext: "csv",
    columns: [
      { key: "sample", label: "sample", required: true, help: "Unique sample ID" },
      { key: "fastq_1", label: "fastq_1", required: true, path: true, help: "R1 or Nanopore FASTQ" },
      { key: "fastq_2", label: "fastq_2", path: true, help: "R2 (Illumina paired only)" },
      { key: "read_layout", label: "read_layout", required: true, options: ["paired", "single"], help: "paired / single" },
      { key: "host_ref", label: "host_ref", path: true, help: "Optional host FASTA to remove" },
    ],
  },
  assembly: {
    title: "Assembly",
    ext: "csv",
    columns: [
      { key: "sample", label: "sample", required: true, help: "Unique sample ID" },
      { key: "fastq_1", label: "fastq_1", required: true, path: true, help: "R1 or Nanopore FASTQ" },
      { key: "fastq_2", label: "fastq_2", path: true, help: "R2 (Illumina paired only)" },
      { key: "read_layout", label: "read_layout", required: true, options: ["paired", "single"], help: "paired / single" },
      { key: "assembly_group", label: "assembly_group", help: "Reserved; leave as default" , default: "default"},
    ],
  },
};
