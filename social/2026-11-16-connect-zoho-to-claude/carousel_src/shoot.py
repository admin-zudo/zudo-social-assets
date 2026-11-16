import os,sys
from playwright.sync_api import sync_playwright
from PIL import Image
themes={'white':'','navy':'theme-navy','blue':'theme-blue','amber':'theme-amber'}
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1080,'height':1350})
    for name,cls in themes.items():
        for i in range(1,5):
            pg.goto('file://'+os.path.abspath(f'slide{i}.html')); pg.evaluate(f"document.body.className='{cls}'"); pg.wait_for_timeout(250)
            pg.screenshot(path=f'{name}_{i}.png'); Image.open(f'{name}_{i}.png').convert('RGB').save(f'{name}_{i}.jpg',quality=90)
    b.close()
