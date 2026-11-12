"""Fast-beat music + SFX + voice ducking. Usage: python3 audio.py T [events.json]
events.json: [{"t":seconds,"type":"pop|whoosh|impact|tick|ding|riser|swoosh","gain":0.3}]
Automatic: impact at 0.15 s, whoosh before every scene change (from tl.json). Writes mix.wav."""
import sys, json, numpy as np, soundfile as sf, subprocess
sr=44100; T=float(sys.argv[1]); N=int(sr*T); t=np.arange(N)/sr; rng=np.random.default_rng(7)
tl=json.load(open('tl.json')); B=[l['start']-0.25 for l in tl]
ev=json.load(open(sys.argv[2])) if len(sys.argv)>2 else []
def add(buf,sig,at,g=1.0):
    i=int(at*sr)
    if i<0: sig=sig[-i:]; i=0
    j=min(len(buf),i+len(sig))
    if j>i: buf[i:j]+=g*sig[:j-i]
def env(n,a,d): x=np.arange(n)/sr; return np.minimum(1,x/max(a,1e-4))*np.exp(-x/d)
def lp(x,k):
    y=np.zeros_like(x); acc=0.
    for i,v in enumerate(x): acc+=k*(v-acc); y[i]=acc
    return y
bpm=124; beat=60/bpm; bar=beat*4; mus=np.zeros(N)
x=np.arange(int(sr*.32))/sr; kick=np.sin(2*np.pi*(48*x+(130/18)*(1-np.exp(-x*18))))*np.exp(-x/0.13)+0.3*np.sin(2*np.pi*52*x)*np.exp(-x/0.2)
hn=int(sr*.05); hat=rng.standard_normal(hn); hat=(hat-lp(hat,0.35))*env(hn,0.0005,0.012)
cn=int(sr*.2); clap=rng.standard_normal(cn); clap=lp(clap-lp(clap,0.08),0.5)*env(cn,0.001,0.05)
roots=[110,87.31,130.81,98]; intro=bar
for kk in range(int(T/beat)+1):
    at=kk*beat
    if at>T-1.2: break
    if at>=intro: add(mus,kick,at,0.9)
    if kk%4 in (1,3) and at>=intro: add(mus,clap,at,0.35)
    add(mus,hat,at+beat/2,0.22)
    if at>=intro: add(mus,hat,at+beat/4,0.09); add(mus,hat,at+3*beat/4,0.09)
    r=roots[int(at//bar)%4]; bn=int(sr*beat*0.45); xb=np.arange(bn)/sr
    add(mus,lp((np.sign(np.sin(2*np.pi*r*xb))*0.5+np.sin(2*np.pi*r*xb))*env(bn,0.004,0.09),0.12),at+beat/2,0.5 if at>=intro else 0.25)
for i in range(int(T/bar)+1):
    r=roots[i%4]; n=int(sr*bar); xx=np.arange(n)/sr
    add(mus,sum(np.sin(2*np.pi*f*xx+0.3*j) for j,f in enumerate([r*2,r*2*1.26,r*3]))*np.minimum(1,xx/0.3)*np.minimum(1,(bar-xx)/0.3),i*bar,0.05)
mus*=np.minimum(1,t/0.5)*np.minimum(1,(T-t)/2.0)
def whoosh(d=0.45):
    n=int(sr*d); w=rng.standard_normal(n); xx=np.arange(n)/sr; k=0.02+0.4*np.sin(np.pi*xx/d)**2; y=np.zeros(n); acc=0
    for i in range(n): acc+=k[i]*(w[i]-acc); y[i]=acc
    return y*np.sin(np.pi*xx/d)**1.5
def pop(): n=int(sr*.09); xx=np.arange(n)/sr; return np.sin(2*np.pi*(900-500*xx/0.09)*xx)*env(n,0.001,0.025)
def impact():
    n=int(sr*.9); xx=np.arange(n)/sr; return np.sin(2*np.pi*(40+60*np.exp(-xx*10))*xx)*np.exp(-xx/0.3)+0.4*lp(rng.standard_normal(n),0.1)*np.exp(-xx/0.12)
def tick(): n=int(sr*.03); xx=np.arange(n)/sr; return np.sin(2*np.pi*3200*xx)*np.exp(-xx/0.004)
def ding(): n=int(sr*1.0); xx=np.arange(n)/sr; return (np.sin(2*np.pi*1318.5*xx)+0.5*np.sin(2*np.pi*1975.5*xx))*np.exp(-xx/0.35)
def riser(d=1.2): n=int(sr*d); xx=np.arange(n)/sr; w=rng.standard_normal(n); return (w-lp(w,0.05))*(xx/d)**2
def swoosh(): n=int(sr*.25); xx=np.arange(n)/sr; return np.sin(2*np.pi*(700-500*xx/0.25)*xx)*env(n,0.002,0.08)
F={"pop":pop,"whoosh":whoosh,"impact":impact,"tick":tick,"ding":ding,"riser":riser,"swoosh":swoosh}
sfx=np.zeros(N); add(sfx,impact(),0.15,0.9)
for b in B[1:]: add(sfx,whoosh(),b-0.32,0.5)
for e in ev: add(sfx,F[e["type"]](),e["t"],e.get("gain",0.35))
v,_=sf.read('vo_m.wav',dtype='float32'); v=v.mean(1) if v.ndim>1 else v
vo=np.zeros(N); vo[:min(N,len(v))]=v[:N]
ve=np.convolve(np.abs(vo),np.ones(2205)/2205,'same'); ve/=ve.max()+1e-9
duck=np.convolve(1-0.55*np.clip(ve*4,0,1),np.ones(4410)/4410,'same')
mix=vo/np.abs(vo).max()*0.9+mus/np.abs(mus).max()*0.32*duck+sfx/(np.abs(sfx).max()+1e-9)*0.42
sf.write('mix_raw.wav',np.stack([mix,mix],1).astype(np.float32),sr)
subprocess.run(["ffmpeg","-loglevel","error","-y","-i","mix_raw.wav","-af","loudnorm=I=-13:TP=-1:LRA=8","-ar","44100","mix.wav"],check=True); print("mix.wav ok")
