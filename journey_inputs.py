"""Bind explicit local JSON inputs, then rerun a research journey without rebinding changes."""
import argparse
import hashlib
import json
import os
import stat
import sys
import unicodedata
from pathlib import Path, PurePosixPath

import research_journey as journey
from corpus_files import read_source_bytes
from design_scenario import _text
from persona import payload_sha256
from review_package import display
from strict_json import loads

SELECTION_SCHEMA='persona.journey-file-selection.v1'
CARD_SCHEMA='persona.journey-input-card.v1'
REQUIRED=journey.INPUT_NAMES
OPTIONAL=('declared_review','method_applications','source_selection')
NAMES=REQUIRED+OPTIONAL
MAX_CARD_BYTES=128*1024
MAX_ARTIFACT_BYTES=8*1024*1024
MAX_OUTPUT_BYTES=16*1024*1024
BOUNDARY=('This card pins explicit local JSON files for repeatable inspection, not authenticated review '
    'or scientific approval. Byte and logical JSON matches do not validate source meaning, identity, rights '
    'or researcher fidelity. Paths are relative to the separately supplied input root. No source root, '
    'provider permission, command or automatic decision is stored. Changed files fail closed; no hash '
    'refresh, artifact migration, source discovery, provider call, input write or canonical update occurs.')


def _detach(value):
    try:raw=json.dumps(value,ensure_ascii=True,allow_nan=False).encode('utf-8')
    except (TypeError,ValueError,RecursionError) as exc:raise ValueError('input card must be finite JSON data') from exc
    if len(raw)>MAX_CARD_BYTES:raise ValueError('input selection/card exceeds 128 KiB')
    return loads(raw)


def template():
    return dict(schema=SELECTION_SCHEMA,pattern_id=None,artifacts={name:None for name in NAMES})


def _relative(value):
    if (not isinstance(value,str) or not value or len(value)>1024 or '\\' in value or ':' in value
            or any(unicodedata.category(c) in ('Cc','Cf','Cs','Zl','Zp') for c in value)):
        raise ValueError('artifact path must be a bounded portable relative JSON path without controls')
    path=PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or str(path)!=value or path.suffix.lower()!='.json':
        raise ValueError('artifact path must be canonical relative JSON inside the explicit input root')
    return value


def _digest(value):
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('artifact digests must be lowercase SHA-256 hex strings')


def _descriptor(value, *, bound):
    value=_detach(value)
    if not isinstance(value,dict) or set(value)!={'schema','pattern_id','artifacts'} or value['schema']!=(CARD_SCHEMA if bound else SELECTION_SCHEMA):
        raise ValueError('input selection/card has missing or unsupported fields')
    _text(value['pattern_id'],'pattern_id',128)
    if not isinstance(value['artifacts'],dict) or set(value['artifacts'])!=set(NAMES):
        raise ValueError('provide every named artifact slot; optional slots must be explicitly null')
    seen=set()
    for name in NAMES:
        item=value['artifacts'][name]
        if item is None:
            if name in REQUIRED:raise ValueError('required artifact path not supplied: '+name)
            continue
        if bound:
            if not isinstance(item,dict) or set(item)!={'path','bytes','raw_sha256','json_sha256'}:
                raise ValueError('bound artifact requires exactly path, bytes, raw_sha256 and json_sha256')
            if type(item['bytes']) is not int or not 0<item['bytes']<=MAX_ARTIFACT_BYTES:
                raise ValueError('bound artifact byte size must be a positive integer within 8 MiB')
            _digest(item['raw_sha256']);_digest(item['json_sha256']);path=_relative(item['path'])
        else:path=_relative(item)
        if path in seen:raise ValueError('artifact paths must be distinct across named slots')
        seen.add(path)
    if bound and sum(row['bytes'] for row in value['artifacts'].values() if row is not None)>MAX_ARTIFACT_BYTES:
        raise ValueError('bound artifact aggregate exceeds 8 MiB')
    return value


def _paths(names,root):
    """Preflight all paths and types before any artifact bytes are opened."""
    root=Path(root).absolute()
    if any(path.is_symlink() for path in (root,*root.parents)):
        raise ValueError('input root must not contain symlinks')
    requested_root=root
    root=root.resolve(strict=True)
    if root!=Path(os.path.abspath(requested_root)) or any(path.is_symlink() for path in (requested_root,*requested_root.parents)):
        raise ValueError('input root changed during preflight')
    if not root.is_dir():raise ValueError('input root must be an existing directory')
    result={}
    for name,relative in names.items():
        candidate=root.joinpath(*PurePosixPath(relative).parts)
        for path in (candidate,*candidate.parents):
            if path==root:break
            if path.is_symlink():raise ValueError('artifact paths must not contain symlinks')
        resolved=candidate.resolve(strict=True)
        if resolved!=candidate:
            raise ValueError('artifact path changed or became an alias during preflight')
        if not resolved.is_relative_to(root) or not stat.S_ISREG(resolved.stat(follow_symlinks=False).st_mode):
            raise ValueError('artifact must be a regular JSON file inside the explicit input root')
        result[name]=resolved
    return result


def _load_artifacts(descriptor,root,source_root,*,bound):
    descriptor=_descriptor(descriptor,bound=bound)
    has_sources=descriptor['artifacts']['source_selection'] is not None
    if has_sources!=(source_root is not None):
        raise ValueError('selected source-selection artifact and explicit source_root must be supplied together')
    names={name:(item['path'] if bound else item) for name,item in descriptor['artifacts'].items() if item is not None}
    paths=_paths(names,root)
    values={name:None for name in NAMES};records={name:None for name in NAMES};remaining=MAX_ARTIFACT_BYTES
    for name in NAMES:
        if name not in paths:continue
        # Reuse the regular-descriptor stability checks, with a bounded read.
        raw=read_source_bytes(paths[name],max_bytes=remaining);remaining-=len(raw)
        actual=hashlib.sha256(raw).hexdigest()
        if bound and (len(raw)!=descriptor['artifacts'][name]['bytes'] or actual!=descriptor['artifacts'][name]['raw_sha256']):
            raise ValueError('artifact bytes changed: '+name+'; preserve the card and explicitly prepare a new one after review')
        try:value=loads(raw.decode('utf-8'))
        except UnicodeError as exc:raise ValueError('artifact must be UTF-8 JSON: '+name) from exc
        logical=payload_sha256(value)
        if bound and logical!=descriptor['artifacts'][name]['json_sha256']:
            raise ValueError('artifact JSON digest does not match its card: '+name)
        values[name]=value
        records[name]=dict(path=names[name],bytes=len(raw),raw_sha256=actual,json_sha256=logical)
    args=[values[name] for name in REQUIRED]+[descriptor['pattern_id'],values['declared_review']]
    options=dict(method_applications=values['method_applications'],source_selection=values['source_selection'],source_root=source_root)
    return descriptor,records,args,options


def prepare(selection,root,*,source_root=None):
    """Validate selected current inputs and return a new detached card; never save/approve it."""
    selection,records,args,options=_load_artifacts(selection,root,source_root,bound=False)
    journey.inspect(*args,**options)
    return dict(schema=CARD_SCHEMA,pattern_id=selection['pattern_id'],artifacts=records)


def _verification(card,records):
    return dict(schema='persona.journey-input-file-check.v1',status='EXPLICIT_INPUT_FILES_MATCH_CARD_NOT_APPROVAL',
        input_card_sha256=payload_sha256(card),artifacts=records,
        input_root='EXPLICIT_CURRENT_ARGUMENT_NOT_PERSISTED',source_root='EXPLICIT_CURRENT_ARGUMENT_IF_SELECTED_NOT_PERSISTED',
        paths_discovered=False,hashes_refreshed=False,input_files_modified=False,
        authorization_scope='EXPLICIT_FILES_ONLY_NOT_STANDING_SOURCE_OR_PROVIDER_PERMISSION',boundary=BOUNDARY)


def inspect(card,root,*,source_root=None):
    card,records,args,options=_load_artifacts(card,root,source_root,bound=True)
    result=journey.inspect(*args,**options)
    result['local_input_file_check']=_verification(card,records)
    journey.encode_result(result)
    return result


def render(card,root,*,source_root=None,format='text'):
    if format not in ('json','text','html'):raise ValueError('format must be json, text or html')
    card,records,args,options=_load_artifacts(card,root,source_root,bound=True)
    checked=_verification(card,records)
    if format=='text':
        # Existing text composition performs its own one current source check.
        output=journey.render(*args,**options)+'\nExplicit local input-file check (not approval):\n'+display(json.dumps(checked,ensure_ascii=True,sort_keys=True))+'\n'
    else:
        result=journey.inspect(*args,**options);result['local_input_file_check']=checked
        journey.encode_result(result)
        if format=='json':output=journey.encode_result(result).decode('utf-8')
        else:
            from journey_html import _format
            # This result was just inspected here; no arbitrary cached-report input path exists.
            output=_format(result)
    if len(output.encode('utf-8'))>MAX_OUTPUT_BYTES:raise ValueError('bound journey output exceeds 16 MiB')
    return output


def _load_card(path):
    requested=Path(path).absolute()
    if any(part.is_symlink() for part in (requested,*requested.parents)):
        raise ValueError('selection/card path must not contain symlinks')
    # Normalize explicit dot segments only after checking their original components.
    normalized=Path(os.path.abspath(requested))
    resolved=requested.resolve(strict=True)
    if resolved!=normalized or not stat.S_ISREG(resolved.stat(follow_symlinks=False).st_mode):
        raise ValueError('selection/card must remain a regular file without aliases')
    raw=read_source_bytes(resolved,max_bytes=MAX_CARD_BYTES)
    return loads(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('template')
    for name in ('prepare','inspect'):
        command=commands.add_parser(name);command.add_argument('input',type=Path)
        command.add_argument('--input-root',type=Path,required=True);command.add_argument('--source-root',type=Path)
        if name=='inspect':command.add_argument('--format',choices=('json','text','html'),default='json')
    args=parser.parse_args()
    try:
        if args.command=='template':output=json.dumps(template(),ensure_ascii=True,indent=2)+'\n'
        elif args.command=='prepare':output=json.dumps(prepare(_load_card(args.input),args.input_root,source_root=args.source_root),ensure_ascii=True,indent=2)+'\n'
        else:output=render(_load_card(args.input),args.input_root,source_root=args.source_root,format=args.format)
        if len(output.encode('utf-8'))>MAX_OUTPUT_BYTES:raise ValueError('bound journey output exceeds 16 MiB')
    except (ValueError,OSError,KeyError,TypeError,AttributeError,RecursionError) as exc:parser.exit(1,str(exc)+'\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__=='__main__':main()
