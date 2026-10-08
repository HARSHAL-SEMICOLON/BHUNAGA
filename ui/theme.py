"""
How the app looks, and the bar across the top.

All the CSS lives here rather than being sprinkled through the screens, so
changing a colour is one edit in one file.

Two rules drive most of the sizing. Buttons are at least 48 pixels tall, because
that is about the size of a fingertip and this app is used on a phone in a
field. And nothing is ever explained by colour alone -- every state also has an
icon or a word, because a lot of farmers are older men and red/green colour
blindness is common.
"""

from __future__ import annotations

import streamlit as st

# the palette, in one place
PRIMARY = "#2c4a1e"
ACCENT = "#a8e063"
DARK = "#2c1f0e"
GOLD = "#e8d5a3"
CREAM = "#fbf7ef"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');

:root{
  --bg:#f5f0e8; --primary:#2c4a1e; --accent:#a8e063; --dark:#2c1f0e;
  --gold:#e8d5a3; --cream:#fbf7ef;
}
.stApp{ background:
   radial-gradient(900px 320px at 100% -80px, #ece3cf 0%, rgba(236,227,207,0) 70%),
   var(--bg); }
#MainMenu, footer, header{visibility:hidden;}
html, body, [class*="css"]{ font-family:'Inter',sans-serif; color:var(--dark); }
.block-container{ padding-top:.4rem; max-width:1120px; }
h1,h2,h3,.serif{ font-family:'Playfair Display',serif !important; color:var(--primary); }

/* sticky navbar */
.navbar{ position:sticky; top:0; z-index:9999; background:var(--dark);
  border-radius:0 0 16px 16px; padding:12px 22px; display:flex; align-items:center;
  gap:14px; box-shadow:0 6px 18px rgba(44,31,14,.25); margin-bottom:14px;}
.navbar .logo{ font-size:1.7rem; font-weight:800; color:var(--gold);
  font-family:'Playfair Display',serif;}
.navbar .sub{ color:#e9dcc0; font-size:.9rem; opacity:.9;}

/* hero */
.hero{ border-radius:18px; padding:54px 40px; margin-bottom:10px; color:#f3fbe9;
  background:linear-gradient(135deg,#2c4a1e 0%, #1c3312 60%, #14260d 100%);
  box-shadow:0 12px 34px rgba(28,51,18,.3); position:relative; overflow:hidden;}
.hero:after{content:"🌾"; position:absolute; right:24px; bottom:-12px; font-size:7rem;
  opacity:.12;}
.hero h1{ color:#f4fbe9 !important; font-size:2.9rem; line-height:1.1; margin:0 0 8px;}
.hero .mr{ color:var(--accent); font-size:1.35rem; font-weight:600; margin-bottom:8px;}
.hero p{ color:#dcebcd; font-size:1.05rem; max-width:640px;}

/* ticker */
.ticker{ overflow:hidden; white-space:nowrap; background:var(--gold);
  border:1px solid #d8c285; border-radius:12px; padding:9px 0; margin:12px 0 18px;}
.ticker span{ display:inline-block; padding-left:100%; animation:scroll 26s linear infinite;
  color:#5a4318; font-weight:600;}
@keyframes scroll{ 0%{transform:translateX(0);} 100%{transform:translateX(-100%);} }

/* cards */
.grid{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:6px 0 8px;}
.grid2{ grid-template-columns:repeat(2,1fr);}
@media (max-width:820px){ .grid,.grid2{ grid-template-columns:1fr 1fr;} .hero h1{font-size:2.1rem;} }
@media (max-width:520px){ .grid,.grid2{ grid-template-columns:1fr;} }
.card{ background:var(--cream); border:1.5px solid #d8c79f; border-radius:12px;
  padding:18px 16px; box-shadow:0 4px 12px rgba(44,31,14,.07);}
.card .ic{ font-size:2.1rem;}
.card h4{ font-family:'Playfair Display',serif; color:var(--primary); margin:.4rem 0 .3rem;
  font-size:1.12rem;}
.card p{ color:#5b4a30; font-size:.92rem; margin:0;}
.card img,.thumb img{ width:100%; height:120px; object-fit:cover; border-radius:10px;}
.thumb .fb{ width:100%; height:120px; border-radius:10px; display:flex; align-items:center;
  justify-content:center; font-size:2.6rem;
  background:linear-gradient(135deg,#3d6b2c,#243f17); color:#dff3c4;}

/* the big picture tiles on the home screen. these are the main way in for
   anyone who cannot read the labels, so the icon is deliberately huge. */
.tile{ background:var(--cream); border:2px solid #d8c79f; border-radius:16px;
  padding:20px 12px 14px; text-align:center; box-shadow:0 4px 12px rgba(44,31,14,.07);
  margin-bottom:-8px;}
.tile .ic{ font-size:3.4rem; line-height:1.1;}
.tile .nm{ font-family:'Playfair Display',serif; color:var(--primary);
  font-size:1.12rem; font-weight:700; margin-top:6px;}
.tile .sub{ color:#7a6647; font-size:.82rem;}

/* one question, as a card you can tap instead of typing */
.qcard{ background:var(--cream); border:1.5px solid #d8c79f; border-left:5px solid var(--accent);
  border-radius:12px; padding:12px 14px; margin-bottom:-8px;}
.qcard .ic{ font-size:1.6rem;}
.qcard .tx{ color:#3c3018; font-size:.93rem; font-weight:600; line-height:1.35;}

/* friends section */
.friends{ background:linear-gradient(135deg,#243f17,#19300f); border-radius:18px;
  padding:26px 22px; margin:14px 0; color:#eaf6dc;}
.friends h2{ color:#f3fbe9 !important;}
.friend{ background:rgba(255,255,255,.06); border:1px solid #3f6a2b; border-radius:12px;
  padding:16px; text-align:center;}
.friend .e{ font-size:2.6rem;} .friend h4{ color:var(--accent); margin:.3rem 0;}
.friend p{ color:#d7e8c6; font-size:.86rem; margin:0;}

/* soil progress */
.stProgress > div > div > div > div{ background-color:var(--primary) !important; }
.soil-row{ font-weight:600; color:var(--primary); margin-bottom:-6px;}

/* newsletter + footer */
.news{ background:#dfe7cf; border:1.5px solid #bccf9d; border-radius:16px;
  padding:24px; margin:16px 0;}
.footer{ background:var(--dark); color:#e9dcc0; border-radius:16px 16px 0 0;
  padding:22px 26px; margin-top:18px; font-size:.9rem;}
.footer b{ color:var(--gold); font-family:'Playfair Display',serif;}

/* council of experts */
.consensus{ display:flex; align-items:center; gap:12px; background:var(--cream);
  border:1.5px solid #d8c79f; border-radius:12px; padding:11px 16px; margin:8px 0 4px;}
.consensus .lbl{ font-weight:700; color:var(--primary); white-space:nowrap;
  font-size:.92rem;}
.consensus .note{ color:#7a6647; font-size:.83rem; white-space:nowrap;}
.meter{ flex:1; height:9px; border-radius:99px; background:#e4dcc6; overflow:hidden;
  min-width:80px;}
.meter i{ display:block; height:100%; border-radius:99px;}
.m-strong i{ background:linear-gradient(90deg,#6aa84f,#a8e063);}
.m-partial i{ background:linear-gradient(90deg,#c9922e,#e8d5a3);}
.m-split i{ background:linear-gradient(90deg,#a83e2b,#d98b63);}

.seats{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:4px 0 10px;}
@media (max-width:820px){ .seats{ grid-template-columns:1fr;} }
.seat{ background:var(--cream); border:1.5px solid #d8c79f; border-left:5px solid var(--primary);
  border-radius:12px; padding:14px 15px;}
.seat h5{ font-family:'Playfair Display',serif; color:var(--primary); margin:0 0 8px;
  font-size:1.02rem;}
.seat .body{ color:#4a3c26; font-size:.88rem; line-height:1.5;}
.seat.quiet{ border-left-color:#b9a880; opacity:.72;}
.seat.quiet .body{ font-style:italic; color:#7a6647;}
.seat.broke{ border-left-color:#a83e2b;}
.clash{ background:#f6e6de; border:1.5px solid #d9a68f; border-radius:10px;
  padding:10px 14px; margin:6px 0; color:#7d3520; font-size:.89rem;}
.gavel{ background:linear-gradient(135deg,#243f17,#19300f); color:#eaf6dc;
  border-radius:12px; padding:12px 16px; margin:6px 0 10px; font-size:.88rem;}
.gavel b{ color:var(--accent);}

/* one day in the week-ahead strip */
.day{ background:var(--cream); border:1.5px solid #d8c79f; border-radius:10px;
  padding:8px 4px; text-align:center;}
.day .d{ color:#7a6647; font-size:.72rem; font-weight:600;}
.day .e{ font-size:1.5rem; line-height:1.3;}
.day .t{ color:var(--primary); font-size:.8rem; font-weight:700;}
.day .r{ color:#4a7fa8; font-size:.72rem;}

/* a good stretch of hours for spraying */
.window{ background:#e7eddc; border-left:5px solid #6aa84f; border-radius:10px;
  padding:10px 14px; margin:6px 0; color:#2f3f1e; font-size:.92rem;}

/* the farmer's own question, above the answer */
.asked{ background:#e7eddc; border-left:5px solid var(--primary); border-radius:10px;
  padding:10px 14px; margin:14px 0 4px; color:#33291a; font-weight:600;}

/* buttons -- 48px minimum, this gets used on a phone in a field */
.stButton>button{ border-radius:12px; border:1.5px solid #c3b488; background:var(--cream);
  color:var(--primary); font-weight:700; min-height:48px;}
.stButton>button:hover{ border-color:var(--primary); color:var(--dark); background:#fffdf7;}
button[kind="primary"]{ background:var(--primary)!important; color:#f4fbe9!important;
  border:none!important;}
/* the five main navigation buttons, bigger again */
.mainnav .stButton>button{ min-height:60px; font-size:1.02rem;}
</style>
"""


def apply() -> None:
    """Load the stylesheet and draw the bar across the top."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="navbar">'
        '<span class="logo">🪱 Bhunaga</span>'
        '<span class="sub">भुनागा — शेतकऱ्याचा सर्वोत्तम मित्र '
        "(Farmer's Best Friend)</span>"
        "</div>",
        unsafe_allow_html=True)


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
