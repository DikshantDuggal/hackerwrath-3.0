# Edgerunners: pitch script for the judges

About 6 minutes, then questions. Follows `Edgerunners-Pitch-BankFraud.pptx` (20 slides). Lines in *italics* are stage directions. Fill in the three [brackets] before you present.

---

## 1 · Title (0:00)
Picture this. Your phone rings. "This is Rohit from your bank's fraud team. We've caught a ₹49,800 charge on your card. Read me the OTP so I can cancel it."

You panic, and you read it out. But that OTP doesn't cancel the payment. It approves it.

We're Edgerunners. We warn you during the call, in Punjabi, Hindi or English, on any Android phone, and only you hear it.

## 2 · The call (0:25)
It's one request, and it sounds reasonable in the moment. That's why it works.

## 3 · The trick (0:35)
First they scare you: they quote your card digits and say money is leaving. Then they trigger a real OTP and ask for it. The moment you read it out, the money is gone.

There's no link and no fake website, just a convincing voice and a countdown. Real banks never ask you to read out an OTP, least of all to cancel a charge.

## 4 · Today (1:05)
There is protection today. Google warns you during scam calls, but only in Hindi and English, on a Pixel or a recent flagship. Truecaller tells you who's calling, but a scammer on a fresh SIM looks clean.

## 5 · The question (1:25)
So we asked a different question. Not *who* is calling, but *what are they asking you to do?* Scan a QR to "receive" money, type your UPI PIN, share an OTP, or install an app that shares your screen. That request is the scam.

## 6 · Try it (1:40)
Let me show you. *Click "A bank officer asks for your OTP".*

## 7–11 · Demo: the bank fraud call (1:45)
- **7, the phone rings:** [CALLER] is calling from an ordinary phone. There's no app on their side. Our user answers in Edgerunners. *Click Answer.*
- **8, listening:** See the ring? That's scam check. It breathes slowly while it listens, and you can forget it's there.
- **9, they ask:** He asks for the code. A chime, a buzz, and the ring turns amber, [MEASURED: X] seconds after the request. An instant phrase check caught it, and the AI check is confirming.
- **10, high risk:** High risk. First, exactly what happened. Under it, *what they said*: claimed to be the bank, asked for the code, rushed you. Then the truth: that code approves the payment. Then what to do. Ending the call is one tap; to keep talking you have to press and hold. A spoken warning plays in your ear, and the caller hears nothing. *Click End call.*
- **11, call story:** Afterwards, a short story of what happened. No audio and no transcript are kept, only these moments, on your phone. *Click Continue to skip the other demos, or Try another call if you have time.*

*(Optional, if time allows: slides 12–13, the refund scam asking for a UPI PIN; slides 14–15, an ordinary call where the app stays silent. Key line on 15:)* We never say a call is safe. No check can promise that, so the ring is never green.

## 16 · How it works (3:30)
The caller dials our number from any phone. Twilio connects the call and streams only the caller's voice to Sarvam, which turns Punjabi, Hindi, English and mixed speech into text live.

Then two checks. An instant phrase check gives the first warning. Then plug-in detectors confirm it: rules, a retrieval check against known scam calls, and an AI pass. But no detector decides what you see. Our policy decides Possible or High risk, and it never lets the AI raise a level without evidence or take a High risk warning down.

We store no audio and no transcript, and the app never says "safe".

## 17 · Design rules (4:10)
Four rules we never break: we never say safe, ending is one tap, nothing is recorded, and it works on any Android phone, because the checking runs on our server.

## 18 · Built this weekend (4:30)
Here's what works today:
- **The Android app:** call screens, an alert that changes its look so you never tune it out, and the "What they said" chips, now including screen-sharing asks.
- **The backend:** a private warning channel to the phone, demo calls, and that policy, with 57 automated tests.
- **A detection engine** from our teammate Dikshant: live Sarvam speech-to-text, rules that don't flag safety advice like "never share your OTP", and a retrieval check trained on thousands of English and Hindi scam dialogues.
- **A prototype that listens to a Telegram call** and checks it live.

Still to connect: the live Twilio audio, that engine into our detector socket, and recorded voice warnings.

## 19 · Next (5:15)
Next: let people forward unknown calls from their own number to the service, flag QR codes and payment links before the call, grow the Telegram prototype into protection for chat-app calls, and eventually run the model on the phone. The business model: platforms pay per protected call minute.

## 20 · Close (5:40)
Google protects Hindi and English calls on a Pixel. Truecaller tells you who's calling. Edgerunners listens for what they're asking you to do, and warns only you, in time to hang up.

We're [TEAM NAMES]. Thank you.

---

## Likely questions, with honest answers

- **"Is the demo a real call?"** The demo is scripted: a scripted caller sends the same warning events the live engine will. The app, the warning channel and the policy are real. Live Twilio audio is the piece we're still connecting. *(Never present the demo as a live call.)*
- **"How accurate is it?"** The retrieval engine reports about 99% on its held-out test split of the TeleAntiFraud-28k dialogues. Real calls, with noise and code-mixing, will be harder. That's why a phrase hit alone can only ever give Possible risk, and High risk needs a confident, cited reading.
- **"Can a scammer talk it out of warning?"** The transcript is treated as data, never instructions. And the policy, not the AI, sets the level: "turn the alert off" can't take a High risk warning down.
- **"Privacy?"** Only the caller's side is analysed, and only when scam check is on. We store no audio and no transcripts. Twilio and Sarvam process the audio, and we don't claim nothing is recorded anywhere.
- **"Why not just block numbers?"** A fresh SIM is clean. The request is what stays the same across every scam.
- **"Does it work on WhatsApp?"** Not today. Our Telegram prototype is the first step toward chat-app calls.
- **"Does the caller know?"** No. Cues play only on the user's phone, and the call is muted while they play.
