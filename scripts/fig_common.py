"""Shared render + tokens for the elsayed figures, copied from the anthropic evaluators-deep pack (scripts/fig_common.py,
itself from the toner pack) so the figures share that surface: palette, type, layout, and the render checks (no overflow,
no clipped SVG text, no label over another label or box). Row ids ride in an HTML comment only."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / 'analysis' / 'private' / 'figures'   # the figures name individuals: private until published on purpose
BG='#f7f4ee'; INK='#191b1a'; MUTED='#666960'; GRID='#e3dfd5'; AXIS='#c3c2b7'
BLUE='#2a78d6'; ORANGE='#eb6834'; AQUA='#1baf7a'; YELLOW='#eda100'; RED='#e34948'
BLUE250='#86b6ef'; GRAY='#b2b4aa'; LGRAY='#dcd9cf'; PURPLE='#7b5cd6'

def esc(s): return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def money(v):
    """Exact dollars below $10M (an award of $423,500 prints as such, not $424K; D30-003); rounded above."""
    v=float(v)
    if v>=100e6: return f'${v/1e6:,.0f}M'
    if v>=10e6: return f'${v/1e6:,.1f}M'
    return f'${v:,.0f}'

def legend(items):
    return '<div class="legend">'+''.join(f'<span><i class="sw" style="background:{c}"></i>{esc(t)}</span>' for c,t in items)+'</div>'

def cite(ids):
    """Row ids ride in an HTML comment only (HANDOFF §3: no ids printed on the figure)."""
    return '<!-- rows: '+' '.join(sorted(set(ids)))+' -->'

def render(stem, document, width, height):
    FIGURES.mkdir(parents=True, exist_ok=True)
    path=FIGURES/(stem+'.html'); path.write_text(document, encoding='utf-8')
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={'width':width,'height':height},device_scale_factor=2)
        pg.goto(path.as_uri(),wait_until='networkidle'); pg.evaluate('document.fonts.ready')
        ov=pg.evaluate('({w:document.documentElement.scrollWidth,h:document.documentElement.scrollHeight})')
        assert ov['w']<=width and ov['h']<=height, (stem,ov)
        box=pg.locator('.footnote').bounding_box(); assert box and box['y']+box['height']<=height,(stem,box)
        # no SVG text may run past its figure's edge: an inline SVG clips it (seven ev1 labels lost their year and amount; steward census 2026-09-29)
        clipped=pg.evaluate('''()=>[...document.querySelectorAll('svg text')].map(t=>{let s=t.ownerSVGElement;while(s.ownerSVGElement)s=s.ownerSVGElement;const r=t.getBoundingClientRect(),q=s.getBoundingClientRect();return [Math.max(q.left-r.left,r.right-q.right,q.top-r.top,r.bottom-q.bottom),t.textContent]}).filter(x=>x[0]>1)''')
        assert not clipped,(stem,'clipped text',clipped[:5])
        # nor print over other text, or over a box it does not sit in (steward census 2026-09-29: 21 figure 1 labels ran over the next column's boxes; two figure 5 labels over each other)
        crowded=pg.evaluate('''()=>{const out=[];for(const s of document.querySelectorAll('body svg')){if(s.ownerSVGElement)continue;
          const boxes=[...s.querySelectorAll('rect[rx="7"]')].map(r=>r.getBoundingClientRect());const ts=[...s.querySelectorAll('text')].map(t=>[t.getBoundingClientRect(),t.textContent]);
          const over=(a,b,m)=>Math.min(a.right,b.right)-Math.max(a.left,b.left)>2&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>m;
          for(let i=0;i<ts.length;i++){const r=ts[i][0];const home=boxes.find(b=>r.left>=b.left-1&&r.right<=b.right+1&&r.top>=b.top-1&&r.bottom<=b.bottom+1);
            for(const b of boxes){if(b!==home&&over(r,b,2)){out.push(['over a box',ts[i][1]]);break}}
            for(let j=i+1;j<ts.length;j++){if(over(r,ts[j][0],3))out.push(['over text',ts[i][1],ts[j][1]])}}}return out}''')
        assert not crowded,(stem,'crowded text',crowded[:5])
        if height <= 8000:
            pg.screenshot(path=str(FIGURES/(stem+'.png'))); b.close()
        else:  # a page this tall (figure 1) is captured in bands and joined: one screenshot of the whole page left parts of its footer, and earlier its whole foot, unpainted (A269a-fig-25; PLAN A8 entry 230, addendum 2)
            import io
            whole = Image.new('RGB', (width*2, height*2))
            for y0 in range(0, height, 2000):
                hh = min(2000, height-y0)
                band = Image.open(io.BytesIO(pg.screenshot(clip={'x':0,'y':y0,'width':width,'height':hh}, full_page=True))).convert('RGB')
                assert band.size == (width*2, hh*2), (stem, y0, band.size)
                whole.paste(band, (0, y0*2))
            b.close(); whole.save(FIGURES/(stem+'.png'))
    im=Image.open(FIGURES/(stem+'.png')).convert('RGB'); im.save(FIGURES/(stem+'.jpg'),quality=94)
    print('rendered',stem,im.size)

def shell(title,kicker,subtitle,body,footnote,width,height,extra_css=''):
    kicker=re.sub(r'^\s*Figure\s+\S+(?:\s*\([^)]*\))?\s*[·:—-]\s*','',kicker)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(title)}</title><style>
*{{box-sizing:border-box}}html,body{{margin:0;width:{width}px;height:{height}px;background:{BG}}}
body{{padding:46px 60px 32px;font-family:Arial,Helvetica,sans-serif;color:{INK};display:flex;flex-direction:column}}
.kicker{{font-size:17px;letter-spacing:2.8px;text-transform:uppercase;color:{MUTED};font-weight:bold}}
h1{{font-size:46px;letter-spacing:-1.4px;margin:12px 0 10px;line-height:1.07}}
.subtitle{{font-size:22px;line-height:1.35;color:{MUTED};margin:0 0 14px;max-width:1900px}}
.legend{{display:flex;gap:26px;font-size:18px;color:{INK};margin:0 0 10px;flex-wrap:wrap}}
.legend span{{display:inline-flex;align-items:center;gap:9px}}.sw{{width:18px;height:18px;border-radius:4px;display:inline-block}}
.footnote{{margin-top:auto;border-top:1px solid #cdcfc6;padding-top:12px;font-size:15px;line-height:1.4;color:{MUTED}}}
.footnote b{{color:{INK}}}svg{{display:block;flex-shrink:0}}text{{font-family:Arial,Helvetica,sans-serif}}{extra_css}
</style></head><body><div class="kicker">{esc(kicker)}</div><h1>{title}</h1><p class="subtitle">{subtitle}</p>{body}<div class="footnote">{footnote}</div></body></html>'''
