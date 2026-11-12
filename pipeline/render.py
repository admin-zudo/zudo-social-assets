"""Render an animated HTML page frame by frame and encode with mix.wav.
Usage: python3 render.py page.html out.mp4 T [width height] [query]
query e.g. "nopeople=1" hides .person elements (Instagram/Facebook Reels version)."""
import sys, json, os, shutil, subprocess
from playwright.sync_api import sync_playwright
html,out,T=sys.argv[1],sys.argv[2],float(sys.argv[3]); W=int(sys.argv[4]) if len(sys.argv)>4 else 1080; H=int(sys.argv[5]) if len(sys.argv)>5 else 1920
q=sys.argv[6] if len(sys.argv)>6 else ""; FPS=30; tl=json.load(open('tl.json'))
fd="frames_"+os.path.basename(out); shutil.rmtree(fd,ignore_errors=True); os.makedirs(fd)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":W,"height":H})
    pg.add_init_script("window.TL="+json.dumps(tl)); pg.goto("file://"+os.path.abspath(html)+("?"+q if q else "")); pg.wait_for_timeout(600)
    for i in range(int(T*FPS)):
        pg.evaluate(f"render({i/FPS},{T})"); pg.screenshot(path=f"{fd}/{i:05d}.jpg",type="jpeg",quality=90)
    b.close()
subprocess.run(["ffmpeg","-loglevel","error","-y","-framerate","30","-i",f"{fd}/%05d.jpg","-i","mix.wav","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",out],check=True)
shutil.rmtree(fd); print(out,"ok")
