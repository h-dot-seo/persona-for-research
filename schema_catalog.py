"""Fixed manual-card completed-structure preflight, never import acceptance."""
import argparse
import json
import math
from pathlib import Path
import re
import sys
from strict_json import read_bounded, loads

ROOT = Path(__file__).resolve().parent
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
CATALOG = {
    'manual-append': ('manual-observation-card.completed.schema.json', 'curate_local.append_observation'),
    'manual-revision': ('manual-observation-revision-card.completed.schema.json', 'revise_local.revise'),
}
BOUNDARY = ('Completed structure only, not import acceptance or permission. No manifest, source bytes, '
    'freshness, quote, identity, no-op or cross-field relationship is checked. '
    'Existing Python consumers remain authoritative. Integer-valued JSON 0.0 may pass this subset '
    'while the revision API requires an exact integer. No inference, source access or external call occurs.')
KEYWORDS = {'$schema', '$id', 'title', 'description', 'type', 'properties', 'required',
    'additionalProperties', 'maxLength', 'enum', 'const', 'pattern', 'readOnly', 'minimum'}
FIELDS = set(('schema manifest_sha256 paper_id observation method condition limitation locator topic '
    'evidence_quote claim_type stance reasoning question_framing alternative_explanation evidence_standard '
    'falsification_check uncertainty text observation_index previous_observation_sha256 operator_id '
    'revision_reason new_version new_build_id').split())
PATTERNS = {r'\S', r'^[0-9a-f]{64}(?![\s\S])'}

class SchemaError(ValueError):
    """Invalid fixed deployed schema, not invalid private input."""


def validate_schema(schema):
    count = [0]
    def visit(n, depth=0):
        count[0] += 1
        if count[0] > 512 or depth > 16 or type(n) is not dict or set(n)-KEYWORDS:
            raise SchemaError('Unsupported fixed schema')
        for key in ('$schema', '$id', 'title', 'description'):
            if key in n and type(n[key]) is not str: raise SchemaError('Invalid annotation')
        if '$schema' in n and n['$schema'] != 'https://json-schema.org/draft/2020-12/schema': raise SchemaError('Unsupported dialect')
        if 'readOnly' in n and type(n['readOnly']) is not bool: raise SchemaError('Invalid annotation')
        kind = n.get('type')
        if kind not in ('object', 'string', 'integer'): raise SchemaError('Unsupported type')
        if 'enum' in n and (type(n['enum']) is not list or not n['enum'] or any(type(v) is not str for v in n['enum']) or len(set(n['enum'])) != len(n['enum'])): raise SchemaError('Unsupported enum')
        if 'const' in n and type(n['const']) is not str: raise SchemaError('Unsupported const')
        if ('enum' in n or 'const' in n) and kind != 'string': raise SchemaError('Unsupported constraint')
        if 'pattern' in n and (kind != 'string' or type(n['pattern']) is not str or n['pattern'] not in PATTERNS): raise SchemaError('Unsupported regex')
        if 'maxLength' in n and (kind != 'string' or type(n['maxLength']) is not int or n['maxLength'] < 0): raise SchemaError('Invalid maximum')
        if 'minimum' in n and (kind != 'integer' or type(n['minimum']) is not int): raise SchemaError('Invalid minimum')
        if kind == 'object':
            props = n.get('properties'); required = n.get('required')
            if type(props) is not dict or set(props)-FIELDS or type(required) is not list or any(type(k) is not str for k in required) or len(set(required)) != len(required) or not set(required)<=set(props) or n.get('additionalProperties') is not False: raise SchemaError('Invalid closed object')
            for key in sorted(props): visit(props[key], depth+1)
        elif any(k in n for k in ('properties','required','additionalProperties')): raise SchemaError('Invalid object keywords')
    visit(schema)


def load_schema(name):
    try:
        filename, _ = CATALOG[name]
        schema = loads(read_bounded(ROOT/'schemas'/filename, MAX_INPUT_BYTES))
        validate_schema(schema)
        return schema
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
        raise SchemaError('Invalid fixed schema') from exc


def check(name, value):
    return _check(name, value, load_schema(name))


def _check(name, value, schema):
    errors = []
    def error(path, code): errors.append(dict(path=list(path), code=code))
    def visit(n, v, path=()):
        kind = n['type']
        matches = (type(v) is dict if kind=='object' else type(v) is str if kind=='string' else
            type(v) is int or (type(v) is float and math.isfinite(v) and v.is_integer()))
        if not matches: error(path, 'TYPE'); return
        if 'const' in n and v != n['const']: error(path, 'CONST')
        if 'enum' in n and v not in n['enum']: error(path, 'ENUM')
        if kind == 'object':
            props=n['properties']
            for k in sorted(set(n['required'])-set(v)): error((*path,k),'MISSING_REQUIRED')
            if set(v)-set(props): error(path,'UNSUPPORTED_FIELDS')
            for k in sorted(props):
                if k in v: visit(props[k],v[k],(*path,k))
        elif kind == 'string':
            if 'maxLength' in n and len(v)>n['maxLength']: error(path,'MAX_LENGTH')
            if 'pattern' in n and re.search(n['pattern'],v) is None: error(path,'PATTERN')
        elif 'minimum' in n and v<n['minimum']: error(path,'MINIMUM')
    visit(schema,value)
    return dict(catalog=name, structurally_conforms=not errors, errors=errors,
        status='SUBSET_STRUCTURAL_CHECK_NOT_FULL_JSON_SCHEMA', import_validation='NOT_PERFORMED',
        hash_binding='NOT_CHECKED', semantic_validation='NOT_PERFORMED',
        authoritative_check=CATALOG[name][1], boundary=BOUNDARY)


def encode(value, text=False):
    # All report paths come from the fixed schema, never unknown input keys/values.
    if text:
        lines=['Completed structure preflight; not import acceptance.', BOUNDARY]
        if 'errors' in value:
            lines.extend([value['status'], 'structurally_conforms: '+str(value['structurally_conforms']).lower()])
            lines.extend('/'+'/'.join(e['path'])+': '+e['code'] for e in value['errors'])
        else: lines.extend(row['catalog'] for row in value['catalogs'])
        raw=('\n'.join(lines)+'\n').encode('ascii')
    else: raw=(json.dumps(value,ensure_ascii=True,sort_keys=True,indent=2)+'\n').encode('ascii')
    if len(raw)>MAX_OUTPUT_BYTES: raise ValueError('Output limit')
    return raw


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    listing=sub.add_parser('list'); listing.add_argument('--text',action='store_true')
    showing=sub.add_parser('show'); showing.add_argument('catalog',choices=tuple(CATALOG))
    checking=sub.add_parser('check'); checking.add_argument('catalog',choices=tuple(CATALOG)); checking.add_argument('file',type=Path); checking.add_argument('--text',action='store_true')
    a=p.parse_args()
    try:
        if a.command=='list':
            result=dict(catalogs=[dict(catalog=n,id=load_schema(n)['$id'],authoritative_check=CATALOG[n][1]) for n in CATALOG], boundary=BOUNDARY)
        elif a.command=='show': result=load_schema(a.catalog)
        else:
            schema=load_schema(a.catalog) # Validate deployment before opening private input.
            result=_check(a.catalog,loads(read_bounded(a.file,MAX_INPUT_BYTES)),schema)
        raw=encode(result,getattr(a,'text',False))
    except SchemaError: p.exit(2,'Invalid fixed catalog schema.\n')
    except (ValueError,OSError,TypeError,KeyError,RecursionError,OverflowError): p.exit(1,'Invalid structural preflight input or output.\n')
    sys.stdout.buffer.write(raw)
    if a.command=='check' and not result['structurally_conforms']: return 1
    return 0

if __name__=='__main__': sys.exit(main())
