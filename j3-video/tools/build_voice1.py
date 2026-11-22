"""Build index.html for the J3 Residence promo from the edit decision list.

The voiceover is cut in-composition: each kept phrase is its own <audio> clip
(data-media-start = source in-point), laid back to back with tight gaps. Every
animation, SFX hit and caption word is timed from the Whisper word timestamps,
re-mapped through the EDL, so editing a cut point moves everything with it.

    python3 -I tools/build.py   # writes index.html
"""
import json, html, os, sys

# ---------------------------------------------------------------- design themes
# Same edit, timing and scenes; each theme swaps the look (theme css), caption
# style, SFX character and a few motion accents.
THEMES = {
    "a": dict(name="Bold Gelap", css=None, cap="karaoke", sfx_gain=1.0, sfx_map={}, music=0.16,
              flash=False, frame=False, stamp_rot=-8, cap_on="#F5C24C", cap_off="#ffffff"),
    "b": dict(name="Mewah Editorial", css="theme-b.css", cap="bar", sfx_gain=0.6,
              sfx_map={"stamp": "pop", "coin": "ding", "riser": "whoosh"}, music=0.2,
              flash=False, frame=True, stamp_rot=0, cap_on="#D9B97E", cap_off="#F3EDE3"),
    "c": dict(name="Viral Bertenaga", css="theme-c.css", cap="box", sfx_gain=1.15, sfx_map={}, music=0.18,
              flash=True, frame=False, stamp_rot=-10, cap_on="#0B0B0B", cap_off="#ffffff"),
}
# ---------------------------------------------------------------- edit variants
# Each variant is its own edit: voice order (hook), shot list, shot lengths and
# transition language. Each also carries a look (theme) that suits the cut.
VARIANTS = {
    "a": dict(name="A · Grafik Penuh", theme="a", order=list(range(14)), blur=False),
    "b": dict(name="B · Sinematik Drone", theme="b", order=[9, 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13], blur=False),
    "c": dict(name="C · Pantas Viral", theme="c", order=[5, 0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13], blur=True),
}
THEME = sys.argv[1] if len(sys.argv) > 1 else "a"
V = VARIANTS[THEME]
T = THEMES[V["theme"]]

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORDS = json.load(open(os.path.join(HERE, "voice_words.json")))  # [[word, start, end], ...]

# ---------------------------------------------------------------- EDL
# (source_in, source_out, gap_before_in_output, note)
EDL = [
    (0.00, 2.34, 0.15, "HOOK  Fasa 1 dan 2 dah habis terjual."),
    (2.50, 5.54, 0.12, "Sekarang Fasa 3 pula dibuka untuk pendaftaran."),
    (6.02, 13.51, 0.22, "Projek rumah teres ... RM430 ribu sahaja."),
    (13.88, 20.01, 0.14, "Freehold, 3 / 3+1 bilik tidur, 2 bilik air."),
    (20.42, 26.36, 0.14, "Saiz tanah 20x73, binaan 1,040 kps."),
    # CUT 26.36-27.63  'Yang menariknya,' (filler)  -> straight to the offer
    (27.63, 29.47, 0.18, "Booking cuma RM500."),
    (29.82, 33.96, 0.10, "Yuran guaman SPA, MOT, disbursement percuma."),
    (34.24, 37.92, 0.14, "Pembiayaan sehingga 100%."),
    (38.30, 42.33, 0.22, "Lokasi: sekolah, masjid, kemudahan harian."),
    (42.68, 45.87, 0.10, "Putrajaya, Bangi, KLIA."),
    (46.24, 48.97, 0.18, "Siap Februari 2028."),
    # CUT 48.97-51.38  'Fasa sebelum ini dah sold out.' (repeats the hook)
    (51.38, 54.34, 0.22, "Daftar awal untuk Fasa 3."),
    (54.60, 55.89, 0.12, "Nak tahu lebih lanjut?"),
    (56.18, 57.25, 0.08, "Hubungi saya sekarang."),
]
END_HOLD = 3.4

# out time of each segment
SEG = [None] * len(EDL)          # indexed by EDL (source) order
t = 0.0
for n, i in enumerate(V["order"]):
    a, b, gap, note = EDL[i]
    if n == 0:
        gap = 0.15
    elif V["order"][n - 1] != i - 1:   # a re-ordered jump: give it a breath
        gap = max(gap, 0.25)
    t += gap
    SEG[i] = dict(i=i, src_in=a, src_out=b, out_in=round(t, 3), out_out=round(t + (b - a), 3), note=note)
    t += b - a
PLAY = [SEG[i] for i in V["order"]]  # in film order
DURATION = round(t + END_HOLD, 2)


def out(src):
    """Map a source (voice file) time to film time."""
    for s in SEG:
        if s["src_in"] - 0.05 <= src <= s["src_out"] + 0.05:
            return round(s["out_in"] + (src - s["src_in"]), 3)
    raise ValueError(f"time {src} was cut")


def w(text, nth=1, after=0.0):
    """Film-time start of the nth occurrence of a word at/after source time `after`."""
    k = 0
    for word, s, e in WORDS:
        if s + 0.001 >= after and word.lower().strip(".,?%") == text.lower():
            k += 1
            if k == nth:
                return out(s)
    raise KeyError(text)


def seg(i):
    return SEG[i]


# ---------------------------------------------------------------- caption text fixes
FIX = {
    "ditaman": "di Taman", "Jendram": "Jenderam", "Saya": "Saiz", "setanah": "tanah",
    "20x73": "20×73", "1040": "1,040", "keputra": "ke", "jaya,": "Putrajaya,",
    "bangi": "Bangi", "Teres": "teres", "Rumah": "rumah",
}

elements = []   # html strings
tweens = []     # js strings
audio = []      # html strings

def clip(html_inner, start, dur, cls="", style="", id_=None, track=1):
    clip.n = getattr(clip, "n", 0) + 1
    idattr = f' id="{id_ or (cls.split()[0] if cls else "el") + str(clip.n)}"'
    elements.append(
        f'<div{idattr} class="clip {cls}" data-start="{start:.3f}" data-duration="{dur:.3f}" '
        f'data-track-index="{track}" style="{style}">{html_inner}</div>')

sfx_n = [0]
def sfx(name, at, vol=0.6, dur=None):
    name = T["sfx_map"].get(name, name); vol = round(min(1.0, vol * T["sfx_gain"]), 3)
    lengths = dict(whoosh=0.7, stamp=0.6, pop=0.12, tick=0.05, ding=1.4, coin=0.9,
                   riser=1.3, swipe=0.35, draw=0.8)
    d = dur or lengths[name]
    sfx_n[0] += 1
    audio.append(f'<audio id="sfx{sfx_n[0]}" src="assets/sfx/{name}.wav" data-start="{max(0,at):.3f}" '
                 f'data-duration="{d:.3f}" data-volume="{vol}" data-track-index="9"></audio>')

def tw(js):
    tweens.append(js)

# ---------------------------------------------------------------- voice clips
for s in PLAY:
    audio.append(
        f'<audio id="vo{s["i"]}" src="assets/audio/voice.mp3" data-start="{s["out_in"]:.3f}" '
        f'data-duration="{s["src_out"]-s["src_in"]:.3f}" data-media-start="{s["src_in"]:.3f}" '
        f'data-volume="1" data-fade-in="0.02" data-fade-out="0.04" data-track-index="8"></audio>'
        f'<!-- {html.escape(s["note"])} -->')

# music bed under everything, ducked by level, lifted for the end card
audio.append(f'<audio id="music" src="assets/sfx/music_bed.wav" data-start="0" data-duration="{DURATION:.3f}" '
             f'data-volume="{T["music"]}" data-fade-in="0.6" data-fade-out="1.6" data-track-index="10"></audio>')

# ---------------------------------------------------------------- SHOTS + TRANSITIONS
# A shot: src "vid:<clip>" (drone, assets/video), "img:<still>" (render) or
# "solid:planbg"; [a, b) is its film window; tin is the transition INTO it.
# Media is wrapped so transitions (on the wrapper) never fight Ken Burns (on media).
VLEN = {"row": 8.0, "landw": 6.5, "estatel": 21.0, "orbit": 12.0, "roofs": 8.0, "shop": 18.0}
S = lambda i: SEG[i]
H = w("harga")

def sh(src, a, b, tin="xfade", d=0.3, off=0.0, k0=(1.0, 0, 0), k1=(1.06, 0, 0), pos="50% 50%"):
    return dict(src=src, a=round(a, 3), b=round(b, 3), tin=tin, d=d, off=off, k0=k0, k1=k1, pos=pos)

OVERLAYS = []   # (a, b) windows that get the translucent map tint

if THEME == "a":
    SHOTS = [
        sh("vid:row", 0, S(1)["out_in"], "fadein", off=1.3, k0=(1.12, 0, 0), k1=(1.0, 0, 0)),
        sh("vid:landw", S(1)["out_in"], S(2)["out_in"], off=2.1, k1=(1.08, 0, 0)),
        sh("vid:estatel", S(2)["out_in"], H, off=0),
        sh("img:street", H, S(3)["out_in"], k0=(1.08, 520, 0), k1=(1.12, -100, 0)),
        sh("img:front", S(3)["out_in"], S(4)["out_in"], k0=(1.2, -300, 40), k1=(1.3, 120, 0), pos="50% 60%"),
        sh("solid:planbg", S(4)["out_in"], S(5)["out_in"]),
        sh("img:corner", S(5)["out_in"], S(7)["out_in"], k0=(1.25, -200, 0), k1=(1.1, 200, 0), pos="40% 50%"),
        sh("img:street", S(7)["out_in"], S(8)["out_in"], k0=(1.15, -500, 0), k1=(1.22, -200, 0)),
        sh("vid:estatel", S(8)["out_in"], S(10)["out_in"], off=11.5, k1=(1.1, 0, 0)),
        sh("vid:orbit", S(10)["out_in"], S(11)["out_in"], off=0, k0=(1.12, 0, 0), k1=(1.0, 0, 0)),
        sh("img:front", S(11)["out_in"], DURATION, k0=(1.1, 0, 0), k1=(1.28, 0, -40), pos="50% 55%"),
    ]
    for x in SHOTS[1:]:
        x["d"] = 0.28
    OVERLAYS = [(S(8)["out_in"], S(10)["out_in"])]

elif THEME == "b":   # cinematic: long drone takes, slow motivated transitions
    SHOTS = [
        sh("vid:estatel", 0, S(0)["out_in"], "fadein", off=0, k0=(1.22, 0, 0), k1=(1.0, 0, 0)),
        sh("vid:row", S(0)["out_in"], S(1)["out_in"], "zoomthru", 0.6, off=0, k1=(1.1, 0, 0)),
        sh("vid:landw", S(1)["out_in"], S(2)["out_in"], "leak", 0.7, off=0.5, k1=(1.08, 0, 0)),
        sh("vid:orbit", S(2)["out_in"], H, "dip", 0.6, off=0.0, k0=(1.12, 0, 0), k1=(1.0, 0, 0)),
        sh("img:street", H, S(3)["out_in"], "xfade", 0.7, k0=(1.06, 450, 0), k1=(1.1, 150, 0)),
        sh("img:front", S(3)["out_in"], S(4)["out_in"], "xfade", 0.7, k0=(1.15, -150, 30), k1=(1.24, 60, 0), pos="50% 60%"),
        sh("solid:planbg", S(4)["out_in"], S(5)["out_in"], "dip", 0.6),
        sh("vid:orbit", S(5)["out_in"], S(7)["out_in"], "zoomthru", 0.6, off=4.5, k1=(1.08, 0, 0)),
        sh("img:corner", S(7)["out_in"], S(8)["out_in"], "leak", 0.7, k0=(1.2, -150, 0), k1=(1.12, 120, 0), pos="40% 50%"),
        sh("vid:shop", S(8)["out_in"], S(10)["out_in"], "dip", 0.6, off=4.0, k1=(1.1, 0, 0)),
        sh("vid:roofs", S(10)["out_in"], S(11)["out_in"], "xfade", 0.6, off=0, k0=(1.1, 0, 0), k1=(1.0, 0, 0)),
        sh("vid:row", S(11)["out_in"], S(12)["out_in"], "zoomthru", 0.6, off=3.6, k1=(1.1, 0, 0)),
        sh("img:front", S(12)["out_in"], DURATION, "dip", 0.6, k0=(1.1, 0, 0), k1=(1.25, 0, -40), pos="50% 55%"),
    ]
    OVERLAYS = [(0, S(0)["out_in"]), (S(8)["out_in"], S(10)["out_in"])]

else:   # "c" fast social cut: a new shot every ~1.2 s, cut on word starts
    POOLS = {
        5: [("vid:orbit", 1.0), ("vid:row", 3.0)],
        0: [("vid:row", 0.0), ("vid:roofs", 0.0), ("vid:row", 5.0)],
        1: [("vid:landw", 0.0), ("vid:landw", 3.5)],
        2: [("vid:estatel", 2.0), ("vid:orbit", 3.0), ("img:street", 0), ("img:front", 0), ("img:corner", 0)],
        3: [("img:front", 0), ("img:corner", 0), ("vid:orbit", 6.0), ("img:street", 0)],
        6: [("img:corner", 0), ("img:street", 0), ("vid:orbit", 9.0)],
        7: [("img:street", 0), ("vid:roofs", 4.0), ("img:front", 0)],
        10: [("vid:orbit", 0.0), ("vid:row", 3.0)],
        11: [("vid:landw", 2.0), ("vid:row", 5.0)],
    }
    PANS = [((1.14, -320, 0), (1.24, -80, 0)), ((1.14, 320, 0), (1.24, 80, 0)),
            ((1.3, 0, 0), (1.14, 0, 0)), ((1.12, -560, 0), (1.2, -260, 0))]
    word_starts = sorted(out(st) for _, st, en in WORDS if any(x["src_in"] - 0.05 <= st < x["src_out"] for x in PLAY))
    SHOTS = []
    nimg = 0
    n = 0
    while n < len(PLAY):
        s_ = PLAY[n]
        a = 0.0 if n == 0 else s_["out_in"]
        i = s_["i"]
        if i == 8:      # map runs over both location lines
            SHOTS.append(sh("vid:estatel", a, S(10)["out_in"], "whip", 0.24, off=12.0, k1=(1.08, 0, 0)))
            OVERLAYS.append((a, S(10)["out_in"])); n += 2; continue
        if i == 4:
            SHOTS.append(sh("solid:planbg", a, PLAY[n + 1]["out_in"], "whip", 0.24)); n += 1; continue
        if i == 12:
            SHOTS.append(sh("img:front", a, DURATION, "whip", 0.24, k0=(1.1, 0, 0), k1=(1.28, 0, -40), pos="50% 55%"))
            break
        b = PLAY[n + 1]["out_in"]
        cuts = [a]
        for ws in word_starts:
            if a + 1.0 <= ws <= b - 0.8 and ws - cuts[-1] >= 1.1:
                cuts.append(ws)
        cuts.append(b)
        pool = POOLS[i]
        used = {}
        for j in range(len(cuts) - 1):
            src, off = pool[j % len(pool)]
            tin = "fadein" if not SHOTS else ("whip" if j == 0 else ("punch" if j % 2 else "glitch"))
            if src.startswith("vid:"):
                base = off + used.get((src, off), 0.0)
                need = cuts[j + 1] - cuts[j] + 0.3
                if base + need > VLEN[src[4:]]:
                    base = max(0.0, VLEN[src[4:]] - need - 0.05)
                used[(src, off)] = used.get((src, off), 0.0) + need
                SHOTS.append(sh(src, cuts[j], cuts[j + 1], tin, 0.24, off=round(base, 3), k0=(1.0, 0, 0), k1=(1.1, 0, 0)))
            else:
                k0, k1 = PANS[nimg % len(PANS)]; nimg += 1
                SHOTS.append(sh(src, cuts[j], cuts[j + 1], tin, 0.24, k0=k0, k1=k1, pos="50% 55%"))
        n += 1

# timing of each transition: (fraction of d before the cut the incoming shot starts,
#                             fraction of d after the cut the outgoing shot holds)
TR = dict(fadein=(0, 0), cut=(0, 0), xfade=(1, 0), zoomthru=(1, 0), leak=(1, 0), dip=(0, 0),
          whip=(0.5, 0.5), punch=(0, 0), glitch=(0, 0))
need_flash = any(x["tin"] in ("punch", "glitch") for x in SHOTS)
need_dip = any(x["tin"] == "dip" for x in SHOTS)
need_leak = any(x["tin"] == "leak" for x in SHOTS)
first_out = {}

for k, x in enumerate(SHOTS):
    nxt = SHOTS[k + 1] if k + 1 < len(SHOTS) else None
    pre = TR[x["tin"]][0] * x["d"] if k else 0
    post = TR[nxt["tin"]][1] * nxt["d"] if nxt else 0
    st = max(0.0, x["a"] - pre); en = min(DURATION, x["b"] + post); dur = en - st
    x["st"], x["en"] = st, en
    pid = f"plate{k}"
    kind, name = x["src"].split(":")
    k0, k1 = x["k0"], x["k1"]
    if kind == "vid":
        assert x["off"] + dur <= VLEN[name] + 0.05, (THEME, name, x["off"], dur)
        elements.append(f'<div id="{pid}" class="pw"><video id="{pid}v" class="clip plate vid" src="assets/video/{name}.mp4" muted playsinline '
                        f'data-start="{st:.3f}" data-duration="{dur:.3f}" data-media-start="{x["off"]:.3f}" data-track-index="0"></video></div>')
        tw(f'tl.fromTo("#{pid}v",{{scale:{k0[0]},x:{k0[1]},y:{k0[2]}}},{{scale:{k1[0]},x:{k1[1]},y:{k1[2]},duration:{dur:.3f},ease:"none"}},{st:.3f});')
    elif kind == "img":
        clip(f'<img src="assets/img/{name}.jpg" style="object-position:{x["pos"]}" alt="">', st, dur, "plate", id_=pid, track=0)
        tw(f'tl.fromTo("#{pid} img",{{xPercent:-50,scale:{k0[0]},x:{k0[1]},y:{k0[2]}}},{{xPercent:-50,scale:{k1[0]},x:{k1[1]},y:{k1[2]},duration:{dur:.3f},ease:"none"}},{st:.3f});')
    else:
        clip("", st, dur, "plate solid " + name, id_=pid, track=0)

    # ---- transition into this shot
    a, d, tin = x["a"], x["d"], x["tin"]
    prev = f"#plate{k-1}" if k else None
    IR = ",immediateRender:false"
    if tin == "fadein":
        tw(f'tl.fromTo("#{pid}",{{opacity:0.1}},{{opacity:1,duration:0.35}},{st:.3f});')
    elif tin == "xfade":
        tw(f'tl.fromTo("#{pid}",{{opacity:0}},{{opacity:1,duration:{d},ease:"power1.inOut"}},{a-d:.3f});')
        sfx("swipe", a - d - 0.05, 0.35)
    elif tin == "zoomthru":
        tw(f'tl.fromTo("#{pid}",{{opacity:0,scale:1.3}},{{opacity:1,scale:1,duration:{d},ease:"power2.out"}},{a-d:.3f});')
        tw(f'tl.fromTo("{prev}",{{scale:1}},{{scale:1.7,duration:{d},ease:"power2.in"{IR}}},{a-d:.3f});')
        sfx("whoosh", a - d, 0.4)
    elif tin == "leak":
        tw(f'tl.fromTo("#{pid}",{{opacity:0}},{{opacity:1,duration:{d},ease:"power1.inOut"}},{a-d:.3f});')
        tw(f'tl.fromTo("#leakov",{{opacity:0,x:-500}},{{opacity:0.95,x:0,duration:{d*0.6:.3f},ease:"power2.out"{IR}}},{a-d:.3f});')
        tw(f'tl.fromTo("#leakov",{{opacity:0.95,x:0}},{{opacity:0,x:500,duration:{d*0.8:.3f},ease:"power2.in"{IR}}},{a-d*0.4:.3f});')
        sfx("whoosh", a - d, 0.3)
    elif tin == "dip":
        tw(f'tl.fromTo("#dipov",{{opacity:0}},{{opacity:1,duration:{d/2:.3f},ease:"power1.in"{IR}}},{a-d/2:.3f});')
        tw(f'tl.fromTo("#dipov",{{opacity:1}},{{opacity:0,duration:{d/2:.3f},ease:"power1.out"{IR}}},{a:.3f});')
        sfx("whoosh", a - d / 2, 0.18)
    elif tin == "whip":
        tw(f'tl.fromTo("#{pid}",{{x:1080}},{{x:0,duration:{d},ease:"expo.inOut"}},{a-d/2:.3f});')
        tw(f'tl.fromTo("{prev}",{{x:0}},{{x:-1080,duration:{d},ease:"expo.inOut"{IR}}},{a-d/2:.3f});')
        sfx("swipe", a - d / 2 - 0.03, 0.6)
    elif tin == "punch":
        tw(f'tl.fromTo("#{pid}",{{scale:1.35}},{{scale:1,duration:0.3,ease:"expo.out"}},{a:.3f});')
        tw(f'tl.fromTo("#flash",{{opacity:0.7}},{{opacity:0,duration:0.18,ease:"power2.out"{IR}}},{a:.3f});')
        sfx("pop", a, 0.5)
    elif tin == "glitch":
        tw(f'tl.fromTo("#{pid}",{{x:-60,scale:1.06}},{{x:0,scale:1,duration:0.28,ease:"elastic.out(1.2,0.25)"}},{a:.3f});')
        tw(f'tl.fromTo("#flash",{{opacity:0.5}},{{opacity:0,duration:0.12{IR}}},{a:.3f});')
        sfx("tick", a, 0.7); sfx("swipe", a - 0.02, 0.25)

for k, (oa, ob) in enumerate(OVERLAYS):
    st = max(0.0, oa - 0.3)
    clip("", st, ob - st, "plate solid mapbg", id_=f"tint{k}", track=0)
    tw(f'tl.fromTo("#tint{k}",{{opacity:0}},{{opacity:1,duration:0.6,ease:"power1.inOut"}},{max(0.0, oa + (0 if oa < 0.5 else 0.3)):.3f});')

# vignette + gradient always on top of plates
clip("", 0, DURATION, "shade", track=1)
if need_dip:
    clip("", 0, DURATION, "dipov", id_="dipov", track=6)
if need_leak:
    clip("", 0, DURATION, "leakov", id_="leakov", track=6)
if T["frame"]:
    clip('<div class="framebox"></div>', 0, DURATION, "frame", id_="frame", track=6)
if need_flash:
    clip("", 0, DURATION, "flash", id_="flash", track=6)

# persistent brand tag (after the hook)
tag_in = PLAY[2]["out_in"]
clip('<span class="dot"></span>J3 RESIDENCE <b>· FASA 3</b>', tag_in, DURATION - tag_in, "brandtag", id_="brandtag", track=2)
tw(f'tl.fromTo("#brandtag",{{opacity:0,y:-30}},{{opacity:1,y:0,duration:0.5,ease:"power3.out"}},{tag_in:.3f});')

# ================================================================ SCENES
# ---- 1. HOOK: Fasa 1 & 2 SOLD OUT
s = seg(0)
t1, t2, tj = w("1"), w("2"), w("terjual")
clip('''<div class="hook">
  <div class="hrow" id="h1"><span class="fasa">FASA 1</span><span class="stamp" id="st1">SOLD OUT</span></div>
  <div class="hrow" id="h2"><span class="fasa">FASA 2</span><span class="stamp" id="st2">SOLD OUT</span></div>
  <div class="hsub" id="hsub">HABIS TERJUAL</div>
</div>''', max(0, s["out_in"] - 0.1), s["out_out"] - max(0, s["out_in"] - 0.1) + 0.12, "center", track=3)
tw(f'tl.fromTo("#h1",{{x:-1100}},{{x:0,duration:0.35,ease:"power4.out"}},{t1-0.30:.3f});')
tw(f'tl.fromTo("#h2",{{x:1100}},{{x:0,duration:0.35,ease:"power4.out"}},{t2-0.25:.3f});')
for sid, at in (("st1", t1 + 0.12), ("st2", t2 + 0.12)):
    tw(f'tl.fromTo("#{sid}",{{scale:3.2,opacity:0,rotation:-14}},{{scale:1,opacity:1,rotation:{T["stamp_rot"]},duration:0.18,ease:"power4.in"}},{at:.3f});')
    tw(f'tl.fromTo(".hook",{{x:-12,y:8}},{{x:0,y:0,duration:0.25,ease:"elastic.out(1,0.3)",immediateRender:false}},{at+0.18:.3f});')
    sfx("stamp", at + 0.15, 0.45)
tw(f'tl.fromTo("#hsub",{{opacity:0,y:40,scaleX:1.4}},{{opacity:1,y:0,scaleX:1,duration:0.4,ease:"power3.out"}},{tj-0.15:.3f});')
sfx("whoosh", s["out_in"] - 0.15, 0.35)
tw(f'tl.to(".hook",{{scale:0.8,opacity:0,duration:0.2,ease:"power2.in"}},{s["out_out"]-0.05:.3f});')

# ---- 2. FASA 3 dibuka
s = seg(1)
t3, tb = w("3"), w("dibuka")
clip('''<div class="f3">
  <div class="kicker" id="f3k">SEKARANG</div>
  <div class="f3big" id="f3big">FASA <em>3</em></div>
  <div class="pill gold" id="f3p">KINI DIBUKA · DAFTAR SEKARANG</div>
</div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.25, "center", track=3)
tw(f'tl.fromTo("#f3k",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.3}},{s["out_in"]:.3f});')
tw(f'tl.fromTo("#f3big",{{scale:0.4,opacity:0}},{{scale:1,opacity:1,duration:0.45,ease:"back.out(2.2)"}},{t3-0.12:.3f});')
tw(f'tl.fromTo("#f3p",{{scaleX:0,opacity:0}},{{scaleX:1,opacity:1,duration:0.35,ease:"power3.out"}},{tb-0.05:.3f});')
sfx("riser", t3 - 1.25, 0.25)
sfx("ding", tb, 0.55)

# ---- 3. Project + location + price
s = seg(2)
tp, tt_, tharga, t430, tsah = w("projek"), w("taman") if False else out(7.64), w("harga"), w("430"), w("sahaja")
clip('''<div class="titlecard" id="tc">
  <div class="kicker">PROJEK BAHARU</div>
  <h1>Rumah Teres<br>1 Tingkat</h1>
  <div class="loc" id="loc"><svg viewBox="0 0 24 24"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>Taman Jenderam Lestari, Dengkil</div>
</div>''', s["out_in"] - 0.1, tharga - s["out_in"] + 0.15, "upper", track=3)
tw(f'tl.fromTo("#tc .kicker",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:0.3}},{s["out_in"]:.3f});')
tw(f'tl.fromTo("#tc h1",{{opacity:0,y:60,clipPath:"inset(0 0 100% 0)"}},{{opacity:1,y:0,clipPath:"inset(0 0 0% 0)",duration:0.5,ease:"power4.out"}},{tp:.3f});')
tw(f'tl.fromTo("#loc",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.4,ease:"back.out(1.8)"}},{tt_:.3f});')
sfx("pop", tt_, 0.5)
tw(f'tl.to("#tc",{{opacity:0,y:-60,duration:0.25}},{tharga-0.1:.3f});')
clip('''<div class="price" id="price">
  <div class="kicker">HARGA BERMULA</div>
  <div class="amt"><span class="cur">RM</span><span id="pnum">0</span><span class="k">K</span></div>
  <div class="pill dark" id="psah">SAHAJA</div>
</div>''', tharga - 0.1, s["out_out"] - tharga + 0.3, "center", track=3)
tw(f'tl.fromTo("#price",{{opacity:0,scale:0.85}},{{opacity:1,scale:1,duration:0.3,ease:"power3.out"}},{tharga-0.1:.3f});')
tw(f'const pc={{v:0}};tl.fromTo(pc,{{v:0}},{{v:430,duration:{max(0.5, w("ribu")-t430+0.3):.3f},ease:"power2.out",onUpdate:()=>{{document.getElementById("pnum").textContent=Math.round(pc.v)}}}},{t430-0.1:.3f});')
n_ticks = 8
for k in range(n_ticks):
    sfx("tick", t430 - 0.1 + k * (w("ribu") - t430 + 0.3) / n_ticks * (k / n_ticks) ** 0.3, 0.35)
sfx("coin", w("ringgit"), 0.6)
tw(f'tl.fromTo("#price .amt",{{scale:1}},{{scale:1.08,duration:0.12,yoyo:true,repeat:1,immediateRender:false}},{w("ringgit"):.3f});')
tw(f'tl.fromTo("#psah",{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.25}},{tsah:.3f});')

# ---- 4. Freehold + rooms
s = seg(3)
tfh, tpil, tbt, tba = w("freehold"), w("pilihan"), w("tidur"), w("air")
clip(f'''<div class="specs">
  <div class="badge" id="fh"><span>STATUS</span>FREEHOLD</div>
  <div class="chips">
    <div class="chip" id="c1"><b>3</b> atau <b>3+1</b><small>Bilik Tidur</small></div>
    <div class="chip" id="c2"><b>2</b><small>Bilik Air</small></div>
  </div>
</div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.3, "center", track=3)
tw(f'tl.fromTo("#fh",{{scale:0,rotation:-20}},{{scale:1,rotation:0,duration:0.45,ease:"back.out(2.5)"}},{tfh-0.15:.3f});')
sfx("stamp", tfh - 0.02, 0.55); sfx("ding", tfh + 0.05, 0.25)
tw(f'tl.fromTo("#c1",{{opacity:0,y:80}},{{opacity:1,y:0,duration:0.4,ease:"back.out(1.7)"}},{tpil:.3f});')
sfx("pop", tpil, 0.55)
tw(f'tl.fromTo("#c2",{{opacity:0,y:80}},{{opacity:1,y:0,duration:0.4,ease:"back.out(1.7)"}},{w("2", after=19.0)-0.05:.3f});')
sfx("pop", w("2", after=19.0), 0.55)

# ---- 5. Land size + built-up on floor plans
s = seg(4)
t2073, t1040 = w("20x73"), w("1040")
clip('''<div class="plans">
  <div class="kicker kc">PELAN LANTAI · JENIS A &amp; B</div>
  <div class="planrow">
    <div class="plan" id="pa"><img src="assets/img/plan-a.jpg" alt=""><span>JENIS A</span></div>
    <div class="plan" id="pb"><img src="assets/img/plan-b.jpg" alt=""><span>JENIS B</span></div>
  </div>
  <div class="dim">
    <div class="dline" id="dw"><i></i><span>20'</span></div>
    <div class="times" id="dx">×</div>
    <div class="dline" id="dl"><i></i><span>73'</span></div>
  </div>
  <div class="dimlab" id="dlab">SAIZ TANAH (KAKI)</div>
  <div class="pill gold big" id="bu">1,040 kps <small>keluasan binaan</small></div>
</div>''', s["out_in"] - 0.15, s["out_out"] - s["out_in"] + 0.35, "full", track=3)
tw(f'tl.fromTo("#pa",{{opacity:0,y:120,rotation:-4}},{{opacity:1,y:0,rotation:-2,duration:0.5,ease:"power3.out"}},{s["out_in"]-0.1:.3f});')
tw(f'tl.fromTo("#pb",{{opacity:0,y:120,rotation:4}},{{opacity:1,y:0,rotation:2,duration:0.5,ease:"power3.out"}},{s["out_in"]+0.05:.3f});')
tw(f'tl.fromTo("#dw i",{{scaleX:0}},{{scaleX:1,duration:0.45,ease:"power2.out"}},{t2073-0.1:.3f});')
tw(f'tl.fromTo("#dw span",{{opacity:0}},{{opacity:1,duration:0.2}},{t2073+0.1:.3f});')
tw(f'tl.fromTo("#dx",{{opacity:0,scale:0}},{{opacity:1,scale:1,duration:0.25}},{t2073+0.35:.3f});')
tw(f'tl.fromTo("#dl i",{{scaleX:0}},{{scaleX:1,duration:0.45,ease:"power2.out"}},{t2073+0.45:.3f});')
tw(f'tl.fromTo("#dl span",{{opacity:0}},{{opacity:1,duration:0.2}},{t2073+0.7:.3f});')
tw(f'tl.fromTo("#dlab",{{opacity:0}},{{opacity:1,duration:0.3}},{t2073+0.8:.3f});')
sfx("draw", t2073 - 0.1, 0.45); sfx("draw", t2073 + 0.45, 0.45)
tw(f'tl.fromTo("#bu",{{opacity:0,scale:0.5}},{{opacity:1,scale:1,duration:0.4,ease:"back.out(2)"}},{t1040-0.05:.3f});')
sfx("pop", t1040, 0.6)

# ---- 6. Booking RM500
s = seg(5)
t500 = w("500")
clip('''<div class="book">
  <div class="kicker" id="bk">BOOKING</div>
  <div class="bignum" id="b500"><span class="cur">RM</span>500</div>
  <div class="pill dark" id="bsaja">SAHAJA!</div>
</div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.2, "center", track=3)
tw(f'tl.fromTo("#bk",{{opacity:0,y:-40}},{{opacity:1,y:0,duration:0.25,ease:"power3.out"}},{s["out_in"]:.3f});')
tw(f'tl.fromTo("#b500",{{scale:2.6,opacity:0}},{{scale:1,opacity:1,duration:0.22,ease:"power4.in"}},{t500-0.18:.3f});')
tw(f'tl.fromTo(".book",{{x:-14}},{{x:0,duration:0.3,ease:"elastic.out(1,0.3)"}},{t500+0.04:.3f});')
sfx("stamp", t500 + 0.02, 0.7); sfx("coin", t500 + 0.08, 0.55)
tw(f'tl.fromTo("#bsaja",{{opacity:0,scale:0.4}},{{opacity:1,scale:1,duration:0.3,ease:"back.out(2.5)"}},{w("ringgit", after=28.0):.3f});')

# ---- 7. Free legal fees checklist
s = seg(6)
items = [("Yuran Guaman SPA", w("guaman")), ("MOT", w("mot")), ("Disbursement SPA", w("disbursement"))]
rows = "".join(f'<div class="ck" id="ck{k}"><span class="box"><svg viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6.5"/></svg></span>{html.escape(n)}</div>'
               for k, (n, _) in enumerate(items))
clip(f'''<div class="list"><div class="kicker">BONUS PEMBELI</div>{rows}
  <div class="stamp green" id="free">PERCUMA</div></div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.3, "center", track=3)
for k, (_, at) in enumerate(items):
    tw(f'tl.fromTo("#ck{k}",{{opacity:0,x:-120}},{{opacity:1,x:0,duration:0.3,ease:"power3.out"}},{at-0.2:.3f});')
    tw(f'tl.fromTo("#ck{k} svg path",{{strokeDashoffset:30}},{{strokeDashoffset:0,duration:0.25}},{at+0.05:.3f});')
    sfx("tick", at + 0.05, 0.6); sfx("pop", at - 0.15, 0.3)
tf = w("percuma")
tw(f'tl.fromTo("#free",{{scale:3,opacity:0,rotation:-16}},{{scale:1,opacity:1,rotation:{T["stamp_rot"]},duration:0.2,ease:"power4.in"}},{tf-0.08:.3f});')
sfx("stamp", tf + 0.1, 0.8); sfx("ding", tf + 0.15, 0.3)

# ---- 8. 100% financing
s = seg(7)
t100 = w("100")
C = 2 * 3.14159 * 150
clip(f'''<div class="fin">
  <div class="kicker">PEMBIAYAAN SEHINGGA</div>
  <div class="ring"><svg viewBox="0 0 360 360"><circle cx="180" cy="180" r="150" class="trk"/>
    <circle id="arc" cx="180" cy="180" r="150" class="arc" style="stroke-dasharray:{C:.1f};stroke-dashoffset:{C:.1f}"/></svg>
    <div class="pct"><span id="pct">0</span>%</div></div>
  <div class="note" id="fnote">*untuk pembeli yang layak</div>
</div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.25, "center", track=3)
tw(f'tl.fromTo(".fin",{{opacity:0,y:60}},{{opacity:1,y:0,duration:0.35,ease:"power3.out"}},{s["out_in"]-0.05:.3f});')
tw(f'tl.fromTo("#arc",{{strokeDashoffset:{C:.1f}}},{{strokeDashoffset:0,duration:0.9,ease:"power2.inOut"}},{t100-0.55:.3f});')
tw(f'const fc={{v:0}};tl.fromTo(fc,{{v:0}},{{v:100,duration:0.9,ease:"power2.inOut",onUpdate:()=>{{document.getElementById("pct").textContent=Math.round(fc.v)}}}},{t100-0.55:.3f});')
sfx("riser", t100 - 1.0, 0.3); sfx("ding", t100 + 0.35, 0.5)
tw(f'tl.fromTo("#fnote",{{opacity:0}},{{opacity:1,duration:0.3}},{w("layak")-0.4:.3f});')

# ---- 9-10. Location map: L = nearby amenities (seg 8), F = Putrajaya/Bangi/KLIA (seg 9).
# They play back to back in A/C; in B the F half opens the film on its own.
s9, s10 = seg(8), seg(9)
pins = [("sekolah", "Sekolah", "school", -250, -330), ("masjid", "Masjid", "mosque", 260, -260),
        ("kemudahan", "Kemudahan Harian", "shop", -200, 260)]
far = [("putra", "Putrajaya", 0, -560), ("bangi", "Bangi", 330, -470), ("klia", "KLIA", -330, 330)]
ICONS = {
    "school": '<path d="M12 3L1 9l11 6 9-4.9V17h2V9L12 3zm-6 10.2V17l6 3.3 6-3.3v-3.8L12 16.5 6 13.2z"/>',
    "mosque": '<path d="M12 2s-4 3-4 6h8c0-3-4-6-4-6zM6 10v10H3v2h18v-2h-3V10H6zm5 3h2v7h-2v-7zM2 7h2v13H2zM20 7h2v13h-2z"/>',
    "shop": '<path d="M4 4h16l1.5 6H2.5L4 4zm-1 8h18v9H3v-9zm4 2v5h4v-5H7z"/>',
}
ROADS = ('<svg class="roads" viewBox="0 0 1080 1500" preserveAspectRatio="none">'
         '<path d="M-40 980 C 300 900, 500 820, 1120 640"/><path d="M380 -20 C 460 400, 560 700, 640 1520"/>'
         '<path d="M-40 360 C 380 520, 700 520, 1120 300"/><path d="M120 1520 C 300 1200, 420 900, 540 750"/></svg>')
HOME = ('<div class="home" id="{p}home"><span class="pulse"></span><span class="pin"><svg viewBox="0 0 24 24"><path d="M12 3l9 8h-3v9h-5v-6h-2v6H6v-9H3z"/></svg></span>'
        '<b>J3 Residence</b><small>Taman Jenderam Lestari, Dengkil</small></div>')
def pois_html(p):
    return "".join(f'<div class="poi" id="{p}poi{k}" style="left:calc(50% + {x}px);top:calc(50% + {y}px)">'
                   f'<span class="ic"><svg viewBox="0 0 24 24">{ICONS[ic]}</svg></span>{name}</div>'
                   for k, (_, name, ic, x, y) in enumerate(pins))

back_to_back = s10["out_in"] > s9["out_in"] and s10["out_in"] - s9["out_out"] < 0.5
# L: amenities
l_in = s9["out_in"] - 0.25
l_out = (s10["out_in"] - 0.1) if back_to_back else (s9["out_out"] + 0.3)
clip(f'<div class="map" id="lmap">{ROADS}{pois_html("l")}{HOME.format(p="l")}</div>', l_in, l_out - l_in, "full", track=3)
tw(f'tl.fromTo("#lmap .roads path",{{strokeDashoffset:1600}},{{strokeDashoffset:0,duration:1.2,ease:"power2.out"}},{s9["out_in"]-0.2:.3f});')
tw(f'tl.fromTo("#lhome",{{scale:0,opacity:0}},{{scale:1,opacity:1,duration:0.45,ease:"back.out(2)"}},{w("lokasi")-0.2:.3f});')
tw(f'tl.fromTo("#lhome .pulse",{{scale:0.6,opacity:0.8}},{{scale:2.4,opacity:0,duration:1.2,repeat:{max(1,int((l_out-l_in)/1.2))},ease:"power1.out"}},{w("lokasi"):.3f});')
sfx("pop", w("lokasi"), 0.6)
for k, (word, *_r) in enumerate(pins):
    at = w(word)
    tw(f'tl.fromTo("#lpoi{k}",{{scale:0,opacity:0}},{{scale:1,opacity:1,duration:0.35,ease:"back.out(2.2)"}},{at-0.08:.3f});')
    sfx("pop", at - 0.02, 0.5)

# F: cities
f_in = l_out if back_to_back else max(0.0, s10["out_in"] - 0.25)
f_out = s10["out_out"] + (0.3 if back_to_back else 0.12)
clip(f'<div class="map" id="fmap">{ROADS}{pois_html("f") if back_to_back else ""}'
     + "".join(f'<svg class="route" id="rt{k}" viewBox="-540 -750 1080 1500"><path d="M0 0 L{x} {y}"/></svg>'
               f'<div class="city" id="city{k}" style="left:calc(50% + {x}px);top:calc(50% + {y}px)"><i></i>{name}</div>'
               for k, (_, name, x, y) in enumerate(far))
     + HOME.format(p="f") + '</div>', f_in, f_out - f_in, "full", track=3)
if back_to_back:
    tw(f'tl.to("#fmap .poi",{{opacity:0.35,duration:0.3}},{s10["out_in"]-0.1:.3f});')
else:   # opening the film: draw the map in
    tw(f'tl.fromTo("#fmap .roads path",{{strokeDashoffset:1600}},{{strokeDashoffset:0,duration:1.2,ease:"power2.out"}},{f_in:.3f});')
    tw(f'tl.fromTo("#fhome",{{scale:0,opacity:0}},{{scale:1,opacity:1,duration:0.45,ease:"back.out(2)"}},{f_in+0.1:.3f});')
    sfx("pop", f_in + 0.15, 0.5)
tw(f'tl.fromTo("#fhome .pulse",{{scale:0.6,opacity:0.8}},{{scale:2.4,opacity:0,duration:1.2,repeat:{max(1,int((f_out-f_in)/1.2))},ease:"power1.out"}},{f_in:.3f});')
tw(f'tl.fromTo("#fmap",{{scale:1}},{{scale:0.86,duration:{f_out-f_in:.3f},ease:"power1.inOut"}},{f_in:.3f});')
far_words = [w("jaya") - 0.35, w("bangi"), w("klia")]
for k, at in enumerate(far_words):
    tw(f'tl.fromTo("#rt{k} path",{{strokeDashoffset:800}},{{strokeDashoffset:0,duration:0.45,ease:"power2.out"}},{at-0.1:.3f});')
    tw(f'tl.fromTo("#city{k}",{{scale:0,opacity:0}},{{scale:1,opacity:1,duration:0.35,ease:"back.out(2)"}},{at+0.2:.3f});')
    sfx("swipe", at - 0.1, 0.45); sfx("pop", at + 0.22, 0.45)

# ---- 11. Completion date
s = seg(10)
tfeb = w("februari")
clip('''<div class="cal">
  <div class="kicker">DIJANGKA SIAP</div>
  <div class="calcard" id="calc"><div class="calhead">2028</div><div class="calbody" id="calm">FEB</div></div>
</div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.25, "center", track=3)
tw(f'tl.fromTo(".cal .kicker",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.3}},{s["out_in"]:.3f});')
tw(f'tl.fromTo("#calc",{{rotationX:-90,opacity:0,transformPerspective:900}},{{rotationX:0,opacity:1,duration:0.5,ease:"back.out(1.6)"}},{tfeb-0.25:.3f});')
sfx("whoosh", tfeb - 0.3, 0.35); sfx("ding", tfeb + 0.25, 0.4)

# ---- 12-14. CTA / end card
s12, s13, s14 = seg(11), seg(12), seg(13)
clip('''<div class="cta">
  <div class="kicker">PENDAFTARAN AWAL</div>
  <div class="ctabig" id="ctab">FASA 3</div>
  <div class="pill gold big" id="ctap">DAFTAR SEKARANG</div>
</div>''', s12["out_in"] - 0.1, s13["out_in"] - s12["out_in"], "center", track=3)
tw(f'tl.fromTo("#ctab",{{scale:0.5,opacity:0}},{{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"}},{w("daftar")-0.15:.3f});')
tw(f'tl.fromTo("#ctap",{{scaleX:0}},{{scaleX:1,duration:0.35,ease:"power3.out"}},{w("awal"):.3f});')
sfx("riser", w("daftar") - 1.2, 0.3); sfx("stamp", w("daftar") - 0.02, 0.45)
end_in = s13["out_in"] - 0.1
clip('''<div class="endcard">
  <div class="logo"><span>J3</span>RESIDENCE</div>
  <div class="q" id="eq">Nak tahu lebih lanjut?</div>
  <div class="phone" id="eph"><svg viewBox="0 0 24 24"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1z"/></svg>HUBUNGI SAYA SEKARANG</div>
  <div class="num" id="enum">Pendaftaran Fasa 3 kini dibuka</div>
  <div class="facts" id="efacts">RM430K · Freehold · Booking RM500 · Siap Feb 2028</div>
  <div class="loc"><svg viewBox="0 0 24 24"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>Taman Jenderam Lestari, Dengkil</div>
</div>''', end_in, DURATION - end_in, "full", id_="end", track=3)
tw(f'tl.fromTo("#end",{{opacity:0}},{{opacity:1,duration:0.35}},{end_in:.3f});')
tw(f'tl.fromTo("#end .logo",{{y:-50,opacity:0}},{{y:0,opacity:1,duration:0.5,ease:"power3.out"}},{end_in:.3f});')
tw(f'tl.fromTo("#eq",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.35}},{s13["out_in"]:.3f});')
tw(f'tl.fromTo("#eph",{{scale:0.6,opacity:0}},{{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"}},{s14["out_in"]-0.05:.3f});')
tw(f'tl.fromTo("#eph",{{scale:1}},{{scale:1.06,duration:0.45,yoyo:true,repeat:3,ease:"sine.inOut",immediateRender:false}},{s14["out_out"]:.3f});')
tw(f'tl.fromTo("#enum",{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.35}},{s14["out_in"]+0.35:.3f});')
tw(f'tl.fromTo("#efacts",{{opacity:0}},{{opacity:1,duration:0.4}},{s14["out_out"]+0.1:.3f});')
sfx("whoosh", end_in - 0.1, 0.4); sfx("ding", s14["out_in"], 0.45); sfx("coin", s14["out_out"] + 0.1, 0.35)

# ================================================================ CAPTIONS (word-level)
cap_n = 0
def owner(st, en):
    best, bo = None, 0.0
    for s_ in SEG:
        o = min(en, s_["src_out"]) - max(st, s_["src_in"])
        if o > bo: best, bo = s_, o
    return best
all_chunks = []
for s in PLAY:
    ws = [(wd, max(st, s["src_in"]), en) for wd, st, en in WORDS if owner(st, en) is s]
    toks = []
    for wd, st, en in ws:
        fixed = FIX.get(wd, wd)
        parts = fixed.split(" ")
        span = (en - st) / len(parts)
        for j, p in enumerate(parts):
            toks.append((p, out(st + j * span)))
    # merge "100" "%"
    merged = []
    for p, at in toks:
        if p == "%" and merged:
            merged[-1] = (merged[-1][0] + "%", merged[-1][1])
        else:
            merged.append((p, at))
    if s is PLAY[0]:
        merged[0] = (merged[0][0], s["out_in"])
    # chunk: max 3 words, break after punctuation
    chunks, cur = [], []
    for p, at in merged:
        cur.append((p, at))
        if len(cur) == 4 or p[-1] in ".?" or (p[-1] == "," and len(cur) >= 2):
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    for ch in chunks:
        all_chunks.append((ch, s))
for c_i, (ch, s) in enumerate(all_chunks):
        st = ch[0][1]
        en = all_chunks[c_i + 1][0][0][1] if c_i + 1 < len(all_chunks) else s["out_out"] + 0.4
        if en - st > 3.0: en = max(st + 1.6, s["out_out"] + 0.3)
        cap_n += 1
        spans = "".join(f'<span id="cw{cap_n}_{j}">{html.escape(p)}</span> ' for j, (p, _) in enumerate(ch))
        clip(f'<div class="cap" id="cap{cap_n}">{spans.strip()}</div>', st, en - st, "capwrap", track=5)
        tw(f'tl.fromTo("#cap{cap_n}",{{y:24,opacity:0}},{{y:0,opacity:1,duration:0.12,ease:"power2.out"}},{st:.3f});')
        on, off = T["cap_on"], T["cap_off"]
        for j, (_, at) in enumerate(ch):
            nxt = ch[j+1][1] if j + 1 < len(ch) else None
            if T["cap"] == "karaoke":
                tw(f'tl.fromTo("#cw{cap_n}_{j}",{{color:"{off}",scale:1}},{{color:"{on}",scale:1.1,duration:0.08}},{at:.3f});')
                if nxt: tw(f'tl.to("#cw{cap_n}_{j}",{{color:"{off}",scale:1,duration:0.08}},{nxt:.3f});')
            elif T["cap"] == "bar":
                tw(f'tl.fromTo("#cw{cap_n}_{j}",{{color:"{off}"}},{{color:"{on}",duration:0.1}},{at:.3f});')
                if nxt: tw(f'tl.to("#cw{cap_n}_{j}",{{color:"{off}",duration:0.15}},{nxt:.3f});')
            else:  # box: active word jumps into a lime block
                tw(f'tl.fromTo("#cw{cap_n}_{j}",{{backgroundColor:"rgba(198,255,61,0)",color:"{off}",scale:1,rotation:0}},'
                   f'{{backgroundColor:"rgba(198,255,61,1)",color:"{on}",scale:1.12,rotation:-3,duration:0.06}},{at:.3f});')
                if nxt: tw(f'tl.to("#cw{cap_n}_{j}",{{backgroundColor:"rgba(198,255,61,0)",color:"{off}",scale:1,rotation:0,duration:0.06}},{nxt:.3f});')

# ================================================================ WRITE
CSS = open(os.path.join(HERE, "style.css")).read()
if T["css"]:
    CSS += "\n/* ---- theme: " + T["name"] + " ---- */\n" + open(os.path.join(HERE, T["css"])).read()
doc = f'''<!doctype html>
<html lang="ms" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <!-- GENERATED by tools/build.py from the EDL. Edit build.py / style.css, not this file. -->
    <script src="vendor/gsap.min.js"></script>
    <style>
{CSS}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main"{' data-motion-blur="on"' if V["blur"] else ""} data-start="0" data-duration="{DURATION}" data-width="1080" data-height="1920">
      {chr(10).join("      " + e for e in elements)}
      {chr(10).join("      " + a for a in audio)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join("      " + x for x in tweens)}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''
doc = doc.replace('<html lang="ms"', f'<html lang="ms" data-variant="{THEME}"')
open(os.path.join(ROOT, "index.html"), "w").write(doc)   # one root per project; pick the theme by argv
json.dump({"duration": DURATION, "segments": SEG}, open(os.path.join(HERE, "edl_out.json"), "w"), indent=1)
print(f"index.html = {V['name']} · {len(SHOTS)} shots · duration {DURATION}s · {len(SEG)} voice clips · {sfx_n[0]} sfx · {cap_n} caption chunks")
for s_ in PLAY:
    print(f'  {s_["out_in"]:6.2f}-{s_["out_out"]:6.2f}  <- src {s_["src_in"]:5.2f}-{s_["src_out"]:5.2f}  {s_["note"]}')
