"""Make 16:9 (YouTube normal) and 1:1 (LinkedIn) versions from the 9:16 render plus a designed side panel.
Usage: python3 compose.py vertical.mp4 panel169.png panel11.png out169.mp4 out11.mp4
panel169.png = 1920x1080 design with an empty 608x1080 slot at x=1240..1848 (video goes there).
panel11.png  = 1080x1080 design with an empty 608x1080 slot at x=472..1080."""
import sys, subprocess
v,p169,p11,o169,o11=sys.argv[1:6]
subprocess.run(["ffmpeg","-loglevel","error","-y","-loop","1","-i",p169,"-i",v,"-filter_complex","[1:v]scale=608:1080[v];[0:v][v]overlay=1240:0:shortest=1,format=yuv420p","-map","1:a","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",o169],check=True)
subprocess.run(["ffmpeg","-loglevel","error","-y","-loop","1","-i",p11,"-i",v,"-filter_complex","[1:v]scale=608:1080[v];[0:v][v]overlay=472:0:shortest=1,format=yuv420p","-map","1:a","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",o11],check=True)
print("composed")
