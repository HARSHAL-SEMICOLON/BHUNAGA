"""
Everything the farmer actually sees.

Split out of app.py, which had grown to the point where the styling, the screens
and the wiring were all tangled together in one file.

    theme.py         design tokens, the stylesheet, and the page header
    nav.py           which screen we are on, and the sidebar navigation
    sidebar.py       navigation, language, profile, knowledge base, settings
    home.py          the picture-first landing screen
    ask.py           the question screen — speak, tap, or type
    council_view.py  the council's deliberation panel
    tools.py         Today, Money and Market

Nothing in here talks to Groq or Qdrant directly. The screens call into
farmer/ and draw what comes back, which keeps the logic testable without
Streamlit in the way.
"""
