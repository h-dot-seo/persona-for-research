"""Read-only local HTML navigation over one freshly inspected research journey."""
import html
import json
import base64
import hashlib

from persona import payload_sha256
from review_package import display
from research_journey import inspect as inspect_journey

MAX_OUTPUT_BYTES = 16 * 1024 * 1024
STYLE = '''
:root{color-scheme:light;--ink:#172e35;--muted:#4c6068;--line:#ccd7d9;--paper:#f5f7f6;--accent:#205b69;--notice:#fff3d7}
*{box-sizing:border-box}html{scroll-padding-top:7rem}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,sans-serif;overflow-wrap:anywhere}
a{color:var(--accent);text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:3px solid #b45117;outline-offset:4px}
header,main,footer{max-width:1160px;margin:auto;padding:1.5rem}header{padding-top:2rem}h1{font-size:clamp(1.7rem,4vw,2.6rem);line-height:1.2;margin:.4rem 0 1rem}h2{font-size:1.45rem;margin:0 0 1rem}h3{font-size:1.1rem;margin:.2rem 0 .8rem}
nav{position:sticky;top:0;background:#fff;border-block:1px solid var(--line);z-index:1;padding:.8rem 1rem}nav ul{max-width:1112px;margin:0 auto;padding:0;display:flex;flex-wrap:wrap;gap:.5rem 1.25rem;list-style:none}
section,article{scroll-margin-top:7rem}section{margin-bottom:2rem}article,.panel{background:#fff;border:1px solid var(--line);border-radius:.5rem;padding:1.1rem;margin:1rem 0}
.notice{background:var(--notice);border-left:5px solid #a16d1b;padding:1rem 1.2rem;margin:1rem 0}.muted{color:var(--muted)}.eyebrow{text-transform:uppercase;letter-spacing:.08em;font-size:.8rem;font-weight:750}.status{font-weight:750}
dl{margin:.4rem 0}dt{font-weight:650;margin-top:.8rem}dd{margin:.2rem 0 .6rem 1rem}blockquote{margin:1rem 0;padding:.8rem 1rem;border-left:3px solid var(--line);background:var(--paper);white-space:pre-wrap}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 ui-monospace,monospace;background:var(--paper);padding:1rem;max-width:100%}code{font-family:ui-monospace,monospace;font-size:.87em}
details{margin:.6rem 0;border-left:2px solid var(--line);padding:.35rem .8rem}summary{cursor:pointer;font-weight:650}details details{margin:.45rem 0}.tree-list{padding-left:1.25rem}.tree-list>li{margin:.4rem 0}.route-index{padding-left:1.3rem}.route-index li{margin:.65rem 0}.record-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.record-grid>div{min-width:0}.empty{font-style:italic;color:var(--muted)}.skip{position:absolute;top:-100px;left:1rem;background:white;padding:.5rem}.skip:focus{top:0;z-index:3}
@media(max-width:640px){header,main,footer{padding:1rem}.record-grid{grid-template-columns:1fr}nav{position:static}html{scroll-padding-top:1rem}section,article{scroll-margin-top:1rem}dd{margin-left:.4rem}}
@media print{body{background:#fff;font-size:10pt}header,main,footer{max-width:none;padding:.3rem}nav,.skip,.back{display:none}.panel,article{border:1px solid #999;break-inside:auto}h2,h3,summary{break-after:avoid}details::details-content{content-visibility:visible}details>*:not(summary){display:block!important}a{color:inherit;text-decoration:none}pre{font-size:8pt}section,article{scroll-margin:0}}
'''
STYLE_SHA256 = base64.b64encode(hashlib.sha256(STYLE.encode('utf-8')).digest()).decode('ascii')
CSP = ("default-src 'none'; style-src 'sha256-"+STYLE_SHA256+
       "'; base-uri 'none'; form-action 'none'; object-src 'none'; frame-src 'none'")


def _escape(value):
    return html.escape(display(value), quote=True)


def _json(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2)


def _scalar(value):
    if value is None: return '<span class="empty">NOT_SUPPLIED (null)</span>'
    if type(value) is bool: return 'true' if value else 'false'
    return _escape(value)


def _reference_label(ref):
    return str(ref['paper_id'])+' / observation '+str(ref['observation_index'])+' / '+(ref['dimension'] or 'base observation')


def _tree(value, known_refs):
    """Render data only. Keys and values never become raw markup, URLs, CSS or IDs."""
    if isinstance(value, dict):
        if set(value) == {'paper_id', 'observation_index', 'dimension'}:
            digest = payload_sha256(value)
            label = _escape(_reference_label(value))
            if digest in known_refs:
                yield '<a href="#evidence-'+digest+'" title="Same exact record; this link adds no evidence or approval">'+label+'</a>'
            else:
                yield '<span>'+label+' <span class="muted">(outside the displayed route index)</span></span>'
            return
        if not value:
            yield '<span class="empty">Empty object; no fields supplied.</span>'; return
        yield '<dl>'
        for key, item in value.items():
            yield '<dt>'+_escape(key)+'</dt><dd>'
            if isinstance(item, (dict, list)) and item:
                yield '<details><summary>'+('Object fields' if isinstance(item, dict) else 'List entries')+' ('+str(len(item))+')</summary>'
                yield from _tree(item, known_refs)
                yield '</details>'
            else: yield from _tree(item, known_refs)
            yield '</dd>'
        yield '</dl>'
    elif isinstance(value, list):
        if not value:
            yield '<span class="empty">Empty list; no entries supplied.</span>'; return
        yield '<ol class="tree-list">'
        for item in value:
            yield '<li>'; yield from _tree(item, known_refs); yield '</li>'
        yield '</ol>'
    else: yield _scalar(value)


class _Document:
    def __init__(self): self.parts = []; self.byte_count = 0
    def add(self, text):
        self.byte_count += len(text.encode('utf-8'))
        if self.byte_count > MAX_OUTPUT_BYTES: raise ValueError('HTML journey exceeds 16 MiB; narrow supplied artifacts explicitly')
        self.parts.append(text)
    def data(self, value, known_refs):
        for chunk in _tree(value, known_refs): self.add(chunk)
    def finish(self): return ''.join(self.parts)


def _format(result):
    """Internal presentation of a just-inspected result, not a cached-report verifier."""
    out = _Document(); known_refs = {row['reference_sha256'] for row in result['evidence_routes']}
    snapshot_sha = payload_sha256(result)
    out.add('<!doctype html><html lang="en"><head><meta charset="utf-8">')
    out.add('<meta name="viewport" content="width=device-width,initial-scale=1">')
    out.add('<meta http-equiv="Content-Security-Policy" content="'+_escape(CSP)+'">')
    out.add('<meta name="referrer" content="no-referrer"><title>Research journey | human review required</title>')
    out.add('<style>'+STYLE+'</style></head><body><a class="skip" href="#overview">Skip to review</a>')
    out.add('<header><p class="eyebrow">Local, read-only evidence review</p><h1>Source → method → argument</h1>')
    out.add('<p class="status">Human review required. This is not research approval.</p><p><code>'+_escape(result['status'])+'</code></p><p>'+_escape(result['question'])+'</p>')
    out.add('<p class="muted">Topic: '+_escape(result['topic'])+' · Reference year: '+str(result['reference_year'])+
        ' · Selected pattern: '+_escape(result['selected_pattern_id'])+'</p></header>')
    nav=[('overview','Verification scope'),('agenda','Review prompts'),('routes','Evidence routes'),
         ('records','Source records'),('reports','Full review histories'),('snapshot','Exact snapshot')]
    out.add('<nav aria-label="Review sections"><ul>'+''.join('<li><a href="#'+key+'">'+label+'</a></li>' for key,label in nav)+'</ul></nav><main>')
    out.add('<section id="overview"><h2>What this file does and does not establish</h2><div class="notice">')
    out.add('<p>'+_escape(result['boundary'])+'</p><p>This file is a snapshot from one inspection. Opening, navigating or printing it does not rerun source checks, save decisions, authenticate review or approve a method. Browser edits are not review artifacts.</p></div>')
    out.add('<div class="record-grid"><div class="panel"><h3>Current local source check</h3>')
    if 'source_recheck' in result:
        out.add('<p>'+_escape(result['source_recheck']['status'])+'</p><p>Selected local bytes and stored quotes were checked when this file was generated, including unused papers. Recorded historical labels remain separate. This does not establish authenticity or semantic support.</p>')
    else:
        out.add('<p class="status">NOT_PERFORMED</p><p>No source files were reread. Stored hash and quote-check labels are not fresh verification.</p>')
    out.add('</div><div class="panel"><h3>Declared review and validation</h3><p>Answer review: '+_escape(result['answer_review_status'])+'</p>')
    if 'method_application_review' in result:
        out.add('<p>Method application: '+_escape(result['method_application_review']['status'])+'</p>')
    out.add('<p>Scientific validation: NOT_PERFORMED. Human review identity: not authenticated. No model/provider call, automatic approval, scientific execution or canonical update occurs in this view.</p></div></div></section>')
    if 'local_input_file_check' in result:
        out.add('<p class="panel">Explicit input-file consistency: '+_escape(result['local_input_file_check']['status'])+
            '. This binds supplied JSON files, not approval or source authenticity. Full per-file checks appear below.</p>')
    out.add('<section id="agenda"><h2>Review prompts</h2><p>Grouped by domain, not severity. Counts are navigation aids, never confidence, readiness or completeness scores. Missing prompts do not mean sufficient evidence.</p>')
    domains = {}
    for prompt in result['review_agenda']: domains.setdefault(prompt['domain'], []).append(prompt)
    if not domains: out.add('<p class="notice">No mechanical prompts detected. Human review and scientific validation are still required.</p>')
    for domain, prompts in domains.items():
        out.add('<details><summary>'+_escape(domain)+' ('+str(len(prompts))+' prompts)</summary>')
        out.data(prompts, known_refs); out.add('</details>')
    out.add('</section><section id="routes"><h2>Exact-reference route index</h2><p>These are the supplied review routes, not a complete corpus or literature inventory. A shared reference connects records, not meanings. “Active” records only a supplied answer citation or design link use, including rejected or deferred claims; it is not accepted evidence. Application-only and context-only references remain separate.</p>')
    out.add('<ol class="route-index">')
    for row in result['evidence_routes']:
        node = row['evidence']; label = _reference_label(node['reference']); active = row['actively_used_in_answer_or_design']
        out.add('<li><a href="#evidence-'+row['reference_sha256']+'">'+_escape(label)+'</a><br><span class="muted">'+
            str(node['publication_year'])+' · '+_escape(node['source_kind'])+' · '+_escape(row['publication_scope'])+
            ' · supplied answer/design use: '+('yes' if active else 'no')+'</span></li>')
    out.add('</ol></section><section id="records"><h2>Source records and distinct uses</h2>')
    for row in result['evidence_routes']:
        node = row['evidence']; record = node['component'] if node['component'] is not None else node['observation']
        out.add('<article id="evidence-'+row['reference_sha256']+'"><h3>'+_escape(_reference_label(node['reference']))+'</h3>')
        out.add('<p>'+str(node['publication_year'])+' · '+_escape(node['source_kind'])+' · '+_escape(row['publication_scope'])+'</p>')
        out.add('<p>Attribution: '+_escape(node['attribution'])+'</p><p>Recorded source check: '+_escape(node['recorded_source_check'])+'</p>')
        out.add('<p>Selected record quote check label: '+_scalar(record.get('evidence_verification'))+'</p>')
        if 'current_source_recheck' in row:
            out.add('<p>Separate current quote check: '+_escape(row['current_source_recheck']['quote_status'])+
                '; locator: '+_escape(row['current_source_recheck']['locator_status'])+'</p>')
        else: out.add('<p>Current local quote check: NOT_PERFORMED.</p>')
        out.add('<p>Selected record locator: '+_scalar(record.get('locator'))+'</p><p><strong>Stored excerpt, not a newly verified publication quotation:</strong></p>')
        quote = record.get('evidence_quote')
        out.add('<blockquote>'+(_escape(quote) if isinstance(quote,str) and quote.strip() else 'NOT_SUPPLIED (missing or blank stored excerpt)')+'</blockquote>')
        out.add('<div class="record-grid"><div><h3>Enclosing observation</h3>')
        out.data(node['observation'], known_refs); out.add('</div><div><h3>Selected component</h3>')
        out.data(node['component'], known_refs); out.add('</div></div>')
        out.add('<details><summary>Complete source metadata and provenance</summary>'); out.data(node, known_refs); out.add('</details>')
        out.add('<details><summary>All separate roles, decisions and route uses</summary>')
        out.data({key:value for key,value in row.items() if key not in ('evidence','reference_sha256')}, known_refs)
        out.add('</details><p class="back"><a href="#routes">Back to route index</a></p></article>')
    out.add('</section><section id="reports"><h2>Full review histories and original declarations</h2><p>Expand each report to inspect all supplied fields. Imported original, reviewed and rejected proposals remain distinct. Links identify the same exact source record only; a history link does not add support or active evidence.</p>')
    sections=[('trajectory_review','Publication chronology and declared relationships'),
        ('pattern_transfer_review','Pattern, context, answer and design review'),
        ('method_application_review','Method-application intent and imported proposal history'),
        ('argument_review','Argument map, assumptions and uncited conclusions'),
        ('evidence_scope','Reader evidence scope and unused sources'),
        ('active_publication_context','Publication context for supplied active uses'),
        ('source_recheck','Current local source recheck, including unused sources'),
        ('local_input_file_check','Pinned JSON input files and per-file consistency')]
    for key, label in sections:
        if key not in result: continue
        out.add('<details><summary>'+label+'</summary>'); out.data(result[key],known_refs); out.add('</details>')
    out.add('</section><section id="snapshot"><h2>Exact structured snapshot</h2><p>All inspected fields are retained below, including fields not highlighted by this view. This is an unsigned record, not an approval certificate or a substitute for original inputs. Use the original CLI inputs to rerun validation; cached reports are not accepted as proof.</p>')
    out.add('<p>Journey input SHA-256: <code>'+result['journey_input_sha256']+'</code></p>')
    out.add('<p>Inspected snapshot SHA-256: <code id="snapshot-sha256">'+snapshot_sha+'</code></p>')
    out.add('<details><summary>Complete JSON snapshot (copyable text, no executable content)</summary><pre id="complete-json">'+html.escape(_json(result), quote=True)+'</pre></details>')
    out.add('</section></main><footer><p>Local review view only. Source text and model/operator declarations are untrusted data. No external resources or interactive decision controls are included. Keep private artifacts local; this file is not anonymized or authorized for publication.</p><p>Use the browser’s native disclosure controls and print function. Check print preview before sharing; no sharing is performed by this file.</p></footer></body></html>')
    return out.finish()


def render(package, patterns, context, links, proposal, draft, argument, publication_relations,
           pattern_id, declared_review=None, *, source_selection=None, source_root=None, method_applications=None):
    """Inspect original inputs exactly once, then render a passive detached snapshot."""
    result = inspect_journey(package, patterns, context, links, proposal, draft, argument, publication_relations,
        pattern_id, declared_review, source_selection=source_selection, source_root=source_root,
        method_applications=method_applications)
    return _format(result)
