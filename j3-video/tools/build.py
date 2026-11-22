"""Build index.html for the Taman Jenderam Lestari (Fasa 3) promo — voiceover 2.

The voiceover is cut in-composition: each kept phrase is its own <audio> clip
(data-media-start = source in-point). Every animation, SFX hit and caption word
is timed from the Whisper word timestamps re-mapped through the EDL.

    python3 -I tools/build.py a|b|c     # writes index.html for one variant
A · Lembut     : natural order, crossfade + swipe
B · Sinematik  : sold-out hook first, zoom-through / light leak / dip-to-black
C · Pantas     : price hook first, ~1.2 s cuts, whip-pan (motion blur) / punch / glitch
No on-screen "J3 Residence" anywhere (brand tag, map, end card, captions).
"""
import json, html, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORDS = json.load(open(os.path.join(HERE, "voice2_words.json")))   # [[word, start, end], ...]
MAP = json.load(open(os.path.join(HERE, "map_meta.json")))

THEMES = {
    "a": dict(css=None, cap="karaoke", sfx_gain=1.0, sfx_map={}, music=0.16, frame=False,
              stamp_rot=-8, cap_on="#F5C24C", cap_off="#ffffff"),
    "b": dict(css="theme-b.css", cap="bar", sfx_gain=0.6, sfx_map={"stamp": "pop", "coin": "ding", "riser": "whoosh"},
              music=0.2, frame=True, stamp_rot=0, cap_on="#D9B97E", cap_off="#F3EDE3"),
    "c": dict(css="theme-c.css", cap="box", sfx_gain=1.15, sfx_map={}, music=0.18, frame=False,
              stamp_rot=-10, cap_on="#0B0B0B", cap_off="#ffffff"),
}
VARIANTS = {
    "a": dict(name="A · Lembut (crossfade)", order=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], blur=False),
    "b": dict(name="B · Sinematik (zoom-through, light leak, dip)", order=[2, 0, 1, 3, 4, 5, 6, 7, 8, 9, 10], blur=False),
    "c": dict(name="C · Pantas (whip, punch, glitch)", order=[7, 0, 1, 2, 3, 4, 5, 6, 8, 9, 10], blur=True),
}
KEY = sys.argv[1] if len(sys.argv) > 1 else "a"
V = VARIANTS[KEY]
T = THEMES[KEY]

# ---------------------------------------------------------------- EDL (voice 2)
# (source_in, source_out, gap_before, note) — cut points sit in measured silences
EDL = [
    (0.00, 5.44, 0.15, "Kalau korang cari rumah tak jauh dari Putrajaya & Cyberjaya, boleh tengok projek ni."),
    (5.86, 7.50, 0.14, "Taman Jenderam Lestari."),          # CUT 7.50-8.46 repeated 'Jendram.'
    (8.84, 11.14, 0.18, "Fasa 1 dan 2 dah habis dijual."),
    (11.39, 14.69, 0.12, "Dan sekarang, Fasa 3 pula dibuka untuk pendaftaran."),
    (15.03, 21.39, 0.18, "Freehold, 3 / 3+1 bilik tidur, 2 bilik air."),
    (21.75, 27.88, 0.14, "Saiz tanah 20x73, binaan 1,040 kps."),
    (28.17, 34.36, 0.20, "Lokasi: sekolah, Putrajaya, Bangi, KLIA."),
    (34.65, 39.84, 0.18, "Harga RM430 ribu, booking RM500."),
    (40.19, 43.43, 0.12, "Kos guaman SPA & MOT ditanggung pemaju."),
    (43.74, 46.80, 0.16, "Siap Februari 2028."),
    (47.05, 50.10, 0.20, "Nak tahu lebih lanjut, hubungi saya."),
]
END_HOLD = 3.2

SEG = [None] * len(EDL)
t = 0.0
for n, i in enumerate(V["order"]):
    a, b, gap, note = EDL[i]
    if n == 0:
        gap = 0.15
    elif V["order"][n - 1] != i - 1:
        gap = max(gap, 0.25)
    t += gap
    SEG[i] = dict(i=i, src_in=a, src_out=b, out_in=round(t, 3), out_out=round(t + (b - a), 3), note=note)
    t += b - a
PLAY = [SEG[i] for i in V["order"]]
DURATION = round(t + END_HOLD, 2)
S = lambda i: SEG[i]


def out(src):
    for s in SEG:
        if s["src_in"] - 0.06 <= src <= s["src_out"] + 0.06:
            return round(s["out_in"] + (src - s["src_in"]), 3)
    raise ValueError(f"time {src} was cut")


def w(text, nth=1, after=0.0):
    k = 0
    for word, s, e in WORDS:
        if s + 0.001 >= after and word.lower().strip(".,?%") == text.lower():
            k += 1
            if k == nth:
                return out(max(s, next(x["src_in"] for x in SEG if x["src_in"] - 0.3 <= s <= x["src_out"])))
    raise KeyError(text)


elements, tweens, audio = [], [], []


def clip(html_inner, start, dur, cls="", style="", id_=None, track=1):
    clip.n = getattr(clip, "n", 0) + 1
    idattr = f' id="{id_ or (cls.split()[0] if cls else "el") + str(clip.n)}"'
    elements.append(f'<div{idattr} class="clip {cls}" data-start="{start:.3f}" data-duration="{dur:.3f}" '
                    f'data-track-index="{track}" style="{style}">{html_inner}</div>')


sfx_n = [0]
def sfx(name, at, vol=0.6, dur=None):
    name = T["sfx_map"].get(name, name); vol = round(min(1.0, vol * T["sfx_gain"]), 3)
    d = dur or dict(whoosh=0.7, stamp=0.6, pop=0.12, tick=0.05, ding=1.4, coin=0.9, riser=1.3, swipe=0.35, draw=0.8)[name]
    sfx_n[0] += 1
    audio.append(f'<audio id="sfx{sfx_n[0]}" src="assets/sfx/{name}.wav" data-start="{max(0, at):.3f}" '
                 f'data-duration="{d:.3f}" data-volume="{vol}" data-track-index="9"></audio>')


def tw(js):
    tweens.append(js)


# ---------------------------------------------------------------- audio
for s in PLAY:
    audio.append(f'<audio id="vo{s["i"]}" src="assets/audio/voice2.mp3" data-start="{s["out_in"]:.3f}" '
                 f'data-duration="{s["src_out"]-s["src_in"]:.3f}" data-media-start="{s["src_in"]:.3f}" '
                 f'data-volume="1" data-fade-in="0.02" data-fade-out="0.04" data-track-index="8"></audio>'
                 f'<!-- {html.escape(s["note"])} -->')
audio.append(f'<audio id="music" src="assets/sfx/music_bed.wav" data-start="0" data-duration="{DURATION:.3f}" '
             f'data-volume="{T["music"]}" data-fade-in="0.6" data-fade-out="1.6" data-track-index="10"></audio>')

# ================================================================ SHOTS + TRANSITIONS
VLEN = {"row": 8.0, "landw": 6.5, "estatel": 21.0, "orbit": 12.0, "roofs": 8.0, "shop": 18.0}


def sh(src, a, b, tin="xfade", d=0.3, off=0.0, k0=(1.0, 0, 0), k1=(1.06, 0, 0), pos="50% 50%"):
    return dict(src=src, a=round(a, 3), b=round(b, 3), tin=tin, d=d, off=off, k0=k0, k1=k1, pos=pos)


I = lambda i: S(i)["out_in"]
H_BOOK = w("booking")
if KEY == "a":      # natural order, soft crossfades
    SHOTS = [
        sh("vid:estatel", 0, I(1), "fadein", off=0, k0=(1.2, 0, 0), k1=(1.0, 0, 0)),
        sh("vid:orbit", I(1), I(2), off=0, k0=(1.1, 0, 0), k1=(1.0, 0, 0)),
        sh("vid:row", I(2), I(3), off=1.0, k0=(1.1, 0, 0), k1=(1.0, 0, 0)),
        sh("vid:estatel", I(3), I(4), off=6.0, k0=(1.0, 0, 0), k1=(1.12, 0, 0)),
        sh("img:front", I(4), I(5), k0=(1.2, -300, 40), k1=(1.3, 120, 0), pos="50% 60%"),
        sh("solid:planbg", I(5), I(6)),
        sh("map:loc", I(6), I(7)),
        sh("img:street", I(7), H_BOOK, k0=(1.08, 520, 0), k1=(1.12, -100, 0)),
        sh("vid:orbit", H_BOOK, I(8), off=4.0, k1=(1.08, 0, 0)),
        sh("img:corner", I(8), I(9), k0=(1.25, -200, 0), k1=(1.1, 200, 0), pos="40% 50%"),
        sh("vid:roofs", I(9), I(10), off=0, k0=(1.1, 0, 0), k1=(1.0, 0, 0)),
        sh("img:front", I(10), DURATION, k0=(1.1, 0, 0), k1=(1.28, 0, -40), pos="50% 55%"),
    ]
    for x in SHOTS[1:]:
        x["d"] = 0.4

elif KEY == "b":    # cinematic, order 2,0,1,3..: long takes, motivated transitions
    SHOTS = [
        sh("vid:row", 0, I(0), "fadein", off=0, k0=(1.15, 0, 0), k1=(1.0, 0, 0)),
        sh("vid:estatel", I(0), I(1), "zoomthru", 0.6, off=0, k0=(1.2, 0, 0), k1=(1.02, 0, 0)),
        sh("vid:orbit", I(1), I(3), "leak", 0.7, off=0, k0=(1.1, 0, 0), k1=(1.0, 0, 0)),
        sh("vid:estatel", I(3), I(4), "dip", 0.6, off=9.0, k0=(1.0, 0, 0), k1=(1.12, 0, 0)),
        sh("img:front", I(4), I(5), "zoomthru", 0.6, k0=(1.15, -150, 30), k1=(1.24, 60, 0), pos="50% 60%"),
        sh("solid:planbg", I(5), I(6), "dip", 0.6),
        sh("map:loc", I(6), I(7), "leak", 0.7),
        sh("img:street", I(7), H_BOOK, "dip", 0.6, k0=(1.06, 450, 0), k1=(1.1, 150, 0)),
        sh("vid:orbit", H_BOOK, I(8), "zoomthru", 0.6, off=5.0, k1=(1.08, 0, 0)),
        sh("img:corner", I(8), I(9), "leak", 0.7, k0=(1.2, -150, 0), k1=(1.12, 120, 0), pos="40% 50%"),
        sh("vid:roofs", I(9), I(10), "zoomthru", 0.6, off=0, k0=(1.1, 0, 0), k1=(1.0, 0, 0)),
        sh("img:front", I(10), DURATION, "dip", 0.6, k0=(1.1, 0, 0), k1=(1.25, 0, -40), pos="50% 55%"),
    ]

else:               # fast social cut, order 7,0,1..: new shot ~every 1.2 s on word starts
    POOLS = {
        7: [("vid:orbit", 1.0), ("img:street", 0), ("vid:row", 3.0), ("img:front", 0)],
        0: [("vid:estatel", 0.0), ("vid:shop", 6.0), ("vid:estatel", 14.0)],
        1: [("vid:orbit", 3.0)],
        2: [("vid:row", 0.0), ("vid:roofs", 0.0)],
        3: [("vid:estatel", 8.0), ("vid:roofs", 2.0), ("vid:estatel", 15.0)],
        4: [("img:front", 0), ("img:corner", 0), ("vid:orbit", 6.0), ("img:street", 0)],
        8: [("img:corner", 0), ("vid:roofs", 4.0)],
        9: [("vid:orbit", 9.0), ("vid:row", 3.0)],
    }
    PANS = [((1.14, -320, 0), (1.24, -80, 0)), ((1.14, 320, 0), (1.24, 80, 0)),
            ((1.3, 0, 0), (1.14, 0, 0)), ((1.12, -560, 0), (1.2, -260, 0))]
    word_starts = sorted(out(st) for _, st, en in WORDS if any(x["src_in"] <= st < x["src_out"] for x in PLAY))
    SHOTS, nimg = [], 0
    for n, s_ in enumerate(PLAY):
        a = 0.0 if n == 0 else s_["out_in"]
        b = PLAY[n + 1]["out_in"] if n + 1 < len(PLAY) else DURATION
        i = s_["i"]
        first = not SHOTS
        if i == 5:
            SHOTS.append(sh("solid:planbg", a, b, "whip", 0.24)); continue
        if i == 6:
            SHOTS.append(sh("map:loc", a, b, "whip", 0.24)); continue
        if i == 10:
            SHOTS.append(sh("img:front", a, b, "whip", 0.24, k0=(1.1, 0, 0), k1=(1.28, 0, -40), pos="50% 55%")); continue
        cuts = [a]
        for ws in word_starts:
            if a + 1.0 <= ws <= b - 0.8 and ws - cuts[-1] >= 1.1:
                cuts.append(ws)
        cuts.append(b)
        used = {}
        for j in range(len(cuts) - 1):
            src, off = POOLS[i][j % len(POOLS[i])]
            tin = "fadein" if first and j == 0 else ("whip" if j == 0 else ("punch" if j % 2 else "glitch"))
            if src.startswith("vid:"):
                need = cuts[j + 1] - cuts[j] + 0.3
                base = off + used.get((src, off), 0.0)
                if base + need > VLEN[src[4:]]:
                    base = max(0.0, VLEN[src[4:]] - need - 0.05)
                used[(src, off)] = used.get((src, off), 0.0) + need
                SHOTS.append(sh(src, cuts[j], cuts[j + 1], tin, 0.24, off=round(base, 3), k1=(1.1, 0, 0)))
            else:
                k0, k1 = PANS[nimg % len(PANS)]; nimg += 1
                SHOTS.append(sh(src, cuts[j], cuts[j + 1], tin, 0.24, k0=k0, k1=k1, pos="50% 55%"))

TR = dict(fadein=(0, 0), xfade=(1, 0), zoomthru=(1, 0), leak=(1, 0), dip=(0, 0), whip=(0.5, 0.5), punch=(0, 0), glitch=(0, 0))
IR = ",immediateRender:false"
MAP_WIN = None
for k, x in enumerate(SHOTS):
    nxt = SHOTS[k + 1] if k + 1 < len(SHOTS) else None
    pre = TR[x["tin"]][0] * x["d"] if k else 0
    post = TR[nxt["tin"]][1] * nxt["d"] if nxt else 0
    st = max(0.0, x["a"] - pre); en = min(DURATION, x["b"] + post); dur = en - st
    pid = f"plate{k}"
    kind, name = x["src"].split(":")
    k0, k1 = x["k0"], x["k1"]
    if x["src"] == "vid:row":       # developer banner (logo + phone no.) on the right edge: push it off-frame
        k0, k1 = (1.3, 150, 0), (1.36, 170, 0)
    if kind == "vid":
        assert x["off"] + dur <= VLEN[name] + 0.05, (KEY, name, x["off"], dur)
        elements.append(f'<div id="{pid}" class="pw"><video id="{pid}v" class="clip plate vid" src="assets/video/{name}.mp4" muted playsinline '
                        f'data-start="{st:.3f}" data-duration="{dur:.3f}" data-media-start="{x["off"]:.3f}" data-track-index="0"></video></div>')
        tw(f'tl.fromTo("#{pid}v",{{scale:{k0[0]},x:{k0[1]},y:{k0[2]}}},{{scale:{k1[0]},x:{k1[1]},y:{k1[2]},duration:{dur:.3f},ease:"none"}},{st:.3f});')
    elif kind == "img":
        clip(f'<img src="assets/img/{name}.jpg" style="object-position:{x["pos"]}" alt="">', st, dur, "plate", id_=pid, track=0)
        tw(f'tl.fromTo("#{pid} img",{{xPercent:-50,scale:{k0[0]},x:{k0[1]},y:{k0[2]}}},{{xPercent:-50,scale:{k1[0]},x:{k1[1]},y:{k1[2]},duration:{dur:.3f},ease:"none"}},{st:.3f});')
    elif kind == "map":
        MAP_WIN = (st, en, pid)     # the map plate itself is built in the location scene
        elements.append(f'<!--MAP:{pid}-->')
    else:
        clip("", st, dur, "plate solid " + name, id_=pid, track=0)

    a, d, tin = x["a"], x["d"], x["tin"]
    prev = f"#plate{k-1}" if k else None
    if tin == "fadein":
        tw(f'tl.fromTo("#{pid}",{{opacity:0.1}},{{opacity:1,duration:0.35}},{st:.3f});')
    elif tin == "xfade":
        tw(f'tl.fromTo("#{pid}",{{opacity:0}},{{opacity:1,duration:{d},ease:"power1.inOut"}},{a-d:.3f});')
        sfx("swipe", a - d - 0.05, 0.3)
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

clip("", 0, DURATION, "shade", track=1)
if any(x["tin"] == "dip" for x in SHOTS): clip("", 0, DURATION, "dipov", id_="dipov", track=6)
if any(x["tin"] == "leak" for x in SHOTS): clip("", 0, DURATION, "leakov", id_="leakov", track=6)
if any(x["tin"] in ("punch", "glitch") for x in SHOTS): clip("", 0, DURATION, "flash", id_="flash", track=6)
if T["frame"]: clip('<div class="framebox"></div>', 0, DURATION, "frame", id_="frame", track=6)

tag_in = PLAY[2]["out_in"]
clip('<span class="dot"></span>TAMAN JENDERAM LESTARI <b>· FASA 3</b>', tag_in, DURATION - tag_in, "brandtag", id_="brandtag", track=2)
tw(f'tl.fromTo("#brandtag",{{opacity:0,y:-30}},{{opacity:1,y:0,duration:0.5,ease:"power3.out"}},{tag_in:.3f});')

PIN = '<svg viewBox="0 0 24 24"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>'

# ================================================================ SCENES
# ---- 0. Hook question: rumah dekat Putrajaya & Cyberjaya
s = S(0)
tpj, tcj, tpr = w("putra"), w("berjaya"), w("projek")
clip('''<div class="qhook">
  <div class="kicker" id="qk">CARI RUMAH TAK JAUH DARI</div>
  <div class="qh" id="q1">PUTRAJAYA</div>
  <div class="qh small" id="q2">&amp; CYBERJAYA?</div>
  <div class="pill gold" id="q3">TENGOK PROJEK NI ↓</div>
</div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.25, "center", track=3)
tw(f'tl.fromTo("#qk",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.35,ease:"power3.out"}},{s["out_in"]+0.1:.3f});')
tw(f'tl.fromTo("#q1",{{opacity:0,scale:1.8}},{{opacity:1,scale:1,duration:0.3,ease:"power4.out"}},{tpj-0.12:.3f});')
tw(f'tl.fromTo("#q2",{{opacity:0,x:200}},{{opacity:1,x:0,duration:0.35,ease:"power3.out"}},{tcj-0.3:.3f});')
tw(f'tl.fromTo("#q3",{{opacity:0,scale:0.6}},{{opacity:1,scale:1,duration:0.35,ease:"back.out(2)"}},{tpr-0.2:.3f});')
sfx("whoosh", s["out_in"] - 0.1, 0.35); sfx("stamp", tpj, 0.45); sfx("pop", tcj, 0.5); sfx("pop", tpr, 0.4)

# ---- 1. Title: Taman Jenderam Lestari
s = S(1)
clip(f'''<div class="titlecard" id="tc">
  <div class="kicker">PROJEK RUMAH TERES 1 TINGKAT</div>
  <h1>Taman Jenderam<br>Lestari</h1>
  <div class="loc" id="loc">{PIN}Jenderam Hilir, Dengkil</div>
</div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.3, "upper", track=3)
tw(f'tl.fromTo("#tc .kicker",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:0.3}},{s["out_in"]-0.05:.3f});')
tw(f'tl.fromTo("#tc h1",{{opacity:0,y:60,clipPath:"inset(0 0 100% 0)"}},{{opacity:1,y:0,clipPath:"inset(0 0 0% 0)",duration:0.5,ease:"power4.out"}},{w("taman"):.3f});')
tw(f'tl.fromTo("#loc",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.4,ease:"back.out(1.8)"}},{w("lestari"):.3f});')
sfx("pop", w("lestari"), 0.5)

# ---- 2. Fasa 1 & 2 sold out
s = S(2)
t1, t2, tj = w("1"), w("2"), w("dijual")
clip('''<div class="hook">
  <div class="hrow" id="h1"><span class="fasa">FASA 1</span><span class="stamp" id="st1">SOLD OUT</span></div>
  <div class="hrow" id="h2"><span class="fasa">FASA 2</span><span class="stamp" id="st2">SOLD OUT</span></div>
  <div class="hsub" id="hsub">HABIS DIJUAL</div>
</div>''', max(0, s["out_in"] - 0.1), s["out_out"] - max(0, s["out_in"] - 0.1) + 0.12, "center", track=3)
tw(f'tl.fromTo("#h1",{{x:-1100}},{{x:0,duration:0.35,ease:"power4.out"}},{t1-0.30:.3f});')
tw(f'tl.fromTo("#h2",{{x:1100}},{{x:0,duration:0.35,ease:"power4.out"}},{t2-0.25:.3f});')
for sid, at in (("st1", t1 + 0.12), ("st2", t2 + 0.12)):
    tw(f'tl.fromTo("#{sid}",{{scale:3.2,opacity:0,rotation:-14}},{{scale:1,opacity:1,rotation:{T["stamp_rot"]},duration:0.18,ease:"power4.in"}},{at:.3f});')
    tw(f'tl.fromTo(".hook",{{x:-12,y:8}},{{x:0,y:0,duration:0.25,ease:"elastic.out(1,0.3)"{IR}}},{at+0.18:.3f});')
    sfx("stamp", at + 0.15, 0.45)
tw(f'tl.fromTo("#hsub",{{opacity:0,y:40,scaleX:1.4}},{{opacity:1,y:0,scaleX:1,duration:0.4,ease:"power3.out"}},{tj-0.15:.3f});')
tw(f'tl.to(".hook",{{scale:0.8,opacity:0,duration:0.2,ease:"power2.in"}},{s["out_out"]-0.05:.3f});')

# ---- 3. Fasa 3 dibuka
s = S(3)
t3, tb = w("3"), w("dibuka")
clip('''<div class="f3">
  <div class="kicker" id="f3k">SEKARANG</div>
  <div class="f3big" id="f3big">FASA <em>3</em></div>
  <div class="pill gold" id="f3p">KINI DIBUKA · DAFTAR SEKARANG</div>
</div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.25, "center", track=3)
tw(f'tl.fromTo("#f3k",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.3}},{w("sekarang"):.3f});')
tw(f'tl.fromTo("#f3big",{{scale:0.4,opacity:0}},{{scale:1,opacity:1,duration:0.45,ease:"back.out(2.2)"}},{t3-0.12:.3f});')
tw(f'tl.fromTo("#f3p",{{scaleX:0,opacity:0}},{{scaleX:1,opacity:1,duration:0.35,ease:"power3.out"}},{tb-0.05:.3f});')
sfx("riser", t3 - 1.25, 0.25); sfx("ding", tb, 0.55)

# ---- 4. Freehold + rooms
s = S(4)
tfh, tpil, t2b = w("freehold"), w("pilihan"), w("2", after=20.0)
clip('''<div class="specs">
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
tw(f'tl.fromTo("#c2",{{opacity:0,y:80}},{{opacity:1,y:0,duration:0.4,ease:"back.out(1.7)"}},{t2b-0.05:.3f});')
sfx("pop", t2b, 0.55)

# ---- 5. Land size + built-up on floor plans
s = S(5)
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

# ---- 6. Location on a real satellite map: close (schools) -> zoom out (Putrajaya, Bangi, KLIA)
s = S(6)
mst, men, mpid = MAP_WIN
C, W_ = MAP["close"], MAP["wide"]
SX, SY = 400, 950                       # site lands here on screen in both plates
cox, coy = SX - C["pins"]["site"][0], SY - C["pins"]["site"][1]
wox, woy = SX - W_["pins"]["site"][0], SY - W_["pins"]["site"][1]
def mpin(cls, pid_, p, label, side="r"):
    return (f'<div class="mpin {cls} {side}" id="{pid_}" style="left:{p[0]}px;top:{p[1]}px">'
            f'<i></i><span>{label}</span></div>')
def layer(id_, P, inner):
    ox, oy = (cox, coy) if P is C else (wox, woy)
    return (f'<div class="mlayer" id="{id_}" style="left:{ox:.1f}px;top:{oy:.1f}px;width:{P["w"]}px;height:{P["h"]}px;'
            f'transform-origin:{P["pins"]["site"][0]}px {P["pins"]["site"][1]}px">{inner}</div>')
close_html = layer("mclose", C, '<img src="assets/img/map_close.jpg" alt="">')
close_pins = layer("mcloseP", C, mpin("school", "pn_sra", C["pins"]["sra"], "SRA Jenderam Hilir")
                   + mpin("school", "pn_skj", C["pins"]["skj"], "SK Jenderam", "t"))
routes = "".join(f'<path id="rt_{k}" d="M{W_["pins"]["site"][0]} {W_["pins"]["site"][1]} L{W_["pins"][k][0]} {W_["pins"][k][1]}"/>'
                 for k in ("putrajaya", "bangi", "klia"))
wide_html = layer("mwide", W_, '<img src="assets/img/map_wide.jpg" alt="">')
wide_pins = layer("mwideP", W_, f'<svg class="mroutes" viewBox="0 0 {W_["w"]} {W_["h"]}" width="{W_["w"]}" height="{W_["h"]}">{routes}</svg>'
                  + mpin("city", "pn_pj", W_["pins"]["putrajaya"], "Putrajaya")
                  + mpin("city", "pn_bg", W_["pins"]["bangi"], "Bangi", "l")
                  + mpin("city", "pn_kl", W_["pins"]["klia"], "KLIA"))
site_html = (f'<div class="msite" id="msite" style="left:{SX}px;top:{SY}px"><span class="pulse"></span><span class="pin">'
             f'<svg viewBox="0 0 24 24"><path d="M12 3l9 8h-3v9h-5v-6h-2v6H6v-9H3z"/></svg></span>'
             f'<b>Taman Jenderam Lestari</b></div>')
credit = '<div class="mcredit" data-layout-ignore>Imej satelit: Esri, Maxar, Earthstar Geographics · Data: © OpenStreetMap</div>'
clip(close_html + wide_html + '<div class="mshade"></div>' + credit, mst, men - mst, "plate mapplate", id_=mpid, track=0)
for i_, e_ in enumerate(elements):
    if e_ == f'<!--MAP:{mpid}-->':
        elements[i_] = elements.pop()       # keep the map plate in its shot slot (z-order)
        break
clip(close_pins + wide_pins + site_html, mst, men - mst, "mapover", id_="mapover", track=3)
tw(f'tl.fromTo("#mapover",{{opacity:0}},{{opacity:1,duration:0.3}},{mst:.3f});')
tlok, tsek, tpj2, tbg, tkl = w("lokasi"), w("sekolah"), w("putra", after=30.0), w("bangi"), w("klia")
zoom_at = tpj2 - 0.1
zoom_end = zoom_at + 1.0
tw(f'tl.fromTo("#mclose,#mcloseP",{{scale:1.18}},{{scale:1,duration:{zoom_at-mst:.3f},ease:"power1.out"}},{mst:.3f});')
tw(f'tl.fromTo("#msite",{{scale:0,opacity:0}},{{scale:1,opacity:1,duration:0.45,ease:"back.out(2)"}},{tlok-0.2:.3f});')
tw(f'tl.fromTo("#msite .pulse",{{scale:0.6,opacity:0.8}},{{scale:2.6,opacity:0,duration:1.2,repeat:{max(1, int((men-tlok)/1.2))},ease:"power1.out"}},{tlok:.3f});')
sfx("pop", tlok, 0.55)
for k, pid_ in enumerate(("pn_sra", "pn_skj")):
    tw(f'tl.fromTo("#{pid_}",{{scale:0,opacity:0}},{{scale:1,opacity:1,duration:0.3,ease:"back.out(2.2)"}},{tsek-0.45+k*0.18:.3f});')
    sfx("pop", tsek - 0.43 + k * 0.18, 0.45)
# the zoom-out: close shrinks 4x into the wide plate, which lands from 4x to 1x
tw(f'tl.fromTo("#mclose,#mcloseP",{{scale:1}},{{scale:0.25,duration:1.0,ease:"power2.inOut"{IR}}},{zoom_at:.3f});')
tw(f'tl.fromTo("#mclose,#mcloseP",{{opacity:1}},{{opacity:0,duration:0.4{IR}}},{zoom_at+0.45:.3f});')
tw(f'tl.fromTo("#mwide,#mwideP",{{scale:4,opacity:0}},{{scale:1,opacity:1,duration:1.0,ease:"power2.inOut"}},{zoom_at:.3f});')
sfx("whoosh", zoom_at, 0.5)
for k, (pid_, at, rk) in enumerate((("pn_pj", tpj2, "putrajaya"), ("pn_bg", tbg, "bangi"), ("pn_kl", tkl, "klia"))):
    at = max(at, zoom_end)
    tw(f'tl.fromTo("#rt_{rk}",{{strokeDashoffset:1400}},{{strokeDashoffset:0,duration:0.45,ease:"power2.out"}},{at-0.1:.3f});')
    tw(f'tl.fromTo("#{pid_}",{{scale:0,opacity:0}},{{scale:1,opacity:1,duration:0.35,ease:"back.out(2)"}},{at+0.1:.3f});')
    sfx("pop", at + 0.12, 0.5)
tw(f'tl.fromTo("#mwide,#mwideP",{{y:0}},{{y:-60,duration:{max(0.5, men-tkl):.3f},ease:"none"{IR}}},{tkl:.3f});')

# ---- 7. Price RM430K, then booking RM500
s = S(7)
tharga, t430, tribu, tring, tbook, t500, tsah = w("harga"), w("430"), w("ribu"), w("ringgit", after=36.9), w("booking"), w("500"), w("sahaja")
clip('''<div class="price" id="price">
  <div class="kicker">HARGA BERMULA</div>
  <div class="amt"><span class="cur">RM</span><span id="pnum">0</span><span class="k">K</span></div>
</div>''', tharga - 0.1, tbook - tharga + 0.05, "center", track=3)
tw(f'tl.fromTo("#price",{{opacity:0,scale:0.85}},{{opacity:1,scale:1,duration:0.3,ease:"power3.out"}},{tharga-0.1:.3f});')
tw(f'const pc={{v:0}};tl.fromTo(pc,{{v:0}},{{v:430,duration:{max(0.5, tribu-t430+0.3):.3f},ease:"power2.out",onUpdate:()=>{{document.getElementById("pnum").textContent=Math.round(pc.v)}}}},{t430-0.1:.3f});')
for k in range(8):
    sfx("tick", t430 - 0.1 + k * (tribu - t430 + 0.3) / 8 * (k / 8) ** 0.3, 0.35)
sfx("coin", tring, 0.6)
tw(f'tl.fromTo("#price .amt",{{scale:1}},{{scale:1.08,duration:0.12,yoyo:true,repeat:1{IR}}},{tring:.3f});')
tw(f'tl.to("#price",{{opacity:0,y:-80,duration:0.2}},{tbook-0.15:.3f});')
clip('''<div class="book">
  <div class="kicker" id="bk">BOOKING</div>
  <div class="bignum" id="b500"><span class="cur">RM</span>500</div>
  <div class="pill dark" id="bsaja">SAHAJA!</div>
</div>''', tbook - 0.1, s["out_out"] - tbook + 0.25, "center", track=3)
tw(f'tl.fromTo("#bk",{{opacity:0,y:-40}},{{opacity:1,y:0,duration:0.25,ease:"power3.out"}},{tbook-0.05:.3f});')
tw(f'tl.fromTo("#b500",{{scale:2.6,opacity:0}},{{scale:1,opacity:1,duration:0.22,ease:"power4.in"}},{t500-0.18:.3f});')
tw(f'tl.fromTo(".book",{{x:-14}},{{x:0,duration:0.3,ease:"elastic.out(1,0.3)"}},{t500+0.04:.3f});')
sfx("stamp", t500 + 0.02, 0.7); sfx("coin", t500 + 0.08, 0.55)
tw(f'tl.fromTo("#bsaja",{{opacity:0,scale:0.4}},{{opacity:1,scale:1,duration:0.3,ease:"back.out(2.5)"}},{tsah:.3f});')

# ---- 8. Legal fees borne by developer
s = S(8)
items = [("Kos Guaman SPA", w("goaman")), ("MOT", w("mot"))]
rows = "".join(f'<div class="ck" id="ck{k}"><span class="box"><svg viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6.5"/></svg></span>{html.escape(n)}</div>'
               for k, (n, _) in enumerate(items))
clip(f'''<div class="list"><div class="kicker">BONUS PEMBELI</div>{rows}
  <div class="stamp green small" id="free">DITANGGUNG PEMAJU</div></div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.3, "center", track=3)
for k, (_, at) in enumerate(items):
    tw(f'tl.fromTo("#ck{k}",{{opacity:0,x:-120}},{{opacity:1,x:0,duration:0.3,ease:"power3.out"}},{at-0.2:.3f});')
    tw(f'tl.fromTo("#ck{k} svg path",{{strokeDashoffset:30}},{{strokeDashoffset:0,duration:0.25}},{at+0.05:.3f});')
    sfx("tick", at + 0.05, 0.6); sfx("pop", at - 0.15, 0.3)
tf = w("ditanggung")
tw(f'tl.fromTo("#free",{{scale:3,opacity:0,rotation:-16}},{{scale:1,opacity:1,rotation:{T["stamp_rot"]},duration:0.2,ease:"power4.in"}},{tf-0.05:.3f});')
sfx("stamp", tf + 0.12, 0.8); sfx("ding", tf + 0.17, 0.3)

# ---- 9. Completion date
s = S(9)
tfeb = w("februari")
clip('''<div class="cal">
  <div class="kicker">DIJANGKA SIAP</div>
  <div class="calcard" id="calc"><div class="calhead">2028</div><div class="calbody" id="calm">FEB</div></div>
</div>''', s["out_in"] - 0.1, s["out_out"] - s["out_in"] + 0.25, "center", track=3)
tw(f'tl.fromTo(".cal .kicker",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.3}},{s["out_in"]:.3f});')
tw(f'tl.fromTo("#calc",{{rotationX:-90,opacity:0,transformPerspective:900}},{{rotationX:0,opacity:1,duration:0.5,ease:"back.out(1.6)"}},{tfeb-0.25:.3f});')
sfx("whoosh", tfeb - 0.3, 0.35); sfx("ding", tfeb + 0.25, 0.4)

# ---- 10. End card (no brand name, no phone number)
s = S(10)
end_in = s["out_in"] - 0.1
clip(f'''<div class="endcard">
  <div class="kicker">TAMAN JENDERAM LESTARI · FASA 3</div>
  <div class="q" id="eq">Nak tahu lebih lanjut?</div>
  <div class="phone" id="eph"><svg viewBox="0 0 24 24"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1z"/></svg>HUBUNGI SAYA SEKARANG</div>
  <div class="num" id="enum">Pendaftaran Fasa 3 kini dibuka</div>
  <div class="facts" id="efacts">RM430K · Freehold · Booking RM500 · Siap Feb 2028</div>
  <div class="loc">{PIN}Jenderam Hilir, Dengkil</div>
</div>''', end_in, DURATION - end_in, "full", id_="end", track=3)
thub = w("hubungi")
tw(f'tl.fromTo("#end",{{opacity:0}},{{opacity:1,duration:0.35}},{end_in:.3f});')
tw(f'tl.fromTo("#end .kicker",{{y:-40,opacity:0}},{{y:0,opacity:1,duration:0.45,ease:"power3.out"}},{end_in:.3f});')
tw(f'tl.fromTo("#eq",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.35}},{s["out_in"]+0.1:.3f});')
tw(f'tl.fromTo("#eph",{{scale:0.6,opacity:0}},{{scale:1,opacity:1,duration:0.4,ease:"back.out(2)"}},{thub-0.1:.3f});')
tw(f'tl.fromTo("#eph",{{scale:1}},{{scale:1.06,duration:0.45,yoyo:true,repeat:3,ease:"sine.inOut"{IR}}},{s["out_out"]:.3f});')
tw(f'tl.fromTo("#enum",{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.35}},{thub+0.3:.3f});')
tw(f'tl.fromTo("#efacts",{{opacity:0}},{{opacity:1,duration:0.4}},{s["out_out"]+0.1:.3f});')
sfx("whoosh", end_in - 0.1, 0.4); sfx("ding", thub, 0.45); sfx("coin", s["out_out"] + 0.1, 0.35)

# ================================================================ CAPTIONS (word level)
FIX = {"Jendram": "Jenderam", "Saya": "Saiz", "setanah": "tanah", "20x73": "20×73", "1040": "1,040",
       "goaman": "guaman", "Freehold": "freehold", "Rumah": "rumah", "Kos": "Kos", "Dan": "Dan"}
def owner(st, en):
    best, bo = None, 0.0
    for s_ in SEG:
        o = min(en, s_["src_out"]) - max(st, s_["src_in"])
        if o > bo: best, bo = s_, o
    return best
all_chunks = []
for s in PLAY:
    toks = []
    for wd, st, en in WORDS:
        if owner(st, en) is not s:
            continue
        st = max(st, s["src_in"])
        low = wd.lower()
        if low.startswith("jaya") and toks and toks[-1][0] == "Putra":
            toks[-1] = ("Putrajaya" + wd[4:], toks[-1][1]); continue
        if low.startswith("berjaya") and toks and toks[-1][0] == "Sai":
            toks[-1] = ("Cyberjaya" + wd[7:], toks[-1][1]); continue
        if wd == "%" and toks:
            toks[-1] = (toks[-1][0] + "%", toks[-1][1]); continue
        toks.append((FIX.get(wd, wd), out(st)))
    if s is PLAY[0]:
        toks[0] = (toks[0][0], s["out_in"])
    chunks, cur = [], []
    for p, at in toks:
        cur.append((p, at))
        if len(cur) == 4 or p[-1] in ".?" or (p[-1] == "," and len(cur) >= 2):
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    all_chunks += [(c, s) for c in chunks]
cap_n = 0
for c_i, (ch, s) in enumerate(all_chunks):
    st = ch[0][1]
    en = all_chunks[c_i + 1][0][0][1] if c_i + 1 < len(all_chunks) else s["out_out"] + 0.4
    if en - st > 3.0: en = max(st + 1.6, s["out_out"] + 0.3)
    cap_n += 1
    spans = " ".join(f'<span id="cw{cap_n}_{j}">{html.escape(p)}</span>' for j, (p, _) in enumerate(ch))
    clip(f'<div class="cap" id="cap{cap_n}">{spans}</div>', st, en - st, "capwrap", track=5)
    tw(f'tl.fromTo("#cap{cap_n}",{{y:24,opacity:0}},{{y:0,opacity:1,duration:0.12,ease:"power2.out"}},{st:.3f});')
    on, off = T["cap_on"], T["cap_off"]
    for j, (_, at) in enumerate(ch):
        nxt = ch[j + 1][1] if j + 1 < len(ch) else None
        if T["cap"] == "karaoke":
            tw(f'tl.fromTo("#cw{cap_n}_{j}",{{color:"{off}",scale:1}},{{color:"{on}",scale:1.1,duration:0.08}},{at:.3f});')
            if nxt: tw(f'tl.to("#cw{cap_n}_{j}",{{color:"{off}",scale:1,duration:0.08}},{nxt:.3f});')
        elif T["cap"] == "bar":
            tw(f'tl.fromTo("#cw{cap_n}_{j}",{{color:"{off}"}},{{color:"{on}",duration:0.1}},{at:.3f});')
            if nxt: tw(f'tl.to("#cw{cap_n}_{j}",{{color:"{off}",duration:0.15}},{nxt:.3f});')
        else:
            tw(f'tl.fromTo("#cw{cap_n}_{j}",{{backgroundColor:"rgba(198,255,61,0)",color:"{off}",scale:1,rotation:0}},'
               f'{{backgroundColor:"rgba(198,255,61,1)",color:"{on}",scale:1.12,rotation:-3,duration:0.06}},{at:.3f});')
            if nxt: tw(f'tl.to("#cw{cap_n}_{j}",{{backgroundColor:"rgba(198,255,61,0)",color:"{off}",scale:1,rotation:0,duration:0.06}},{nxt:.3f});')

# ================================================================ WRITE
CSS = open(os.path.join(HERE, "style.css")).read()
if T["css"]:
    CSS += "\n/* ---- theme ---- */\n" + open(os.path.join(HERE, T["css"])).read()
blur = ' data-motion-blur="on"' if V["blur"] else ""
NL = "\n      "
doc = f'''<!doctype html>
<html lang="ms" data-resolution="portrait" data-variant="{KEY}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <!-- GENERATED by tools/build.py ({V["name"]}). Edit build.py / style.css, not this file. -->
    <script src="vendor/gsap.min.js"></script>
    <style>
{CSS}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main"{blur} data-start="0" data-duration="{DURATION}" data-width="1080" data-height="1920">
      {NL.join(elements)}
      {NL.join(audio)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {NL.join(tweens)}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''
assert "J3" not in doc.split("<style>")[0] + doc.split("</style>")[1], "brand name leaked into the film"
open(os.path.join(ROOT, "index.html"), "w").write(doc)
json.dump({"variant": KEY, "duration": DURATION, "segments": PLAY, "shots": SHOTS}, open(os.path.join(HERE, "edl_out.json"), "w"), indent=1)
print(f"index.html = {V['name']} · {len(SHOTS)} shots · {DURATION}s · {sfx_n[0]} sfx · {cap_n} captions")
for s_ in PLAY:
    print(f'  {s_["out_in"]:6.2f}-{s_["out_out"]:6.2f}  <- src {s_["src_in"]:5.2f}-{s_["src_out"]:5.2f}  {s_["note"]}')
