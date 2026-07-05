#!/usr/bin/env python3

import argparse
import html
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Create a simple IGV session file for HOMES_amplicon Nanopore BAM outputs.")
    parser.add_argument("--reference", required=True)
    parser.add_argument("--bam", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    resources = "\n".join(f'    <Resource path="{html.escape(str(Path(bam)))}"/>' for bam in args.bam)
    panels = "\n".join(
        f'      <Track attributeKey="{html.escape(str(Path(bam)))}" id="{html.escape(str(Path(bam)))}" name="{html.escape(Path(bam).name)}"/>'
        for bam in args.bam
    )
    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<Session genome="{html.escape(str(Path(args.reference)))}" version="8">
  <Resources>
{resources}
  </Resources>
  <Panel name="DataPanel">
{panels}
  </Panel>
</Session>
"""
    Path(args.output).write_text(doc)


if __name__ == "__main__":
    main()
