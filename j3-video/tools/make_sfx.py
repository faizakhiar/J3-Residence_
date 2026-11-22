"""Synthesize the film's sound effects and music bed (deterministic, seeded)."""
import numpy as np, wave, sys, os
SR = 44100
rng = np.random.default_rng(7)
out = sys.argv[1]

def save(name, x, peak=0.9):
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    if x.ndim == 1: x = np.stack([x, x], 1)
    with wave.open(os.path.join(out, name), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())

def t(d): return np.arange(int(SR * d)) / SR
def env(n, a, r):
    e = np.ones(n); A = int(SR*a); R = int(SR*r)
    e[:A] = np.linspace(0, 1, A); e[-R:] *= np.linspace(1, 0, R) ** 2; return e
def onepole(x, a):  # simple low-pass
    y = np.empty_like(x); s = 0.0
    for i, v in enumerate(x): s += a * (v - s); y[i] = s
    return y
def sweep_noise(d, f0, f1):
    n = rng.standard_normal(int(SR*d)); k = np.linspace(f0, f1, len(n))
    a = 1 - np.exp(-2*np.pi*k/SR)
    y = np.empty_like(n); s = 0.0; s2 = 0.0
    for i, v in enumerate(n):
        s += a[i]*(v-s); s2 += a[i]*(s-s2); y[i] = s - s2*0.6
    return y

# whoosh: band-swept noise, swell then fade, slight stereo pan
d = 0.7; x = sweep_noise(d, 300, 4000) * np.sin(np.pi*np.linspace(0,1,int(SR*d)))**1.5
pan = np.linspace(0.2, 0.8, len(x)); save("whoosh.wav", np.stack([x*(1-pan), x*pan], 1))
# stamp / impact: sub thump + noise crack
d = 0.6; tt = t(d)
thump = np.sin(2*np.pi*(55 + 90*np.exp(-tt*30))*tt) * np.exp(-tt*7)
crack = onepole(rng.standard_normal(len(tt)), 0.5) * np.exp(-tt*35)
save("stamp.wav", thump*1.0 + crack*0.5)
# pop: pitch-drop sine blip
d = 0.12; tt = t(d); f = 900*np.exp(-tt*18)+250
save("pop.wav", np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-tt*35), 0.7)
# tick
d = 0.05; tt = t(d); save("tick.wav", np.sin(2*np.pi*2400*tt)*np.exp(-tt*120) + rng.standard_normal(len(tt))*np.exp(-tt*300)*0.3, 0.6)
# ding: bell partials
d = 1.4; tt = t(d)
bell = sum(a*np.sin(2*np.pi*f*tt)*np.exp(-tt*k) for f,a,k in [(1318,1,3),(1976,.5,4),(2637,.35,6),(3951,.15,9)])
save("ding.wav", bell * env(len(tt), 0.003, 0.2), 0.7)
# coin / cash: two quick bright bells
d = 0.9; tt = t(d); c = np.zeros(len(tt))
for st, f in [(0, 2093), (0.08, 2637)]:
    s = int(st*SR); u = tt[:len(tt)-s]
    c[s:] += (np.sin(2*np.pi*f*u)+0.4*np.sin(2*np.pi*f*2.01*u))*np.exp(-u*7)
save("coin.wav", c, 0.7)
# riser: rising noise + sine glide into a cutoff
d = 1.3; tt = t(d); r = sweep_noise(d, 200, 6000)*(tt/d)**2
r += 0.3*np.sin(2*np.pi*np.cumsum(200+900*(tt/d)**2)/SR)*(tt/d)**2
save("riser.wav", r * env(len(tt), 0.01, 0.03), 0.8)
# swipe (short whoosh for transitions)
d = 0.35; x = sweep_noise(d, 1500, 7000)*np.sin(np.pi*np.linspace(0,1,int(SR*d)))**2
save("swipe.wav", x, 0.7)
# draw: soft scribble for dimension lines
d = 0.8; tt = t(d); x = sweep_noise(d, 2500, 3500)*(0.6+0.4*np.sin(2*np.pi*14*tt))*env(len(tt),0.05,0.2)
save("draw.wav", x, 0.5)

# music bed: warm 4-chord pad + soft pluck arpeggio, 96 BPM, 64 s
bpm = 96; beat = 60/bpm; dur = 64; tt = t(dur); n = len(tt)
chords = [[57,60,64,67],[53,57,60,64],[48,52,55,59],[55,59,62,65]]  # Am7 Fmaj7 Cmaj7 G7(ish)
hz = lambda m: 440*2**((m-69)/12)
pad = np.zeros(n); arp = np.zeros(n); bass = np.zeros(n)
bar = beat*4
for b in range(int(dur/bar)+1):
    ch = chords[b % 4]; s0 = int(b*bar*SR); s1 = min(n, int((b+1)*bar*SR)+int(0.3*SR))
    if s0 >= n: break
    u = np.arange(s1-s0)/SR; e = np.minimum(1, u/0.4) * np.minimum(1, (s1-s0)/SR - u + 0.01)/1
    e = np.clip(e, 0, 1)
    for m in ch:
        pad[s0:s1] += e*(np.sin(2*np.pi*hz(m)*u) + 0.3*np.sin(2*np.pi*hz(m)*1.003*u) + 0.15*np.sin(2*np.pi*hz(m)*2*u))
    bass[s0:s1] += e*np.sin(2*np.pi*hz(ch[0]-12)*u)
    for k in range(8):
        m = ch[[0,1,2,3,2,1,2,3][k]] + 12; a0 = s0 + int(k*beat/2*SR)
        if a0 >= n: break
        L = min(int(0.5*SR), n-a0); v = np.arange(L)/SR
        arp[a0:a0+L] += np.sin(2*np.pi*hz(m)*v)*np.exp(-v*9)*(0.9 if k%2==0 else 0.6)
pad = onepole(pad, 0.08)
mix = pad*0.22 + arp*0.28 + bass*0.35
fade = np.ones(n); fade[:int(1.5*SR)] = np.linspace(0,1,int(1.5*SR)); fade[-int(3*SR):] = np.linspace(1,0,int(3*SR))
L = mix*fade; R = np.roll(mix, int(0.012*SR))*fade
save("music_bed.wav", np.stack([L,R],1), 0.8)
print("ok")
