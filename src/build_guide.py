"""Dependency-free printable guide renderer for the project's Markdown subset."""
from pathlib import Path
from html import escape
import re

ROOT = Path(__file__).resolve().parents[1]
FILES = ['TEAM_GUIDE.md', 'TUTORIAL.md', 'OPERATIONS.md', 'REFERENCE.md']


def inline(text):
    text = escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    def link(match):
        target = match[2]
        if target in FILES:
            target = '#' + target[:-3].lower()
        return f'<a href="{target}">{match[1]}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)


def render(text):
    out, paragraph, fenced = [], [], False
    def flush():
        if paragraph:
            out.append('<p>'+inline(' '.join(paragraph))+'</p>')
            paragraph.clear()
    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            out.append('</code></pre>' if fenced else '<pre><code>')
            fenced = not fenced
        elif fenced:
            out.append(escape(line)+'\n')
        elif line.startswith('#'):
            flush(); level = min(4, len(line)-len(line.lstrip('#')))
            out.append(f'<h{level}>{inline(line[level:].strip())}</h{level}>')
        elif line.startswith('- '):
            flush(); out.append('<p class="bullet">• '+inline(line[2:])+'</p>')
        elif re.match(r'^\d+\. ', line):
            flush(); out.append('<p class="bullet">'+inline(line)+'</p>')
        elif not line.strip():
            flush()
        else:
            paragraph.append(line)
    flush()
    return ''.join(out)


def build():
    sections = ''.join(f'<section id="{f[:-3].lower()}">{render((ROOT/"docs"/f).read_text(encoding="utf-8"))}</section>' for f in FILES)
    navigation = ''.join(f'<a href="#{f[:-3].lower()}">{f[:-3].replace("_", " ").title()}</a>' for f in FILES)
    html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SENTINEL team handbook</title><style>
    body{font:17px/1.7 system-ui,sans-serif;color:#20352f;background:#f3f5ef;margin:0}main{max-width:920px;margin:auto;padding:40px}nav{position:sticky;top:0;background:#123e35;color:white;padding:16px;display:flex;gap:20px;flex-wrap:wrap}nav a{color:white}h1{font-size:34px;line-height:1.2;color:#124c40}h2{font-size:24px;margin-top:36px}section{background:white;padding:38px;margin-bottom:35px;border:1px solid #d6e0d6;border-radius:14px;scroll-margin-top:90px}a{color:#126f60}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef3ef;padding:18px;font-size:14px}code{font-size:.88em;overflow-wrap:anywhere}.bullet{padding-left:18px}button{padding:10px;border:0;border-radius:7px;cursor:pointer}@media(max-width:650px){main{padding:12px}section{padding:20px}h1{font-size:28px}}@media print{@page{size:A4;margin:18mm}body{background:white;font-size:11pt;line-height:1.5}nav{display:none}main{padding:0;max-width:none}section{border:0;padding:0;border-radius:0;break-before:page}h1,h2,h3{break-after:avoid}pre{break-inside:avoid}a{color:inherit;text-decoration:none}}
    </style></head><body><nav><a href="/">SENTINEL workspace</a>'''+navigation+'''<button onclick="window.print()">Print / save PDF</button></nav><main>'''+sections+'</main></body></html>'
    (ROOT/'web/guide.html').write_text(html, encoding='utf-8')
    print('Built web/guide.html from four source documents')


if __name__ == '__main__':
    build()
