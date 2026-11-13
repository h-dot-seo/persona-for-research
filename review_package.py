"""Render a compact read-only review from a validated bound scholarly package."""
from exclusive_output import add_output_argument, emit, preflight
import argparse
import json
import sys
import unicodedata
from pathlib import Path

from compare_releases import checked_package
from research_workflow import apply
from reasoning_cards import DIMENSIONS, REVIEW_FIELDS
from strict_json import load
from observation_provenance import lines as origin_lines, KEY as OBSERVATION_ORIGIN


def display(value):
    """Escape controls so source fields cannot forge terminal lines or commands."""
    return ''.join('\\u%04x' % ord(c) if unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Zl', 'Zp') else c
                   for c in str(value))


def _details(package, topic):
    """Render package-bound references, never inferred or auto-selected evidence."""
    persona = package['persona']
    lines = ['Topic-matched evidence details (not relevance ranking or method selection):',
             'Bindings: persona_payload_sha256=' + package['knowledge']['persona_payload_sha256'] +
             '; knowledge_papers_sha256=' + persona['knowledge_papers_sha256']]
    count = 0
    # Keep original observation indices: a filtered ordinal is not a usable reference.
    for paper in package['knowledge']['papers']:
        for index, observation in enumerate(paper['observations']):
            if observation['topic'].casefold() != topic.casefold():
                continue
            count += 1
            ref = dict(paper_id=paper['paper_id'], observation_index=index, dimension=None)
            lines.append('  Reference: ' + json.dumps(ref, ensure_ascii=True, sort_keys=True))
            lines.append(f"    Source: {display(paper['kind'])} {display(paper['year'])}; sha256={paper['source_sha256']}; "
                         f"recorded byte check={display(paper.get('source_verification', 'NOT_PERFORMED'))}")
            lines.append('    Observation: claim_type=' + display(observation.get('claim_type', 'operator_interpretation')) +
                         '; stance=' + display(observation.get('stance', 'support')))
            for field in ('topic', 'method', 'condition', 'limitation', 'locator'):
                lines.append('    ' + field + ': ' + display(observation[field]))
            quote = observation.get('evidence_quote')
            lines.append('    evidence_quote: ' + (display(quote) if quote is not None else '[NOT_SUPPLIED]'))
            lines.append('    recorded quote check: ' + display(observation.get('evidence_verification', 'NOT_PERFORMED')))
            if OBSERVATION_ORIGIN in observation: lines.extend(origin_lines(observation[OBSERVATION_ORIGIN], display))
            components = observation.get('reasoning', {})
            missing = [d for d in DIMENSIONS if d not in components]
            lines.append('    Missing for this observation: ' + (', '.join(missing) if missing else 'none (coverage only)'))
            for dimension in DIMENSIONS:
                if dimension not in components:
                    continue
                component = components[dimension]
                lines.append('    Component reference: ' + json.dumps(dict(ref, dimension=dimension), ensure_ascii=True, sort_keys=True))
                for field in ('claim_type', 'text', 'locator', 'evidence_quote'):
                    lines.append('      ' + field + ': ' + display(component[field]))
                lines.append('      recorded quote check: ' + display(component.get('evidence_verification', 'NOT_PERFORMED')))
                for field in REVIEW_FIELDS:
                    if field in component:
                        lines.append('      ' + field + ': ' + display(component[field]))
    if not count:
        lines.append('  No topic-matched observations. Nothing was inferred or selected.')
    lines.append('Detail boundary: exact observation-topic matching, not question relevance or a recommended method. '
                 'References are positional within these unsigned package bindings; rebuilds can invalidate them. '
                 'Publication years are supplied metadata, not a historical cutoff or intellectual influence. '
                 'Per-observation gaps are not filled by another paper. Labels are curator declarations, '
                 'not authenticated author claims; coauthored work does not establish individual ownership. '
                 'Stored quotes and annotations may be private: this output is not sanitization or rights clearance.')
    return lines


def render(value, question, topic, *, evidence_details=False, human_validation=None, split_declaration=None):
    package = checked_package(value)
    application = apply(package, question, topic)  # Ignore any saved application summary.
    rules = [r for r in package['persona']['rules'] if r['topic'].casefold() == topic.casefold()]
    paper_ids = {r['paper_id'] for r in rules}
    papers = [p for p in package['knowledge']['papers'] if p['paper_id'] in paper_ids]
    kinds = {kind: sum(p['kind'] == kind for p in papers) for kind in ('research', 'review')}
    persona = package['persona']
    lines = [f'Scholarly simulation | {display(topic)}', f'Question: {display(question)}',
             f"Package: {display(persona['author_id'])} | version={display(persona['version'])} | build={display(persona['build_id'])}",
             'Status: ' + application['status'],
             f"Evidence: {len(papers)} paper IDs (research={kinds['research']}, review={kinds['review']}); "
             f"{len({p['source_sha256'] for p in papers})} supplied source hashes"]
    for pattern in application['patterns']:
        lines.append(f"{pattern['classification']}: {display(pattern['method'])}")
        lines.append('  Condition: ' + display(pattern['condition']))
        for rule in rules:
            if (rule['method'], rule['condition']) != (pattern['method'], pattern['condition']):
                continue
            lines.append(f"  [{display(rule['stance'])}] {display(rule['rule_id'])} | {display(rule['paper_id'])} | "
                         f"{display(rule['source_kind'])} {display(rule['year'])} | {display(rule['locator'])} | "
                         f"claim_type={display(rule['claim_type'])}")
            lines.append('    Limitation: ' + display(rule['limitation']))
            if OBSERVATION_ORIGIN in rule: lines.extend(origin_lines(rule[OBSERVATION_ORIGIN], display))
    cards = application['reasoning_cards']
    if cards:
        lines.append('Supplied reasoning records:')
    for card in cards:
        for dimension, component in card['components'].items():
            lines.append(f"  [{display(card['evidence_stance'])}] {display(card['rule_id'])} | {display(card['paper_id'])} | "
                         f"{display(dimension)} [{display(component['claim_type'])}]: {display(component['text'])} "
                         f"({display(component['locator'])})" +
                         (f" [origin={display(component['origin'])}; proposed={display(component['proposed_claim_type'])}]"
                          if 'origin' in component else ''))
    missing = application['evidence_coverage']['missing_dimensions']
    lines.append('Missing supplied records: ' + (', '.join(missing) if missing else 'none (coverage only)'))
    if evidence_details:
        lines.extend(_details(package, topic))
    observation_checks = sum(r.get('evidence_verification') == 'EXACT_QUOTE_MATCH_ONLY' for r in rules)
    component_checks = sum(c.get('evidence_verification') == 'EXACT_QUOTE_MATCH_ONLY'
                           for card in cards for c in card['components'].values())
    byte_checks = sum(p.get('source_verification') == 'LOCAL_BYTES_SHA256_MATCH' for p in papers)
    lines.append(f'Recorded checks: {observation_checks} observation quote matches; '
                 f'{component_checks} component quote matches; {byte_checks} local byte checks. Not rechecked here.')
    if human_validation is not None:
        # Lazy import: human_validation reuses this module's display helper.
        from human_validation import axis, axis_lines
        lines.extend(axis_lines(axis(package['persona'], package['knowledge'], human_validation)))
    if split_declaration is not None:
        # Lazy import: split_declaration reuses this module's display helper.
        from split_declaration import status as split_status, render as split_render
        lines.append(split_render(split_status(package, record=split_declaration)).rstrip('\n'))
    lines.append('Boundary: curated paper records, not private thoughts or individual authorship. '
                 'Quote matches, coverage and distinct hashes do not establish semantic support, '
                 'independent publications or researcher fidelity. Renderer uses no LLM and makes no canonical update.')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--question', required=True)
    parser.add_argument('--topic', required=True)
    parser.add_argument('--evidence-details', action='store_true',
                        help='Include bound observation/component references, quotes and per-observation gaps')
    parser.add_argument('--human-validation', type=Path, action='append',
                        help='Detached human validation record(s) checked against this package; reported read-only')
    parser.add_argument('--split', type=Path,
                        help='Frozen private split declaration; read-only comparison, not an intake gate')
    add_output_argument(parser); args = parser.parse_args()
    preflight(parser, getattr(args, 'output', None))
    try:
        records = None
        split = None
        package = None
        if args.split:
            from split_declaration import bounded_reader, validate_declaration
            read = bounded_reader()
            split = read(args.split)
            validate_declaration(split, frozen=True)
            package = read(args.package)
            if args.human_validation:
                records = [read(path) for path in args.human_validation]
        elif args.human_validation:
            from human_validation import bounded_reader  # Lazy: human_validation imports display from this module.
            read = bounded_reader()  # Records share the 8 MiB combined input budget of check and status.
            records = [read(path) for path in args.human_validation]
        text = render(package if args.split else load(args.package), args.question, args.topic,
                      evidence_details=args.evidence_details, human_validation=records, split_declaration=split)
        if args.split:
            from split_declaration import MAX_OUTPUT_BYTES
            if len(text.encode('utf-8')) > MAX_OUTPUT_BYTES:
                raise ValueError('split review output exceeds 16 MiB')
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError, RuntimeError) as exc:
        parser.exit(1, str(exc) + '\n')
    emit(parser, text.encode('utf-8'), getattr(args, 'output', None))


if __name__ == '__main__':
    main()
