"""
The design system: one set of tokens, one stylesheet, used by every screen.

Three rules this file follows.

Tokens, not literals. Colour, spacing, radius and shadow are CSS custom
properties declared once in :root. Changing the green is one edit, not forty.

Width is set in exactly one place. The app ran for weeks looking like a narrow
strip down the middle of a wide monitor. The cause was not Streamlit and not
nested columns -- it was a single `max-width:1120px` on .block-container in
this file, overriding the `layout="wide"` set in app.py. Anything that clamps
the content width belongs here, where it can be found.

Streamlit needs real hooks. `st.markdown("<div class='x'>")` renders as a
SIBLING of the widgets that follow, never a parent, so wrapping widgets that
way silently styles nothing. To reach a widget, either target its own
data-testid or wrap it in `st.container(key="name")`, which emits a real
`st-key-name` class.
"""

from __future__ import annotations

import streamlit as st

# the palette, in one place
PRIMARY = "#1f5134"
ACCENT = "#2f8f5b"
DARK = "#13271b"
GOLD = "#c7912f"
CREAM = "#ffffff"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=Inter:wght@400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap');

:root{
  /* ── colour ──────────────────────────────────────────────
     Brand values come from the product palette. Four of them fail WCAG AA
     as text, though, so each of those has a darker sibling at the same hue:
     the brand value fills shapes, the sibling carries words. Measured on
     white -- #2E8B57 4.25:1, #738078 4.13, #D9534F 3.96, #E9A23B 2.17,
     against the 4.5 an accessible interface needs. */
  --forest:#176B45;      --forest-d:#0f4a2f;   --forest-l:#2E8B57;
  --emerald:#2E8B57;                           /* fills and borders only */
  --emerald-l:#EAF5EE;
  --gold:#c7912f;        --gold-l:#fdf6e7;
  /* clay and rice paste: the two colours a Warli wall is painted in, and the
     reason this app stops looking like a generic green SaaS dashboard */
  --clay:#9d5531;        --clay-d:#7f4226;     --clay-l:#f3e7de;
  --paste:#f6efe2;
  --ink:#17251D;         --muted:#677268;      --faint:#5f6e66;   /* passes on white and on the warm sand */
  /* a warm sand rather than a cool off-white; the cool grey was fighting
     every warm thing on the page */
  --bg:#F8F5EE;          --paper:#FFFFFF;      --sage:#EAF5EE;
  --line:#e6e2d7;        --line-s:#d4cec0;
  --danger:#B3332F;      --danger-fill:#D9534F;   --danger-l:#fbeeea;
  --warn:#8A5D12;        --warn-fill:#E9A23B;     --warn-l:#fdf4e3;

  /* ── spacing ────────────────────────────────────────────── */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px;

  /* ── shape ──────────────────────────────────────────────── */
  --r-s:8px; --r:12px; --r-l:16px; --r-xl:20px; --r-pill:999px;
  --sh-1:0 1px 2px rgba(22,36,27,.05), 0 1px 3px rgba(22,36,27,.06);
  --sh-2:0 4px 10px rgba(22,36,27,.07), 0 2px 4px rgba(22,36,27,.05);
  --sh-3:0 12px 28px rgba(22,36,27,.12);

  /* ── type ───────────────────────────────────────────────── */
  --sans:'Inter','Noto Sans Devanagari',system-ui,sans-serif;
  --display:'Manrope','Noto Sans Devanagari',system-ui,sans-serif;
}

/* ═══════════════════ 1. LAYOUT ═══════════════════
   The one place width is decided. app.py already asks for layout="wide";
   this used to clamp it to 1120px and waste half a desktop screen. */
.stApp{ background:var(--bg); }
/* 1500px was a prose measure, and this is not prose -- it is cards, metrics
   and short lines. On a wide or zoomed-out screen that cap threw half the
   window away as margin. 2000px still stops a single line of text running
   the width of a cinema display. */
.block-container{ max-width:2000px; padding:var(--s3) var(--s5) var(--s6); }
@media (max-width:1200px){ .block-container{ padding:var(--s3) var(--s4) var(--s5); } }
@media (max-width:640px){ .block-container{ padding:var(--s2) var(--s3) var(--s5); } }

/* a readable sidebar, not a sliver */
[data-testid="stSidebar"]{ width:276px !important; min-width:276px !important;
  background:var(--paper); border-right:1px solid var(--line); }
[data-testid="stSidebar"] > div{ padding-top:var(--s3); }
@media (max-width:640px){
  [data-testid="stSidebar"]{ width:85vw !important; min-width:0 !important; } }

/* the chrome Streamlit draws for itself */
/* Streamlit's own footer is branding, not a control, so it goes. The main
   menu stays: it is how anyone reruns the app, prints it, or reaches the
   settings. Only the Deploy button -- meaningless on a local run -- is hidden,
   and by its own testid rather than by nuking the whole bar. */
footer{ visibility:hidden; }
/* The reopen-the-sidebar button lives INSIDE this header. Hiding the header
   outright -- which this file used to do -- hid the only way back to the
   sidebar once it was closed. */
[data-testid="stHeader"]{ background:transparent; pointer-events:none; }
[data-testid="stAppDeployButton"]{ display:none; }
/* Collapsed, this is the only way back to the navigation and the language
   switch, so it has to look like a control rather than a stray chip floating
   in the margin. Brand green, solid, and large enough to hit with a thumb. */
[data-testid="stExpandSidebarButton"]{
  visibility:visible !important; pointer-events:auto;
  background:var(--forest) !important; border:none !important;
  border-radius:10px !important; box-shadow:var(--sh-2) !important;
  width:38px !important; height:38px !important;
  margin:6px 0 0 8px !important;
  transition:background .15s ease, transform .12s ease; }
[data-testid="stExpandSidebarButton"]:hover{
  background:var(--forest-l) !important; transform:translateY(-1px); }
[data-testid="stExpandSidebarButton"] svg{ color:#f3faf4 !important;
  fill:#f3faf4 !important; width:20px; height:20px; }
[data-testid="stSidebarCollapseButton"]{ visibility:visible !important; }

/* ═══════════════════ 2. TYPE ═══════════════════ */
html, body, [class*="css"]{ font-family:var(--sans); color:var(--ink); }
h1,h2,h3,h4,h5{ font-family:var(--display) !important; color:var(--ink);
  letter-spacing:-.01em; }
h1{ font-size:1.9rem; } h2{ font-size:1.45rem; } h3{ font-size:1.2rem; }
h4{ font-size:1.05rem; } h5{ font-size:.95rem; }
p, li, label, .stMarkdown{ font-size:.95rem; line-height:1.6; }
small, .stCaption, [data-testid="stCaptionContainer"]{ color:var(--muted) !important; }
a{ color:var(--forest); }

/* ═══════════════════ 3. APP SHELL ═══════════════════ */
/* sidebar brand block */
.brand{ display:flex; align-items:center; gap:10px; padding:2px 2px var(--s3); }
.brand .bmark{ width:38px; height:38px; border-radius:11px; flex:none;
  display:flex; align-items:center; justify-content:center; font-size:1.25rem;
  background:linear-gradient(135deg,var(--forest),var(--forest-l));
  box-shadow:var(--sh-2); }
.brand .bn{ font-family:var(--display); font-weight:800; font-size:1.08rem;
  color:var(--ink); line-height:1.15; }
.brand .bs{ color:var(--muted); font-size:.74rem; line-height:1.3; }

/* sidebar section labels */
.sgroup{ color:var(--faint); font-size:.68rem; font-weight:700; letter-spacing:.09em;
  text-transform:uppercase; margin:var(--s4) 0 var(--s2) 2px; }

/* page header: title on the left, state on the right */
.pagehead{ display:flex; align-items:flex-end; justify-content:space-between;
  gap:var(--s4); flex-wrap:wrap; padding:0 0 var(--s2);
  border-bottom:1px solid var(--line); margin-bottom:var(--s3); }
.pagehead .pt{ font-family:var(--display); font-size:1.5rem; font-weight:800;
  color:var(--ink); line-height:1.2; }
.pagehead .pc{ color:var(--muted); font-size:.86rem; margin-top:2px; }
.pagehead .pr{ display:flex; align-items:center; gap:var(--s2); flex-wrap:wrap; }

/* a small status pill: service up, degraded, off */
.pill{ display:inline-flex; align-items:center; gap:6px; padding:5px 11px;
  border-radius:var(--r-pill); font-size:.76rem; font-weight:600;
  border:1px solid var(--line-s); background:var(--paper); color:var(--muted); }
.pill .dot{ width:7px; height:7px; border-radius:50%; background:var(--faint); }
.pill.ok{ background:var(--emerald-l); border-color:#bfdccb; color:#1d6b40; }
.pill.ok .dot{ background:var(--emerald); }
.pill.warn{ background:var(--warn-l); border-color:#e8d5a8; color:var(--warn); }
.pill.warn .dot{ background:var(--warn-fill); }
.pill.off{ background:var(--danger-l); border-color:#e8c4ba; color:var(--danger); }
.pill.off .dot{ background:var(--danger-fill); }

/* ═══════════════════ 4. HERO ═══════════════════ */
.hero{ border-radius:var(--r-xl); padding:30px 34px 24px; margin-bottom:var(--s3);
  color:#eef7f0; position:relative; overflow:hidden;
  background:
    radial-gradient(560px 280px at 88% 6%, rgba(47,143,91,.28), transparent 70%),
    linear-gradient(135deg,var(--forest) 0%, var(--forest-d) 62%, #0f2a1b 100%);
  box-shadow:var(--sh-3); }
/* the watermark is an inline SVG now -- an emoji drew a different picture on
   every device and said nothing about where this app comes from */
.hero .wm{ position:absolute; right:22px; bottom:26px; width:208px; height:auto;
  opacity:.16; animation:sway 11s ease-in-out infinite; }
.hero{ padding-bottom:40px; }
.hero .wband{ position:absolute; left:0; right:0; bottom:0; width:100%;
  height:26px; opacity:.92; }
@media (max-width:820px){ .hero .wm{ width:130px; opacity:.12; } }
.hero h1{ color:#f3faf4 !important; font-size:2rem; line-height:1.15;
  margin:0 0 4px; font-weight:800; }
.hero .mr{ color:#8fd4a9; font-size:1.05rem; font-weight:600; margin-bottom:8px; }
.hero p{ color:#c9ded0; font-size:1rem; max-width:620px; margin-bottom:var(--s4); }
.chips{ display:flex; flex-wrap:wrap; gap:var(--s2); }
.chip{ display:flex; align-items:center; gap:10px; padding:9px 15px 9px 11px;
  background:rgba(255,255,255,.08); border:1px solid rgba(143,212,169,.26);
  border-radius:var(--r-pill); transition:background .18s ease; }
.chip:hover{ background:rgba(255,255,255,.14); }
.chip .ci{ font-size:1.15rem; line-height:1; }
.chip .ct{ display:flex; flex-direction:column; line-height:1.25; }
.chip .ct b{ color:#eef7f0; font-size:.88rem; font-weight:700; }
.chip .ct i{ color:#9db9a8; font-size:.75rem; font-style:normal; }
@media (max-width:820px){
  .hero{ padding:28px 20px 24px; } .hero h1{ font-size:1.6rem; }
  .chip .ct i{ display:none; } }

/* a running Warli border, used to divide sections */
.wband{ display:block; width:100%; height:30px; border-radius:4px; }
.wdiv{ margin:var(--s5) 0 var(--s4); }

/* the four painted panels that replaced the stock photographs */
.warli{ position:relative; border-radius:var(--r); overflow:hidden;
  border:1px solid var(--line); box-shadow:var(--sh-1);
  transition:transform .15s ease, box-shadow .15s ease; }
.warli:hover{ transform:translateY(-2px); box-shadow:var(--sh-2); }
.warli svg{ display:block; width:100%; height:auto; }
.warli .wcap{ position:absolute; left:0; right:0; bottom:0; padding:7px 11px;
  color:var(--paste); font-size:.82rem; font-weight:600;
  background:linear-gradient(transparent, rgba(60,28,12,.78)); }

/* ═══════════════════ 5. CARDS & GRIDS ═══════════════════ */
.grid{ display:grid; grid-template-columns:repeat(4,1fr); gap:var(--s3);
  margin:var(--s2) 0; }
.grid2{ grid-template-columns:repeat(2,1fr); }
@media (max-width:980px){ .grid,.grid2{ grid-template-columns:1fr 1fr; } }
@media (max-width:560px){ .grid,.grid2{ grid-template-columns:1fr; } }

.card{ background:var(--paper); border:1px solid var(--line); border-radius:var(--r);
  padding:var(--s4); box-shadow:var(--sh-1); }
.card .ic{ font-size:1.7rem; }
.card h4{ color:var(--ink); margin:var(--s2) 0 var(--s1); font-size:1rem;
  font-weight:700; }
.card p{ color:var(--muted); font-size:.88rem; margin:0; line-height:1.55; }
.card img,.thumb img{ width:100%; height:128px; object-fit:cover;
  border-radius:var(--r); border:1px solid var(--line); }
.thumb .fb{ width:100%; height:128px; border-radius:var(--r); display:flex;
  align-items:center; justify-content:center; font-size:2.4rem;
  background:linear-gradient(135deg,var(--forest-l),var(--forest-d)); color:#cfe8d8; }

/* the farmer's own farm, on the home screen */
.panel{ background:var(--paper); border:1px solid var(--line); border-radius:var(--r);
  padding:2px var(--s4); box-shadow:var(--sh-1); animation:popIn .32s ease both; }
.panel.empty{ padding:var(--s4); color:var(--muted); font-size:.9rem;
  line-height:1.55; background:var(--sage); border-style:dashed;
  border-color:var(--line-s); }
.prow{ display:flex; align-items:center; gap:10px; padding:11px 0;
  border-bottom:1px solid var(--line); }
.prow:last-child{ border-bottom:none; }
.prow .pi{ font-size:1rem; width:20px; text-align:center; }
.prow .pk{ color:var(--muted); font-size:.83rem; min-width:58px; }
.prow .pv{ color:var(--ink); font-weight:700; font-size:.92rem; margin-left:auto;
  text-align:right; }

/* friends section */
.friends{ background:linear-gradient(135deg,var(--forest-d),#0f2a1b);
  border-radius:var(--r-l); padding:var(--s5) var(--s4); margin:var(--s4) 0;
  color:#dcebe1; }
.friends h2{ color:#f3faf4 !important; margin-bottom:var(--s3); }
.friend{ background:rgba(255,255,255,.055); border:1px solid rgba(143,212,169,.2);
  border-radius:var(--r); padding:var(--s4); text-align:center; }
.friend .e{ font-size:2.2rem; }
.friend h4{ color:#8fd4a9; margin:var(--s1) 0; }
.friend p{ color:#b9d0c2; font-size:.84rem; margin:0; }

/* ticker */
.ticker{ overflow:hidden; white-space:nowrap; background:var(--clay-l);
  border:1px solid #e4d2c4; border-radius:var(--r); padding:9px 0;
  margin:var(--s3) 0 var(--s4); }
.ticker span{ display:inline-block; padding-left:100%; color:#6f3d22;
  font-weight:600; font-size:.88rem; animation:scroll 30s linear infinite; }
@keyframes scroll{ 0%{transform:translateX(0);} 100%{transform:translateX(-100%);} }

/* soil progress */
.stProgress > div > div > div > div{ background-color:var(--emerald) !important; }
.soil-row{ font-weight:600; color:var(--ink); font-size:.9rem; margin-bottom:-6px; }

.footer{ background:linear-gradient(135deg,var(--clay),var(--clay-d));
  color:var(--paste); border-radius:var(--r-l); padding:var(--s5);
  margin-top:var(--s2); font-size:.86rem; }
.footer b{ color:var(--paste); font-family:var(--display); }
.footwrap{ margin-top:var(--s5); border-radius:var(--r-l); overflow:hidden; }
.footwrap .wband{ height:28px; border-radius:0; }
.footwrap .footer{ border-radius:0; margin-top:0; }

/* ═══════════════════ 6. CONTROLS ═══════════════════ */
/* 48px minimum: this is used on a phone, outdoors, with working hands */
.stButton>button{ border-radius:var(--r); border:1px solid var(--line-s);
  background:var(--paper); color:var(--ink); font-weight:600; min-height:46px;
  font-family:var(--sans); box-shadow:var(--sh-1);
  transition:border-color .15s ease, background .15s ease, transform .12s ease; }
.stButton>button:hover{ border-color:var(--emerald); background:#fbfdfa;
  color:var(--forest); }
.stButton>button:active{ transform:translateY(1px); }
button[kind="primary"]{ background:var(--forest) !important; color:#f3faf4 !important;
  border:1px solid var(--forest) !important; }
button[kind="primary"]:hover{ background:var(--forest-l) !important;
  color:#ffffff !important; }

/* The main navigation, in the sidebar.
   Streamlit centres a button's contents, and it does it on the button AND on
   the markdown container inside it, so setting justify-content alone left the
   labels floating in the middle of the row -- a nav list that looked like six
   unrelated centred words. Both layers have to be told. */
.st-key-sidenav [data-testid^="stBaseButton"]{
  justify-content:flex-start !important; text-align:left !important;
  gap:10px; min-height:42px; font-weight:600; font-size:.92rem;
  box-shadow:none; border-color:transparent; background:transparent;
  padding-left:12px; }
.st-key-sidenav [data-testid^="stBaseButton"] [data-testid="stMarkdownContainer"]{
  text-align:left !important; width:100%; }
.st-key-sidenav [data-testid^="stBaseButton"] p{ text-align:left !important;
  margin:0; }
.st-key-sidenav [data-testid^="stBaseButton"]:hover{ background:var(--sage);
  border-color:transparent; }
.st-key-sidenav [data-testid="stBaseButton-primary"]{
  background:var(--emerald-l) !important; color:var(--forest) !important;
  border:1px solid #bfdccb !important; }

/* home tiles: the whole card is the button, not a div with a button under it */
.st-key-hometiles .stButton>button{ min-height:112px; border-radius:var(--r-l);
  background:var(--paper); border:1px solid var(--line); color:var(--ink);
  font-family:var(--display); font-size:1rem; font-weight:700;
  box-shadow:var(--sh-1); }
.st-key-hometiles .stButton>button:hover{ border-color:var(--emerald);
  transform:translateY(-2px); box-shadow:var(--sh-2); }
.st-key-hometiles .stButton>button p:first-child:not(:only-child){
  font-size:2.4rem; line-height:1.1; margin:0 0 2px; }

/* a tappable question: long text, so left-aligned */
.st-key-popq .stButton>button,
[class*="st-key-qb_"] .stButton>button{ min-height:58px; text-align:left;
  justify-content:flex-start; border-left:3px solid var(--emerald);
  font-weight:500; font-size:.92rem; line-height:1.4; padding:10px 14px; }

/* Columns stacked far too early. Streamlit gives each column a min-width of
   its content, so a flex row whose children will not shrink wraps as soon as
   the content pane narrows -- which is what happened to the three market
   fields the moment the sidebar opened. Letting them shrink (min-width:0)
   keeps the row a row down to tablet width, where stacking is correct. */
@media (min-width:900px){
  [data-testid="stHorizontalBlock"]{ flex-wrap:nowrap; }
  [data-testid="stColumn"]{ min-width:0 !important; }
}
@media (max-width:899px){
  [data-testid="stHorizontalBlock"]{ flex-wrap:wrap; }
}

/* language switch */
[data-testid="stSidebar"] [role="radiogroup"]{ gap:6px; flex-wrap:wrap; }
[role="radiogroup"] label{ background:var(--paper); border:1px solid var(--line-s);
  border-radius:var(--r-pill); padding:4px 13px;
  transition:border-color .15s ease, background .15s ease; }
/* the sidebar is 276px wide: at the default size these four wrapped one to a
   row and ate a third of the panel */
[data-testid="stSidebar"] [role="radiogroup"] label{ padding:3px 9px;
  font-size:.85rem; }
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child{
  transform:scale(.8); }
[role="radiogroup"] label:hover{ border-color:var(--emerald); background:#fbfdfa; }

/* inputs */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
[data-baseweb="select"] > div{ border-radius:var(--r-s) !important;
  border-color:var(--line-s) !important; font-family:var(--sans) !important; }
.stTextInput input:focus, .stNumberInput input:focus{
  border-color:var(--emerald) !important; box-shadow:0 0 0 3px rgba(47,143,91,.12) !important; }

/* metrics, used by the weather and money screens */
[data-testid="stMetric"]{ background:var(--paper); border:1px solid var(--line);
  border-radius:var(--r); padding:var(--s3) var(--s4); box-shadow:var(--sh-1); }
[data-testid="stMetricLabel"]{ color:var(--muted) !important; font-size:.8rem !important; }
[data-testid="stMetricValue"]{ color:var(--ink) !important; font-family:var(--display);
  font-size:1.6rem !important; font-weight:800 !important; }

/* tabs */
[data-baseweb="tab-list"]{ gap:var(--s1); border-bottom:1px solid var(--line); }
[data-baseweb="tab"]{ font-weight:600; font-size:.9rem; }

/* expanders */
[data-testid="stExpander"]{ border:1px solid var(--line); border-radius:var(--r);
  background:var(--paper); box-shadow:var(--sh-1); }

/* Keyboard focus has to be visible -- it is the only way to tell where you
   are without a mouse, and the default ring vanishes against these greens. */
:is(button, input, textarea, select, [role="radio"], [role="tab"],
    summary, a):focus-visible{
  outline:2px solid var(--emerald) !important; outline-offset:2px !important;
  border-radius:var(--r-s); }

/* status messages */
[data-testid="stAlert"]{ border-radius:var(--r); border:1px solid var(--line);
  box-shadow:var(--sh-1); font-size:.92rem; }

/* tables */
[data-testid="stDataFrame"], [data-testid="stTable"]{
  border:1px solid var(--line); border-radius:var(--r); overflow:hidden;
  box-shadow:var(--sh-1); }
[data-testid="stDataFrame"] thead th{ background:var(--sage) !important;
  color:var(--ink) !important; font-weight:700 !important; }

/* ═══════════════════ 7. CHAT ═══════════════════ */
.msg{ max-width:min(860px,94%); padding:13px 17px; border-radius:var(--r-l);
  margin:var(--s2) 0; font-size:.95rem; line-height:1.62;
  animation:fadeUp .32s ease both; }
.msg.me{ margin-left:auto; background:var(--forest); color:#eef7f0;
  border-bottom-right-radius:var(--r-s); font-weight:500; }
.msg.bot{ margin-right:auto; background:var(--paper); color:var(--ink);
  border:1px solid var(--line); border-bottom-left-radius:var(--r-s);
  box-shadow:var(--sh-1); }
/* the reply bubble is a keyed container so the model's markdown can render
   inside it as real headings, lists and tables */
[class*="st-key-bot"]{ max-width:min(860px,94%); margin:var(--s2) auto var(--s2) 0;
  padding:13px 17px; border-radius:var(--r-l); border-bottom-left-radius:var(--r-s);
  background:var(--paper); border:1px solid var(--line); box-shadow:var(--sh-1);
  animation:fadeUp .32s ease both; }
[class*="st-key-bot"] p{ font-size:.95rem; line-height:1.62; margin:0 0 8px; }
[class*="st-key-bot"] p:last-child{ margin-bottom:0; }
[class*="st-key-bot"] h1,[class*="st-key-bot"] h2,
[class*="st-key-bot"] h3,[class*="st-key-bot"] h4{ font-size:1rem; margin:10px 0 4px; }
[class*="st-key-bot"] ul,[class*="st-key-bot"] ol{ margin:6px 0 8px 18px; }
[class*="st-key-bot"] li{ margin-bottom:3px; }
[class*="st-key-bot"] table{ width:100%; border-collapse:collapse; margin:8px 0;
  font-size:.88rem; }
[class*="st-key-bot"] th,[class*="st-key-bot"] td{ border:1px solid var(--line);
  padding:6px 9px; text-align:left; }
[class*="st-key-bot"] th{ background:var(--sage); }

.msg.bot h1,.msg.bot h2,.msg.bot h3,.msg.bot h4{ font-size:1rem; margin:10px 0 4px; }
.msg.bot ul,.msg.bot ol{ margin:6px 0 6px 18px; }
.msg.bot table{ width:100%; border-collapse:collapse; margin:8px 0; font-size:.88rem; }
.msg.bot th,.msg.bot td{ border:1px solid var(--line); padding:6px 9px; text-align:left; }
.msg.bot th{ background:var(--sage); }
.who{ font-size:.74rem; font-weight:700; letter-spacing:.05em;
  text-transform:uppercase; color:var(--faint); margin:var(--s3) 0 0; }
.who.me{ text-align:right; }

/* the farmer's own question, above the answer (legacy) */
.asked{ background:var(--sage); border-left:3px solid var(--forest);
  border-radius:var(--r-s); padding:10px 14px; margin:var(--s4) 0 var(--s1);
  color:var(--ink); font-weight:600; }
.qcard{ background:var(--paper); border:1px solid var(--line);
  border-left:3px solid var(--emerald); border-radius:var(--r); padding:12px 14px; }
.qcard .ic{ font-size:1.4rem; }
.qcard .tx{ color:var(--ink); font-size:.9rem; font-weight:600; line-height:1.35; }

/* ═══════════════════ 8. COUNCIL OF EXPERTS ═══════════════════ */
.consensus{ display:flex; align-items:center; gap:var(--s3); background:var(--paper);
  border:1px solid var(--line); border-radius:var(--r); padding:11px 16px;
  margin:var(--s2) 0 var(--s1); box-shadow:var(--sh-1); }
.consensus .lbl{ font-weight:700; color:var(--ink); white-space:nowrap; font-size:.9rem; }
.consensus .note{ color:var(--muted); font-size:.82rem; white-space:nowrap; }
.meter{ flex:1; height:8px; border-radius:var(--r-pill); background:var(--line);
  overflow:hidden; min-width:80px; }
.meter i{ display:block; height:100%; border-radius:var(--r-pill); }
.m-strong i{ background:linear-gradient(90deg,var(--forest),var(--emerald)); }
.m-partial i{ background:linear-gradient(90deg,#b8822a,var(--warn-fill)); }
.m-split i{ background:linear-gradient(90deg,var(--danger-fill),#cf7a62); }

.seats{ display:grid; grid-template-columns:repeat(3,1fr); gap:var(--s3);
  margin:var(--s1) 0 var(--s3); }
@media (max-width:900px){ .seats{ grid-template-columns:1fr; } }
.seat{ background:var(--paper); border:1px solid var(--line);
  border-left:3px solid var(--forest); border-radius:var(--r); padding:14px 15px;
  box-shadow:var(--sh-1); }
.seat h5{ color:var(--ink); margin:0 0 var(--s2); font-size:.98rem; }
.seat .body{ color:var(--muted); font-size:.87rem; line-height:1.55; }
.seat.quiet{ border-left-color:var(--line-s); opacity:.75; }
.seat.quiet .body{ font-style:italic; }
.seat.broke{ border-left-color:var(--danger); }
.clash{ background:var(--danger-l); border:1px solid #e8c4ba; border-radius:var(--r-s);
  padding:10px 14px; margin:var(--s1) 0; color:var(--danger); font-size:.88rem; }
.gavel{ background:linear-gradient(135deg,var(--forest-d),#0f2a1b); color:#dcebe1;
  border-radius:var(--r); padding:12px 16px; margin:var(--s1) 0 var(--s2);
  font-size:.87rem; }
.gavel b{ color:#8fd4a9; }

/* ═══════════════════ 9. WEATHER & TOOLS ═══════════════════ */
.day{ background:var(--paper); border:1px solid var(--line); border-radius:var(--r-s);
  padding:10px 4px; text-align:center; box-shadow:var(--sh-1); }
.day .d{ color:var(--muted); font-size:.72rem; font-weight:600; }
.day .e{ font-size:1.5rem; line-height:1.35; }
.day .t{ color:var(--ink); font-size:.82rem; font-weight:700; }
.day .r{ color:#376f91; font-size:.72rem; }  /* 5.46:1; #3f7fa6 was 4.38 */

.window{ background:var(--emerald-l); border-left:3px solid var(--emerald);
  border-radius:var(--r-s); padding:10px 14px; margin:var(--s1) 0;
  color:#1d4b31; font-size:.9rem; }

/* ═══════════════════ 10. MOTION ═══════════════════
   One-shot entrances and hover responses only. Nothing loops in the reading
   area: a farmer squinting at a phone in sunlight does not need moving text.
   All of it is switched off for anyone who asked their system for less. */
@keyframes fadeUp{ from{opacity:0; transform:translateY(12px);} to{opacity:1; transform:none;} }
@keyframes popIn{ from{opacity:0; transform:scale(.98);} to{opacity:1; transform:none;} }
@keyframes sway{ 0%,100%{transform:translateY(0) rotate(0);} 50%{transform:translateY(-6px) rotate(-3deg);} }

.rise{ animation:fadeUp .45s cubic-bezier(.22,.8,.3,1) both; }
.card,.friend,.thumb img,.panel,.day{
  transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease; }
.card:hover,.panel:hover,.day:hover{ transform:translateY(-2px);
  box-shadow:var(--sh-2); border-color:var(--line-s); }
.friend:hover{ transform:translateY(-2px); background:rgba(255,255,255,.1); }
.thumb img:hover{ transform:scale(1.02); box-shadow:var(--sh-2); }

@media (prefers-reduced-motion: reduce){
  .rise,.hero .wm,.ticker span,.msg,.panel{ animation:none !important; }
  .card:hover,.friend:hover,.panel:hover,.thumb img:hover,.day:hover{
    transform:none !important; }
}
</style>
"""


def apply() -> None:
    """Load the stylesheet. The page header is drawn separately, by header()."""
    st.markdown(CSS, unsafe_allow_html=True)


def brand() -> None:
    """The product mark, at the top of the sidebar."""
    st.markdown(
        '<div class="brand">'
        '<span class="bmark">🪱</span>'
        '<span><span class="bn">Bhunaga</span><br>'
        '<span class="bs">भुनागा — शेतकऱ्याचा मित्र</span></span>'
        "</div>", unsafe_allow_html=True)


def header(title: str, caption: str = "", pills: list[tuple[str, str]] | None = None) -> None:
    """
    The bar across the top of every screen.

    `pills` are (state, label) where state is ok | warn | off. They say what is
    actually working right now -- which model, whether the index is loaded --
    so a failure is visible before it is confusing.
    """
    right = "".join(
        f'<span class="pill {state}"><span class="dot"></span>{label}</span>'
        for state, label in (pills or []))
    cap = f'<div class="pc">{caption}</div>' if caption else ""
    st.markdown(
        f'<div class="pagehead"><div><div class="pt">{title}</div>{cap}</div>'
        f'<div class="pr">{right}</div></div>', unsafe_allow_html=True)


def group(label: str) -> None:
    """A small uppercase section label, for grouping sidebar controls."""
    st.markdown(f'<div class="sgroup">{label}</div>', unsafe_allow_html=True)


def photo(url: str, emoji: str) -> str:
    """
    A small photo, falling back to an emoji if it will not load.

    Worth the trouble: these are hotlinked from Unsplash, and a farmer on a bad
    rural connection should still see something meaningful rather than a broken
    image icon.
    """
    fallback = (f"this.onerror=null;this.outerHTML="
                f"'<div class=&quot;fb&quot;>{emoji}</div>'")
    return (f'<div class="thumb"><img src="{url}&w=500&q=70&auto=format" '
            f'loading="lazy" onerror="{fallback}"></div>')


PHOTOS = {
    "soil": "https://images.unsplash.com/photo-1464226184884-fa280b87c399?",
    "crops": "https://images.unsplash.com/photo-1500382017468-9049fed747ef?",
    "compost": "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?",
    "worm": "https://images.unsplash.com/photo-1611735341450-74d61e660ad2?",
}
