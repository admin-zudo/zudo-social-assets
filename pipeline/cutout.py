"""Cut people out of their background. Usage: python3 cutout.py in.webp out.png [more pairs...]"""
import sys
from rembg import remove, new_session
from PIL import Image
s=new_session("isnet-general-use"); a=sys.argv[1:]
for i in range(0,len(a),2):
    remove(Image.open(a[i]).convert("RGB"),session=s,post_process_mask=True).save(a[i+1]); print(a[i+1])
