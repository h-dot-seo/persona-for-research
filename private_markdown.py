"""Private Markdown presentation of existing reports; not a sanitizer or validator."""
import json
import string

from review_package import display

NOTICE = ('Private local review note. Not a sanitizer or sharing authorization: '
          'quotes, filenames, identifiers and human assessments may be private. '
          'Do not paste into public locations; review before sharing. Markdown '
          'renderers differ and may create automatic links; no universal rendering '
          'safety or network-isolation guarantee is made. No new assessment, '
          'scientific verdict, source authentication or approval is derived.')


def escape(value):
    """Controls become visible escapes; all ASCII punctuation is backslash escaped."""
    return ''.join('\\' + char if char in string.punctuation else char
                   for char in display(value))


def render(title, result, *, max_bytes, limit_message):
    """Format one existing result with a complete sorted, reversible JSON snapshot."""
    snapshot = json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2,
                          allow_nan=False)
    # Sorting the display as well as the snapshot removes insertion-order effects.
    normalized = json.loads(snapshot)
    lines = ['# ' + escape(title), '', escape(NOTICE), '',
             '## Existing report fields', '']
    size = sum(len((line + '\n').encode('utf-8')) for line in lines)
    def append(line):
        nonlocal size
        size += len((line + '\n').encode('utf-8'))
        if size > max_bytes:
            raise ValueError(limit_message)
        lines.append(line)
    def tree(value, depth=0):
        prefix = '  ' * depth
        if type(value) is dict:
            if not value:
                append(prefix + '- Empty object')
            for key, child in value.items():
                if type(child) in (dict, list):
                    append(prefix + '- **' + escape(key) + '**:')
                    tree(child, depth + 1)
                else:
                    append(prefix + '- **' + escape(key) + '**: ' + escape(json.dumps(child, ensure_ascii=True)))
        elif type(value) is list:
            if not value:
                append(prefix + '- Empty list')
            for index, child in enumerate(value):
                append(prefix + '- Item ' + str(index) + ':')
                tree(child, depth + 1)
        else:
            append(prefix + '- Value: ' + escape(json.dumps(value, ensure_ascii=True)))
    tree(normalized)
    append('')
    append('## Complete JSON snapshot')
    append('')
    # Every JSON line is indented, including any original backticks or HTML.
    # ensure_ascii escapes actual controls and newlines inside JSON strings.
    for line in snapshot.split('\n'):
        append('    ' + line)
    output = '\n'.join(lines) + '\n'
    if len(output.encode('utf-8')) > max_bytes:
        raise ValueError(limit_message)
    return output
