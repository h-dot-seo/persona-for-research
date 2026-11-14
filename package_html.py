"""Passive local HTML formatting of an inspected package overview; no command line."""
import html

from journey_html import STYLE, CSP, _escape, _scalar, _tree
from persona import payload_sha256
from package_overview import json_text

MAX_OUTPUT_BYTES = 16 * 1024 * 1024


class _Document:
    def __init__(self):
        self.parts = []
        self.size = 0

    def add(self, text):
        self.size += len(text.encode('utf-8'))
        if self.size > MAX_OUTPUT_BYTES:
            raise ValueError('HTML package overview exceeds 16 MiB')
        self.parts.append(text)

    def data(self, value, known):
        for part in _tree(value, known):
            self.add(part)


def render(result):
    """Format the inspector result, not an unvalidated package or a scientific verdict."""
    snapshot = json_text(result)
    known = {payload_sha256(ref) for ref in result['references']}
    if len(known) != len(result['references']):
        raise ValueError('duplicate package overview reference')
    doc = _Document()
    doc.add('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="'+_escape(CSP)+'">'
            '<title>Bound package overview</title><style>'+STYLE+'</style></head><body>'
            '<a class="skip" href="#main">Skip to content</a><header><h1>Bound package overview</h1>')
    doc.add('<p class="notice">'+_escape(result['boundary'])+'</p><p class="notice">'+_escape(result['privacy'])+'</p></header>')
    sections = [('identity','Identity and bindings'),('validation','Declared axes and detached records'),
                ('topics','Exact topic inventory'),('papers','Papers and observations'),
                ('coverage','Supplied coverage'),('origins','Recorded imported origins'),('snapshot','Exact JSON snapshot')]
    doc.add('<nav aria-label="Package sections"><ul>')
    for key,label in sections:
        doc.add('<li><a href="#'+key+'">'+label+'</a></li>')
    doc.add('</ul></nav><main id="main"><section id="identity"><h2>Identity and bindings</h2>')
    doc.data({k:result[k] for k in ('identity','persona_sha256','knowledge_papers_sha256')},known)
    doc.add('<p class="notice">Current local source check: '+_scalar(result['current_local_source_check'])+'</p></section>')
    doc.add('<section id="validation"><h2>Declared axes and detached records</h2>')
    doc.data({k:result[k] for k in ('validation_axis_declarations','validation_axis_boundary','mechanical_prerequisites','human_validation')},known)
    doc.add('</section><section id="topics"><h2>Exact topic inventory</h2>')
    doc.data(result['topic_inventory'],known)
    for topic in result['topic_inventory']['topics']:
        doc.add('<details><summary>'+_escape(topic['topic'])+' reference links</summary>')
        for row in topic['observation_refs']:
            doc.data(dict(paper_id=row['paper_id'],observation_index=row['observation_index'],dimension=None),known)
        doc.add('</details>')
    doc.add('</section><section id="papers"><h2>Papers and observations</h2>')
    for paper in result['papers']:
        doc.add('<article><h3>'+_escape(paper['recorded_paper']['paper_id'])+'</h3>')
        doc.data({k:paper[k] for k in ('recorded_paper','recorded_source_check')},known)
        for observation in paper['observations']:
            digest = payload_sha256(observation['reference'])
            doc.add('<section id="evidence-'+digest+'"><h4>Observation '+str(observation['reference']['observation_index'])+'</h4>')
            doc.data({k:v for k,v in observation.items() if k != 'components'},known)
            for component in observation['components']:
                digest = payload_sha256(component['reference'])
                doc.add('<section id="evidence-'+digest+'"><h5>'+_escape(component['reference']['dimension'])+'</h5>')
                doc.data(component,known)
                doc.add('</section>')
            doc.add('</section>')
        doc.add('</article>')
    doc.add('</section><section id="coverage"><h2>Supplied coverage</h2>')
    doc.data(result['coverage'],known)
    doc.add('</section><section id="origins"><h2>Recorded imported origins</h2>')
    doc.data(result['imported_observation_origins'],known)
    doc.add('</section><section id="snapshot"><h2>Exact JSON snapshot</h2><pre id="json-snapshot">'+html.escape(snapshot, quote=True)+'</pre></section></main>')
    doc.add('<footer><p>'+_escape(result['boundary'])+'</p><p>'+_escape(result['privacy'])+'</p></footer></body></html>\n')
    return ''.join(doc.parts)
