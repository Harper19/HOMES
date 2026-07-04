# GitHub Workflow

## First Commit

From `/Users/kbian8/Documents/nextflow_work/HOMES`:

```bash
git init
git add README.md .gitignore commands.md nextflow.config docs workflows samplesheets scripts modules configs assets envs tests
git commit -m "Initialize HOMES microbiome workflow project"
```

Create an empty GitHub repository named `HOMES`, then connect it:

```bash
git remote add origin https://github.com/YOUR_USERNAME/HOMES.git
git branch -M main
git push -u origin main
```

## Normal Update Cycle

```bash
git status
git add FILES_YOU_CHANGED
git commit -m "Describe the change"
git push
```

## Check Before Commit

```bash
git status
git diff --cached --stat
```

Do not commit raw sequencing files, `work/`, `results/`, or reference databases.

