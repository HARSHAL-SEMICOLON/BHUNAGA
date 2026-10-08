"""
Ways to reach Bhunaga that are not the web app.

    webhook.py    WhatsApp messages and IVR phone calls, over Twilio

A channel is deliberately thin. It converts its own message format into a
question, hands it to farmer/assistant.py, and converts the answer back. None of
them contains any farming logic, which is why adding a new one — SMS, Telegram,
a missed-call service — is a small file rather than a second copy of the app.
"""
