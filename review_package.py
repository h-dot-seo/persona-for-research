"""Render a compact read-only review from a validated bound scholarly package."""
import argparse
import sys
import unicodedata
from pathlib import Path

from compare_releases import checked_package
from research_workflow import apply
from strict_json import load


def display(value):
    """Escape controls so source fields cannot forge terminal lines or commands."""
    return ''.join('\\u%04x' % ord(c) if unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Zl', 'Zp') else c
                   for c in str(value))


def render(value, question, topic):
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
                         f"{display(rule['source_kind'])} {display(rule['year'])} | {display(rule['locator'])}")
            lines.append('    Limitation: ' + display(rule['limitation']))
    cards = application['reasoning_cards']
    if cards:
        lines.append('Supplied reasoning records:')
    for card in cards:
        for dimension, component in card['components'].items():
            lines.append(f"  [{display(card['evidence_stance'])}] {display(card['rule_id'])} | {display(card['paper_id'])} | "
                         f"{display(dimension)} [{display(component['claim_type'])}]: {display(component['text'])} "
                         f"({display(component['locator'])})")
    missing = application['evidence_coverage']['missing_dimensions']
    lines.append('Missing supplied records: ' + (', '.join(missing) if missing else 'none (coverage only)'))
    observation_checks = sum(r.get('evidence_verification') == 'EXACT_QUOTE_MATCH_ONLY' for r in rules)
    component_checks = sum(c.get('evidence_verification') == 'EXACT_QUOTE_MATCH_ONLY'
                           for card in cards for c in card['components'].values())
    byte_checks = sum(p.get('source_verification') == 'LOCAL_BYTES_SHA256_MATCH' for p in papers)
    lines.append(f'Recorded checks: {observation_checks} observation quote matches; '
                 f'{component_checks} component quote matches; {byte_checks} local byte checks. Not rechecked here.')
    lines.append('Boundary: curated paper records, not private thoughts or individual authorship. '
                 'Quote matches, coverage and distinct hashes do not establish semantic support, '
                 'independent publications or researcher fidelity. Renderer uses no LLM and makes no canonical update.')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--question', required=True)
    parser.add_argument('--topic', required=True)
    args = parser.parse_args()
    try:
        text = render(load(args.package), args.question, args.topic)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(text.encode('utf-8'))


if __name__ == '__main__':
    main()
