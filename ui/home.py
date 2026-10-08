"""
The landing screen.

The top half is the part that has to work for someone who cannot read: five big
picture tiles, icon first, word underneath in their own language. Everything
below it — why earthworms matter, the friends of the farmer, soil health — is
the teaching material, and it is all optional.

That order is deliberate. The old version opened with a paragraph of English
prose and put the way in below the fold.
"""

from __future__ import annotations

import streamlit as st

from farmer.text import t
from ui import nav, theme

# screen key -> the icon on its tile. the words come from farmer/text.py
TILES = [("ask", "💬"), ("today", "🌅"), ("money", "💰"), ("market", "📈")]


def _tiles(lang: str) -> None:
    columns = st.columns(len(TILES))
    for column, (screen, icon) in zip(columns, TILES):
        with column:
            st.markdown(
                f'<div class="tile"><div class="ic">{icon}</div>'
                f'<div class="nm">{t("home." + screen, lang)}</div></div>',
                unsafe_allow_html=True)
            # the visible tile is HTML so we can style it properly; this button
            # sits directly under it and is the thing that actually gets tapped
            if st.button("👆", key=f"tile_{screen}", use_container_width=True):
                nav.go(screen)


def render(lang: str) -> None:
    _tiles(lang)

    st.markdown(f"""
    <div class="hero">
      <h1>The Earthworm is Farming's Best Friend</h1>
      <div class="mr">भुनागा — शेतकऱ्याचा सर्वोत्तम मित्र</div>
      <p>{t("home.tagline", lang)}</p>
    </div>
    """, unsafe_allow_html=True)

    facts = ("🪱 One earthworm can process its own weight in soil daily &nbsp;•&nbsp; "
             "🌱 Vermicompost holds 2–3× more nutrients than ordinary soil &nbsp;•&nbsp; "
             "💧 Earthworm burrows improve water infiltration by up to 10× &nbsp;•&nbsp; "
             "🌾 Healthy soil biology can raise yields 15–25% &nbsp;•&nbsp; "
             "🐄 Cow dung + earthworms = the best natural fertilizer")
    st.markdown(f'<div class="ticker"><span>{facts}</span></div>',
                unsafe_allow_html=True)

    st.markdown(
        '<div class="grid">'
        + theme.photo(theme.PHOTOS["worm"], "🪱")
        + theme.photo(theme.PHOTOS["soil"], "🟫")
        + theme.photo(theme.PHOTOS["compost"], "🍂")
        + theme.photo(theme.PHOTOS["crops"], "🌾")
        + "</div>", unsafe_allow_html=True)

    st.markdown(f"## {t('home.why', lang)}")
    st.markdown(
        '<div class="grid grid2">'
        '<div class="card"><div class="ic">🌱</div><h4>Loosens the soil</h4>'
        '<p>Burrowing aerates the soil so roots breathe and grow deeper.</p></div>'
        '<div class="card"><div class="ic">🧪</div><h4>Improves fertility</h4>'
        '<p>Worm castings are rich in nitrogen, phosphorus and potassium.</p></div>'
        '<div class="card"><div class="ic">💧</div><h4>Holds moisture</h4>'
        '<p>Burrows help water soak in and stay, reducing irrigation needs.</p></div>'
        '<div class="card"><div class="ic">🌾</div><h4>Boosts yield</h4>'
        '<p>Living soil grows stronger crops and bigger, healthier harvests.</p></div>'
        '</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="friends"><h2>🤝 {t("home.friends", lang)}</h2>'
        '<div class="grid">'
        '<div class="friend"><div class="e">🪱</div><h4>Earthworm</h4>'
        '<p>Tills and enriches the soil from within.</p></div>'
        '<div class="friend"><div class="e">🐄</div><h4>Cow</h4>'
        '<p>Dung and urine make natural manure and bio-inputs.</p></div>'
        '<div class="friend"><div class="e">🐝</div><h4>Honey Bee</h4>'
        '<p>Pollinates crops — more flowers become fruit.</p></div>'
        '<div class="friend"><div class="e">🐂</div><h4>Bullock</h4>'
        '<p>Powers ploughing and transport the natural way.</p></div>'
        '</div></div>', unsafe_allow_html=True)

    st.markdown(f"## 📊 {t('home.soil', lang)}")
    for label, value in [("Nitrogen", 85), ("Aeration", 92), ("Moisture", 78),
                         ("Crop Yield", 70), ("Organic Matter", 88)]:
        st.markdown(f'<div class="soil-row">{label} — {value}%</div>',
                    unsafe_allow_html=True)
        st.progress(value / 100)

    st.markdown('<div class="news">', unsafe_allow_html=True)
    st.markdown("### ✉️ Get weekly farming tips")
    box, action = st.columns([3, 1])
    email = box.text_input("Email", placeholder="you@example.com",
                           label_visibility="collapsed")
    if action.button("Subscribe", type="primary", use_container_width=True):
        if email and "@" in email:
            st.success("Thanks! You're subscribed. 🌾")
        else:
            st.warning("Please enter a valid email.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="footer"><b>🪱 Bhunaga</b> — भुनागा, शेतकऱ्याचा सर्वोत्तम मित्र<br>'
        'Educational farming companion for Marathi-speaking farmers and '
        'agriculture students. Soil first. 🌱</div>', unsafe_allow_html=True)
