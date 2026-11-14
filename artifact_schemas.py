#!/usr/bin/env python3
"""Browse descriptive artifact identifiers and evidenced workflow links, not validation schemas."""
import argparse
import json
from pathlib import Path
from strict_json import load
from review_package import display

ROOT=Path(__file__).resolve().parent
SCHEMA='persona.artifact-schema-index.v1'
MAX_OUTPUT_BYTES=16*1024*1024
BOUNDARY=('Descriptive local public-code index only, not JSON Schema, input validation, binding freshness, '
          'authenticity, permission, semantic judgment or approval. Source mentions are not producer/consumer '
          'proof. Unknown relationships remain unknown; source-reviewed and synthetic-exercised evidence '
          'are distinct. Default and opt-in versions coexist; no automatic conversion, retirement or future '
          'support-period promise is introduced. No private artifact input, network, model call or file write.')


def catalog(workflow=None):
    value=load(ROOT/'docs/artifact-schema-index.json')
    rows=value['records']
    if workflow is not None:
        if workflow not in {r['workflow'] for r in rows}:raise ValueError('unknown indexed workflow')
        rows=[r for r in rows if r['workflow']==workflow]
    return dict(schema=SCHEMA,records=rows,boundary=BOUNDARY)


def encode(result,format='json'):
    if format=='json':raw=(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    else:
        lines=[BOUNDARY]
        for row in result['records']:
            lines.extend([f"{row['workflow']} | {row['role']} | {row['variant']} | {row['schema_id'] or 'UNTAGGED'}",
                          '  category='+row['category']+'; mode='+row['mode'],
                          '  producer='+json.dumps(row['producer'],ensure_ascii=True),
                          '  consumer='+json.dumps(row['consumer'],ensure_ascii=True),
                          '  source mentions (not attribution)='+', '.join(row['source_mentions']),
                          '  '+row['note']])
        raw=('\n'.join(display(line) for line in lines)+'\n').encode('utf-8')
    if len(raw)>MAX_OUTPUT_BYTES:raise ValueError('index output exceeds 16 MiB')
    return raw


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format',choices=('json','text'),default='json')
    parser.add_argument('--workflow',help='Exact indexed workflow; no artifact path is accepted')
    args=parser.parse_args()
    try:raw=encode(catalog(args.workflow),args.format)
    except (ValueError,OSError,TypeError,KeyError,RecursionError) as exc:parser.exit(1,str(exc)+'\n')
    import sys
    sys.stdout.buffer.write(raw)


if __name__=='__main__':main()
