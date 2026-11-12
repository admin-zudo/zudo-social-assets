"""Bold voice 3 (Kokoro, free). Usage: python3 voice.py script.json
script.json: {"lines":[{"say":"text spoken (respell for pronunciation)","show":"caption text"}...]}
One line = one scene. Each sentence is generated separately and checked with Whisper.
Writes vo_m.wav (mastered, 44.1k) and tl.json [{text,start,end}] and qc.txt."""
import sys, json, re, difflib, numpy as np, soundfile as sf, subprocess, torch, torchaudio.functional as AF
from kokoro_onnx import Kokoro
from faster_whisper import WhisperModel
K="/home/claude/kokoro/"
k=Kokoro(K+"kokoro-v1.0.onnx",K+"voices-v1.0.bin")
W=WhisperModel('small.en',device='cpu',compute_type='int8')
voice=k.get_voice_style("am_fenrir")*0.6+k.get_voice_style("am_onyx")*0.4
lines=json.load(open(sys.argv[1]))["lines"]
NUM={"0":"zero","1":"one","2":"two","3":"three","4":"four","5":"five","6":"six","7":"seven","8":"eight","9":"nine","10":"ten"}
def norm(s): return [NUM.get(w,w) for w in re.sub(r"[^a-z0-9 ]","",s.lower().replace("-"," ")).split()]
SR=24000; out=[np.zeros(int(SR*.35),np.float32)]; t=.35; tl=[]; qc=[]
for L in lines:
    st=t; en=t
    for s in [x.strip() for x in re.findall(r'[^.?!]+[.?!]?',L["say"]) if x.strip()]:
        best=None
        for speed in (1.08,1.04,1.12):
            a,_=k.create(s,voice=voice,speed=speed,lang="en-us"); a=a.astype(np.float32)
            got=" ".join(x.text for x in W.transcribe(AF.resample(torch.from_numpy(a),SR,16000).numpy(),language="en")[0])
            r=difflib.SequenceMatcher(None,norm(s),norm(got)).ratio()
            if best is None or r>best[0]: best=(r,a,got)
            if r>=0.9: break
        r,a,got=best; qc.append(f"{r:.2f} | said: {s} | heard: {got.strip()}")
        out.append(a); t+=len(a)/SR; en=t
        g=0.45 if s.endswith('?') else 0.32
        out.append(np.zeros(int(SR*g),np.float32)); t+=g
    out.append(np.zeros(int(SR*.12),np.float32)); t+=.12
    tl.append({"text":L["show"],"start":round(st,2),"end":round(en,2)})
sf.write("vo.wav",np.concatenate(out),SR); json.dump(tl,open("tl.json","w"),indent=1)
open("qc.txt","w").write("\n".join(qc)); print("\n".join(qc)); print("VOICE_END",round(t,2))
subprocess.run(["ffmpeg","-loglevel","error","-y","-i","vo.wav","-af","highpass=f=60,equalizer=f=110:t=q:w=1:g=4,equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1:g=3,acompressor=threshold=-24dB:ratio=4:attack=3:release=90:makeup=4,asoftclip=type=tanh","-ar","44100","vo_m.wav"],check=True)
