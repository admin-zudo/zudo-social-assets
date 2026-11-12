"""Fails (exit 1) if any text overlaps a person image.
Carousel: python3 check_overlap.py slide1.html slide2.html ...  (1080x1350)
Video:    python3 check_overlap.py --video video.html T   (checks every scene at 2.8 s in, 1080x1920)"""
import sys, json
from playwright.sync_api import sync_playwright
JS="""(root)=>{const sc=root?document.getElementById(root):document.body;const out=[];
const imgs=[...sc.querySelectorAll('.ppl img,.person img')].filter(i=>getComputedStyle(i.closest('.ppl,.person')).display!=='none').map(i=>{const r=i.getBoundingClientRect(),c=i.parentElement.getBoundingClientRect();return {l:Math.max(r.left,c.left)+10,t:Math.max(r.top,c.top)+10,r:Math.min(r.right,c.right)-10,b:Math.min(r.bottom,c.bottom)-10}});
[...sc.querySelectorAll('*')].filter(e=>!e.closest('.ppl,.person')&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())).forEach(e=>{const g=document.createRange();g.selectNodeContents(e);for(const r of g.getClientRects())for(const p of imgs){const ox=Math.min(r.right,p.r)-Math.max(r.left,p.l),oy=Math.min(r.bottom,p.b)-Math.max(r.top,p.t);if(ox>4&&oy>4)out.push(e.textContent.trim().slice(0,30))}});return out}"""
bad=False
with sync_playwright() as p:
    b=p.chromium.launch()
    if sys.argv[1]=="--video":
        tl=json.load(open('tl.json')); T=float(sys.argv[3]); pg=b.new_page(viewport={"width":1080,"height":1920})
        pg.add_init_script("window.TL="+json.dumps(tl)); pg.goto("file://"+__import__('os').path.abspath(sys.argv[2])); pg.wait_for_timeout(500)
        n=pg.evaluate("document.querySelectorAll('.scene').length")
        for i in range(n):
            t=(tl[i]['start'] if i<len(tl) else T-3)+2.8; pg.evaluate(f"render({t},{T})")
            r=pg.evaluate(JS,f"s{i}");
            if r: bad=True; print(f"scene s{i} overlaps:",r)
    else:
        pg=b.new_page(viewport={"width":1080,"height":1350})
        for f in sys.argv[1:]:
            pg.goto("file://"+__import__('os').path.abspath(f)); pg.wait_for_timeout(400); r=pg.evaluate(JS,None)
            if r: bad=True; print(f,"overlaps:",r)
    b.close()
print("OVERLAP" if bad else "NO OVERLAP"); sys.exit(1 if bad else 0)
