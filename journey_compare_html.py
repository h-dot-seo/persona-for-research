"""Passive HTML formatting of one fresh comparison result; no input loader or CLI."""
import html
import json
from journey_html import STYLE, CSP, _escape, _reference_label, _tree
from persona import payload_sha256

MAX_OUTPUT_BYTES=16*1024*1024
PRIVACY=('Keep this comparison local: it can contain private quotes, filenames, identifiers and declarations. '
         'It is not anonymized or cleared for sharing. Previous/current are supplied labels, not authenticated '
         'chronology. Source checks are two current reads, not historical source snapshots. '
         'Changes and prompt counts are navigation, not improvement, research approval or scientific judgments.')

class _Document:
    def __init__(self):self.parts=[];self.size=0
    def add(self,text):
        self.size+=len(text.encode('utf-8'))
        if self.size>MAX_OUTPUT_BYTES:raise ValueError('HTML journey comparison exceeds 16 MiB')
        self.parts.append(text)
    def data(self,value,known=(),prefix=''):
        if not prefix:
            # A comparison summary cannot choose an evidence side for nested references.
            self.add('<pre>'+html.escape(json.dumps(value,ensure_ascii=True,sort_keys=True,indent=2),quote=True)+'</pre>')
            return
        for chunk in _tree(value,known,anchor_prefix=prefix):self.add(chunk)
    def finish(self):return ''.join(self.parts)


def render(result):
    """Format an inspected comparison only; this function grants no validation authority."""
    snapshot=json.dumps(result,ensure_ascii=True,allow_nan=False,sort_keys=True,indent=2)+'\n'
    if len(snapshot.encode('utf-8'))>MAX_OUTPUT_BYTES:raise ValueError('HTML comparison JSON snapshot exceeds 16 MiB')
    result=json.loads(snapshot)  # Canonical object-key order, preserving every list order and value.
    reports={side:result[side+'_report'] for side in ('previous','current')}
    known={side:{row['reference_sha256'] for row in report['evidence_routes']} for side,report in reports.items()}
    for side,report in reports.items():
        refs=[payload_sha256(row['evidence']['reference']) for row in report['evidence_routes']]
        if len(refs)!=len(set(refs)) or refs!=[row['reference_sha256'] for row in report['evidence_routes']]:
            raise ValueError('comparison HTML needs unique exact route references')
    doc=_Document()
    doc.add('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="'+_escape(CSP)+'">'
        '<title>Research journey comparison | human review required</title><style>'+STYLE+'</style></head><body>'
        '<a class="skip" href="#overview">Skip to comparison</a><header><h1>Previous / current journey comparison</h1>'
        '<p class="status">Human review required. Not research approval.</p><p class="notice">'+_escape(PRIVACY)+'</p>'
        '<p>'+_escape(result['boundary'])+'</p></header>')
    sections=(('overview','Identity and context'),('artifacts','Selected file changes'),('routes','Exact-reference route changes'),
              ('declarations','Declared record changes'),('prompts','Exact prompt counts'),('evidence','Previous/current evidence'),
              ('reports','Both complete fresh reports'),('snapshot','Complete JSON snapshot'))
    doc.add('<nav aria-label="Comparison sections"><ul>')
    for key,label in sections:doc.add('<li><a href="#'+key+'">'+label+'</a></li>')
    doc.add('</ul></nav><main><section id="overview"><h2>Identity and context</h2>')
    doc.data({k:result[k] for k in ('status','declared_author_id','identity_scope','bindings','comparison_input_sha256',
        'input_card_changed','logical_journey_inputs_changed','inspected_reports_changed','context_comparison','source_recheck_scope',
        'route_scope','record_scope','summary_scope','exact_key_correspondence','prompt_count_scope')})
    doc.add('</section><section id="artifacts"><h2>Selected file changes</h2>');doc.data(result['artifact_comparison'])
    doc.add('</section><section id="routes"><h2>Exact-reference route changes</h2><p>Same exact reference is not stable semantic identity. Neither side is authoritative by position.</p>')
    if not result['exact_reference_comparison']:doc.add('<p class="empty">No supplied route comparison entries.</p>')
    for row in result['exact_reference_comparison']:
        digest=row['reference_sha256'];doc.add('<article><h3>'+_escape(_reference_label(row['reference']))+'</h3><p>')
        for side in ('previous','current'):
            if digest in known[side]:doc.add('<a href="#'+side+'-evidence-'+digest+'">'+side.title()+' exact evidence</a> ')
            else:doc.add('<span>'+side.title()+': not in supplied route union on this side.</span> ')
        doc.add('</p>');doc.data({k:v for k,v in row.items() if k!='reference'});doc.add('</article>')
    doc.add('</section><section id="declarations"><h2>Declared record changes</h2>');doc.data(result['declared_record_comparison'])
    doc.add('</section><section id="prompts"><h2>Exact prompt counts</h2><p>Counts are not scores or proof of resolution.</p>');doc.data(result['exact_prompt_comparison'])
    doc.add('</section><section id="evidence"><h2>Previous/current evidence</h2><div class="record-grid">')
    for side,report in reports.items():
        doc.add('<div><h3>'+side.title()+' supplied routes</h3>')
        if not report['evidence_routes']:doc.add('<p class="empty">No supplied evidence routes.</p>')
        for row in report['evidence_routes']:
            doc.add('<article id="'+side+'-evidence-'+row['reference_sha256']+'"><h4>'+_escape(_reference_label(row['evidence']['reference']))+'</h4>')
            doc.add('<details><summary>'+side.title()+' evidence and recorded uses</summary>')
            doc.data(row,known[side],side+'-');doc.add('</details></article>')
        doc.add('</div>')
    doc.add('</div></section><section id="reports"><h2>Both complete fresh reports</h2><div class="record-grid">')
    for side,report in reports.items():
        doc.add('<div><h3>'+side.title()+'</h3><details><summary>Complete '+side+' report, including preserved histories</summary>')
        doc.data(report,known[side],side+'-');doc.add('</details></div>')
    doc.add('</div></section><section id="snapshot"><h2>Complete JSON snapshot</h2><p>Snapshot payload sha256: <code>'+payload_sha256(result)+'</code></p>'
        '<details><summary>Exact comparison JSON including both reports</summary><pre id="json-snapshot">'+html.escape(snapshot,quote=True)+'</pre></details></section></main>')
    doc.add('<footer><p class="notice">'+_escape(PRIVACY)+'</p><p>'+_escape(result['boundary'])+'</p></footer></body></html>\n')
    return doc.finish()
