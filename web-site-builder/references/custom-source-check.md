# Checks for manually authored HTML

Use only for an existing page or custom stack without the assembler, in its
existing sandbox. Check document containers, IDs and references, not all HTML5
rules. Browser inspection remains necessary for scripts and visible behavior.

```python
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
class Check(HTMLParser):
    def __init__(self):
        super().__init__(); self.starts=Counter(); self.ends=Counter()
        self.stack=[]; self.ids=[]; self.refs=[]; self.errors=[]; self.closed=False; self.doctypes=0
    def handle_decl(self, value):
        self.doctypes += value.strip().lower() == 'doctype html'
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag in {'html','head','body','main'}:
            self.starts[tag]+=1; self.stack.append(tag)
        if 'id' in a: self.ids.append(a['id'])
        if a.get('href','').startswith('#') and len(a['href'])>1: self.refs.append(a['href'][1:])
        for name in ('aria-labelledby','aria-controls'):
            self.refs.extend(a.get(name,'').split())
    def handle_endtag(self, tag):
        if tag not in {'html','head','body','main'}: return
        self.ends[tag]+=1
        if not self.stack or self.stack.pop()!=tag: self.errors.append('container order: '+tag)
        if tag=='html': self.closed=True
    def handle_data(self, value):
        if self.closed and value.strip(): self.errors.append('content after html')
p=Check(); p.feed(Path('index.html').read_text(encoding='utf-8'))
assert p.doctypes==1 and not p.stack and not p.errors, p.errors
assert all(p.starts[t]==p.ends[t]==1 for t in ('html','head','body','main')), 'document containers'
assert len(p.ids)==len(set(p.ids)), 'duplicate IDs'
assert all(r in p.ids for r in p.refs), 'unresolved anchors/ARIA'
print('Source containers, IDs and references passed')
```
