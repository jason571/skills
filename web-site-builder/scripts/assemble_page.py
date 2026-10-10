"""Assemble persisted website content without delegating document structure to an LLM.

Standard-library only. No networking, dependency installation or publication.
The draft stays authoritative; validation failure leaves the last output unchanged.
"""
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile


class DraftError(ValueError):
    def __init__(self, message, diagnostics=None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


def source_inventory(folder, limit=64):
    """Names only, bounded, excluding private paths and symlink traversal."""
    paths = []
    for current, directories, files in os.walk(folder, followlinks=False):
        directories[:] = sorted(name for name in directories
            if not name.startswith('.') and not (Path(current)/name).is_symlink())
        for name in sorted(files):
            path = Path(current)/name
            if name.startswith('.') or path.is_symlink() or path.suffix.lower() not in {'.html', '.css', '.js'}:
                continue
            if len(paths) >= limit:
                return paths, True
            paths.append(path.relative_to(folder).as_posix())
    return paths, False


def text(value, pointer, *, required=False):
    if not isinstance(value, str) or (required and not value.strip()):
        raise DraftError(f'{pointer}: expected {"nonempty " if required else ""}string')
    return value


class Inspect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.refs, self.languages, self.controls = [], [], set(), set()
        self.roots, self.forbidden = [], []

    def handle_decl(self, value):
        self.forbidden.append('doctype')

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {'html', 'head', 'body', 'main'}:
            self.roots.append(tag)
        if tag == 'script':
            self.forbidden.append(tag)
        if 'id' in values:
            self.ids.append(values['id'])
        if values.get('href', '').startswith('#') and values['href'] != '#':
            self.refs.append(values['href'][1:])
        for attr in ('aria-labelledby', 'aria-controls'):
            self.refs.extend(values.get(attr, '').split())
        if 'data-copylang' in values:
            self.languages.add(values['data-copylang'])
        if tag == 'button' and 'data-setlang' in values:
            if values.get('type') != 'button':
                raise DraftError('language buttons require type="button"')
            self.controls.add(values['data-setlang'])

    def handle_endtag(self, tag):
        if tag in {'html', 'head', 'body', 'main'}:
            self.roots.append('/'+tag)


LANGUAGE_SCRIPT = """document.addEventListener('DOMContentLoaded',()=>{
const root=document.documentElement,buttons=[...document.querySelectorAll('button[data-setlang]')],copies=[...document.querySelectorAll('[data-copylang]')],initial=root.dataset.lang;
const choose=lang=>{root.dataset.lang=root.lang=lang;buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.setlang===lang)));copies.forEach(e=>{e.hidden=e.dataset.copylang!==lang})};
buttons.forEach(b=>b.addEventListener('click',()=>choose(b.dataset.setlang)));choose(initial);
try{for(const b of buttons){b.click();const lang=b.dataset.setlang;if(root.lang!==lang||b.getAttribute('aria-pressed')!=='true'||!copies.some(e=>e.dataset.copylang===lang&&!e.hidden)||copies.some(e=>e.hidden!==(e.dataset.copylang!==lang)))throw Error('language click failed')}}finally{choose(initial)}
});"""


def build(draft_path, output_path):
    draft_path, output_path = Path(draft_path), Path(output_path)
    if draft_path.resolve() == output_path.resolve():
        raise DraftError('output must not replace its source draft')
    data = json.loads(draft_path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise DraftError('/: expected a native JSON object')
    unknown = set(data) - {'title', 'language', 'description', 'css', 'css_file', 'parts', 'javascript', 'javascript_file', 'languages'}
    if unknown:
        raise DraftError('/: unexpected fields '+', '.join(sorted(unknown)))
    title = text(data.get('title'), '/title', required=True)
    language = text(data.get('language', 'zh'), '/language', required=True)
    if not re.fullmatch(r'[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{1,8})*', language):
        raise DraftError('/language: invalid language code')
    def source_path(name, pointer):
        name = text(name, pointer, required=True)
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            raise DraftError(pointer+': source path must stay inside the draft directory')
        source = (draft_path.parent/path).resolve()
        if not source.is_relative_to(draft_path.parent.resolve()):
            raise DraftError(pointer+': source symlink escapes the draft directory')
        if source == output_path.resolve():
            raise DraftError(pointer+': output must not overwrite an authored source')
        return source

    parts = data.get('parts')
    if not isinstance(parts, list) or not parts:
        raise DraftError('/parts: expected a nonempty native array')
    references = []
    for name in ('css', 'javascript'):
        if name in data and name+'_file' in data:
            raise DraftError('/'+name+': choose inline source OR a file, not both')
        if name+'_file' in data:
            references.append(('/'+name+'_file', data[name+'_file']))
    for index, part in enumerate(parts):
        pointer = f'/parts/{index}'
        if not isinstance(part, dict) or set(part) not in ({'id', 'html'}, {'id', 'file'}):
            raise DraftError(pointer+': fields must be id and either html or file')
        if 'file' in part:
            references.append((pointer+'/file', part['file']))
    # Validate the complete file interface before reading or replacing output.
    # Never guess that a similarly named file is the intended content/order.
    missing = []
    for pointer, name in references:
        if not source_path(name, pointer).is_file():
            missing.append({'pointer': pointer, 'path': name})
    if missing:
        available, truncated = source_inventory(draft_path.parent)
        raise DraftError('manifest references missing source files', {
            'missing_sources': missing[:32], 'missing_source_count': len(missing),
            'available_sources': available, 'inventory_truncated': truncated,
            'recovery': 'Correct only the listed manifest paths using the saved file names, or create a genuinely missing part. Do not reread all source or guess replacements. Rerun the saved assembly entrypoint after that edit.'})

    def saved_source(name, pointer):
        source = source_path(name, pointer)
        try:
            return source.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as error:
            raise DraftError(pointer+': cannot read UTF-8 source '+name) from error
    def source_field(name):
        if name in data and name+'_file' in data:
            raise DraftError('/'+name+': choose inline source OR a file, not both')
        return (saved_source(data[name+'_file'], '/'+name+'_file') if name+'_file' in data
                else text(data.get(name, ''), '/'+name))
    css, javascript = source_field('css'), source_field('javascript')
    if re.search(r'</style\b', css, re.I):
        raise DraftError('/css: supply CSS only, without a closing style tag')
    if re.search(r'</script\b', javascript, re.I):
        raise DraftError('/javascript: supply JavaScript only, without a closing script tag')
    inspector, blocks, part_ids, id_owners, ref_owners = Inspect(), [], set(), {}, {}
    for index, part in enumerate(parts):
        pointer = f'/parts/{index}'
        if not isinstance(part, dict) or set(part) not in ({'id', 'html'}, {'id', 'file'}):
            raise DraftError(pointer+': fields must be id and either html or file')
        key = text(part['id'], pointer+'/id', required=True)
        if key in part_ids:
            raise DraftError(pointer+'/id: duplicate part identifier '+key)
        part_ids.add(key)
        block = (saved_source(part['file'], pointer+'/file') if 'file' in part
                 else text(part['html'], pointer+'/html', required=True))
        source_pointer = pointer+('/file' if 'file' in part else '/html')
        if not block.strip():
            raise DraftError(pointer+': empty source part')
        fragment = Inspect()
        try:
            fragment.feed(block)
        except DraftError as error:
            raise DraftError(source_pointer+': '+str(error)) from error
        if fragment.roots or fragment.forbidden:
            raise DraftError(source_pointer+': provide inner HTML only; roots, doctypes and scripts belong to the assembler')
        for element_id in fragment.ids:
            if element_id in id_owners:
                raise DraftError(source_pointer+': duplicate element ID '+element_id+'; already in '+id_owners[element_id])
            id_owners[element_id] = source_pointer
        for ref in fragment.refs:
            ref_owners.setdefault(ref, source_pointer)
        inspector.feed(block)
        blocks.append(block)
    for ref in inspector.refs:
        if ref not in id_owners:
            raise DraftError(ref_owners[ref]+': unresolved anchor or ARIA reference '+ref)
    languages = data.get('languages', [])
    if not isinstance(languages, list) or any(not isinstance(v, str) for v in languages):
        raise DraftError('/languages: expected an array of language codes')
    if languages:
        if (len(languages) != len(set(languages)) or language not in languages
                or any(not re.fullmatch(r'[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{1,8})*', v) for v in languages)):
            raise DraftError('/languages: unique valid codes must include the default language')
        if inspector.controls != set(languages) or inspector.languages != set(languages):
            raise DraftError('/parts: language controls and translated content must match /languages')
        javascript = LANGUAGE_SCRIPT+'\n'+javascript
    description = text(data.get('description', ''), '/description')
    source = ('<!doctype html>\n<html lang="'+html.escape(language, quote=True)+'" data-lang="'+html.escape(language, quote=True)+'">\n'
        '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>'+html.escape(title)+'</title><meta name="description" content="'+html.escape(description, quote=True)+'">'
        '<style>[hidden]{display:none!important}\n'+css+'</style></head>\n<body><main>\n'
        +'\n'.join(blocks)+'\n</main>\n'+('<script>'+javascript+'</script>\n' if javascript else '')+'</body></html>\n')
    # Preserve every authored part. Do not repair source by guessing or rewriting it.
    # Atomic replacement also preserves the previous delivery on an I/O failure.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=output_path.parent,
                                         prefix='.'+output_path.name+'.', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(source)
        os.replace(temporary, output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'status':'assembled', 'output':output_path.name, 'parts':len(parts),
            'source_chars':len(source), 'structural_checks':'passed', 'browser_review':'required'}


def assemble(draft_path, output_path):
    """Compact recoverable diagnostics; build() retains its exception API."""
    try:
        return build(draft_path, output_path)
    except (DraftError, json.JSONDecodeError) as error:
        report = {'status': 'rejected', 'error': str(error), 'draft_retained': True,
                  'previous_output_unchanged': True}
        if isinstance(error, DraftError):
            report.update(error.diagnostics)
        return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('draft', type=Path)
    parser.add_argument('output', type=Path)
    arguments = parser.parse_args()
    report = assemble(arguments.draft, arguments.output)
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'assembled' else 1)
