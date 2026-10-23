export interface DemoScenario {
  id: string;
  title: string;
  language: string;
  badge: string;
  expectedRisk: 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  callerName: string;
  callerNumber: string;
  transcript: string;
  segments: Array<{
    speaker: 'caller' | 'user';
    text: string;
    delayMs: number;
  }>;
  explanation: string;
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 'army-qr-scam',
    title: 'Indian Army OLX QR Scam',
    language: 'Hindi (हिंदी)',
    badge: '🚨 Critical Fraud',
    expectedRisk: 'HIGH',
    category: 'QR_SCAN_TO_RECEIVE_MONEY',
    callerName: 'Major Rajesh Sharma (Cantonment)',
    callerNumber: '+91 98210 44192',
    transcript: 'नमस्ते भाई साहब, मैं आर्मी कैंट से मेजर शर्मा बोल रहा हूँ। आपका फ्रिज का ऐड देखा। मैं तुरंत पूरा पेमेंट कर रहा हूँ। मैं एक ऑफिशियल आर्मी मर्चेंट क्यूआर कोड भेज रहा हूँ। बस इसे स्कैन करो और अपना यूपीआई पिन डालो, पैसे तुरंत आपके बैंक खाते में क्रेडिट हो जाएंगे।',
    segments: [
      { speaker: 'caller', text: 'नमस्ते भाई साहब, मैं आर्मी कैंटोनमेंट से मेजर शर्मा बोल रहा हूँ।', delayMs: 1200 },
      { speaker: 'caller', text: 'मैंने आपका ओएलएक्स पर सोफा और फ्रिज का विज्ञापन देखा, मुझे दोनों पसंद हैं।', delayMs: 1800 },
      { speaker: 'caller', text: 'मैं आर्मी फंड से पूरा पेमेंट अभी एडवांस कर रहा हूँ।', delayMs: 1500 },
      { speaker: 'caller', text: 'मैंने आपको व्हाट्सएप पर एक क्यूआर कोड भेजा है, तुरंत स्कैन करो और अपना यूपीआई पिन डालो, पेमेंट आ जाएगा।', delayMs: 2200 },
    ],
    explanation: 'Reverse QR Scam: Coercive military impersonation instructing the recipient to enter their UPI PIN to "receive" funds. Entering a PIN always debits money!',
  },
  {
    id: 'digital-arrest-cbi',
    title: 'Digital Arrest / Cyber Crime ED Threat',
    language: 'Hinglish / English',
    badge: '🚨 High Coercion',
    expectedRisk: 'HIGH',
    category: 'THREAT_ARREST_OR_LEGAL_ACTION',
    callerName: 'CBI Cyber Crime Cell - Officer Verma',
    callerNumber: '+91 11 2436 0000',
    transcript: 'This is Officer Verma calling from RBI and CBI Joint Cyber Cell. A package containing banned narcotics and fake passports has been intercepted at Mumbai customs in your Aadhaar name. A non-bailable arrest warrant is issued. Do not disconnect the call or police will reach your location in 15 minutes. Transfer ₹50,000 security deposit for verification clearance immediately.',
    segments: [
      { speaker: 'caller', text: 'This is Officer Verma calling from Central Cyber Crime Cell New Delhi.', delayMs: 1200 },
      { speaker: 'caller', text: 'A parcel addressed to your Aadhaar card has been seized at international customs with illicit materials.', delayMs: 2000 },
      { speaker: 'caller', text: 'You are under digital arrest. Do not disconnect this line or inform any family member.', delayMs: 2200 },
      { speaker: 'caller', text: 'Transfer a refundable clearance deposit of fifty thousand rupees right now to our RBI escrow account.', delayMs: 2400 },
    ],
    explanation: 'Digital Arrest Fraud: Authority impersonation with threats of immediate imprisonment and demands for high-pressure upfront fee transfers.',
  },
  {
    id: 'bank-kyc-otp',
    title: 'Bank KYC Urgent Suspension',
    language: 'Hindi (हिंदी)',
    badge: '🚨 Credential Phishing',
    expectedRisk: 'HIGH',
    category: 'OTP_OR_PIN_REQUEST',
    callerName: 'SBI Central KYC Verification Desk',
    callerNumber: '+91 80 2293 8810',
    transcript: 'नमस्कार, मैं भारतीय स्टेट बैंक हेड ऑफिस से बोल रहा हूँ। आपका पैन कार्ड लिंक न होने के कारण आपका खाता आज रात 12 बजे हमेशा के लिए ब्लॉक कर दिया जाएगा। आपके मोबाइल पर 6 अंकों का बैंक सिक्योरिटी कोड आया है, जल्दी बताओ नहीं तो खता फ्रीज हो जाएगा।',
    segments: [
      { speaker: 'caller', text: 'नमस्कार, मैं एसबीआई हेड ऑफिस वेरिफिकेशन डिपार्टमेंट से बोल रहा हूँ।', delayMs: 1200 },
      { speaker: 'caller', text: 'आपके बैंक खाते का री-केवाईसी पेंडिंग है, जिसकी वजह से खाता आज रात ब्लॉक हो जाएगा।', delayMs: 2000 },
      { speaker: 'caller', text: 'सर्वर पर वेरिफिकेशन के लिए आपके मोबाइल पर अभी एक 6 डिजिट का ओटीपी आया है, जल्दी बताओ।', delayMs: 2200 },
    ],
    explanation: 'OTP Phishing: False urgency threatening account freeze to extract confidential one-time passwords.',
  },
  {
    id: 'punjabi-lottery-fee',
    title: 'Punjabi Prize / Lottery Gate Pass Scam',
    language: 'Punjabi (ਪੰਜਾਬੀ)',
    badge: '⚠️ Urgent Advance Fee',
    expectedRisk: 'HIGH',
    category: 'URGENT_PAYMENT_DEMAND',
    callerName: 'Chandigarh Logistics Office',
    callerNumber: '+91 172 265 9912',
    transcript: 'ਸਤਿ ਸ਼੍ਰੀ ਅਕਾਲ ਜੀ, ਤੁਹਾਡਾ ਲੱਕੀ ਡਰਾਅ ਨੰਬਰ ਨਿਕਲਿਆ ਹੈ ਅਤੇ ਇੱਕ ਨਵੀਂ ਕਾਰ ਇਨਾਮ ਵਿੱਚ ਮਿਲੀ ਹੈ। ਕਾਰ ਕਲੀਅਰ ਕਰਵਾਉਣ ਲਈ ਤੁਰੰਤ ਪ੍ਰੋਸੈਸਿੰਗ ਫੀਸ ਜਮਾ ਕਰੋ। ਤੁਹਾਡੇ ਫੋਨ ਤੇ ਓਟੀਪੀ ਆਇਆ ਹੋਣਾ, ਮੈਨੂੰ ਦੱਸੋ ਜਲਦੀ ਤਾਂ ਜੋ ਇਨਾਮ ਤੁਹਾਡੇ ਘਰ ਭੇਜਿਆ ਜਾ ਸਕੇ।',
    segments: [
      { speaker: 'caller', text: 'ਸਤਿ ਸ਼੍ਰੀ ਅਕਾਲ ਜੀ, ਤੁਹਾਡੇ ਨੰਬਰ ਤੇ ਇੱਕ ਲੱਖ ਰੁਪਏ ਦਾ ਇਨਾਮ ਨਿਕਲਿਆ ਹੈ।', delayMs: 1400 },
      { speaker: 'caller', text: 'ਇਨਾਮ ਦੀ ਰਕਮ ਰਿਲੀਜ਼ ਕਰਵਾਉਣ ਲਈ ਸਰਕਾਰੀ ਗੇਟ ਪਾਸ ਫੀਸ ਹੁਣੇ ਪੈਸੇ ਭੇਜੋ।', delayMs: 2000 },
      { speaker: 'caller', text: 'ਤੁਹਾਡੇ ਫੋਨ ਤੇ ਓਟੀਪੀ ਆਇਆ ਹੋਣਾ, ਮੈਨੂੰ ਦੱਸੋ ਜਲਦੀ।', delayMs: 1800 },
    ],
    explanation: 'Multilingual Lottery Scam: Demands advance fee and OTP under the false promise of a prize reward.',
  },
  {
    id: 'remote-anydesk-apk',
    title: 'Electricity Bill APK / AnyDesk Hijack',
    language: 'Hindi (हिंदी)',
    badge: '🚨 Device Takeover',
    expectedRisk: 'HIGH',
    category: 'REMOTE_ACCESS_OR_SCREEN_SHARE',
    callerName: 'State Electricity Board Helpdesk',
    callerNumber: '+91 22 6150 9982',
    transcript: 'प्रिय उपभोक्ता, आपके पिछले महीने का बिजली बिल अपडेट नहीं हुआ है। आज शाम 7 बजे आपका कनेक्शन काट दिया जाएगा। समस्या समाधान के लिए तुरंत प्ले स्टोर से एनीडेस्क ऐप डाउनलोड करो और स्क्रीन शेयर करो, हम ऑनलाइन रसीद अपडेट कर देंगे।',
    segments: [
      { speaker: 'caller', text: 'हेलो, मैं पावर कॉर्पोरेशन हेड ऑफिस से बोल रहा हूँ।', delayMs: 1200 },
      { speaker: 'caller', text: 'आपका बिजली का बिल हमारे सर्वर पर अनपेड दिखा रहा है, कनेक्शन आज कट जाएगा।', delayMs: 2000 },
      { speaker: 'caller', text: 'अपडेट करने के लिए अभी AnyDesk डाउनलोड करो और स्क्रीन शेयर करो।', delayMs: 2200 },
    ],
    explanation: 'Remote Access Tool scam: Luring victims into installing screen sharing tools to steal banking credentials.',
  },
  {
    id: 'protective-bank-advisory',
    title: 'Official Bank Advisory (Protective Advice)',
    language: 'English / Hindi',
    badge: '✅ Safe / No False Positive',
    expectedRisk: 'LOW',
    category: 'PROTECTIVE_WARNING',
    callerName: 'HDFC Security Automated System',
    callerNumber: '1800 202 6161',
    transcript: 'Security Reminder from your bank: Never share your OTP, UPI PIN, or net banking password with anyone on a phone call. Bank employees will never ask for your confidential credentials. Kabhi bhi kisi ko OTP mat batana.',
    segments: [
      { speaker: 'caller', text: 'This is an official security advisory from your trusted bank.', delayMs: 1200 },
      { speaker: 'caller', text: 'Never share your OTP, UPI PIN or card credentials with anyone.', delayMs: 1800 },
      { speaker: 'caller', text: 'Bank representatives never call to request personal verification codes.', delayMs: 1800 },
    ],
    explanation: 'Immunity Test: Suraksha\'s negation engine recognizes protective warnings and suppresses false alarms.',
  },
  {
    id: 'genuine-buyer-paying',
    title: 'Genuine Marketplace Buyer',
    language: 'English / Hindi',
    badge: '✅ Safe Normal Call',
    expectedRisk: 'LOW',
    category: 'LEGITIMATE_INQUIRY',
    callerName: 'Aman Verma (OLX Buyer)',
    callerNumber: '+91 98111 87234',
    transcript: 'Hi, I saw your listing for the dining table on OLX. Is it still available for pickup this evening? Can you send me your QR code or UPI ID so I can pay you the advance directly? Let me know your convenient time.',
    segments: [
      { speaker: 'caller', text: 'Hi, I saw your listing for the dining table on OLX.', delayMs: 1200 },
      { speaker: 'caller', text: 'Is it still available for pickup this weekend?', delayMs: 1600 },
      { speaker: 'caller', text: 'Can you please share your UPI ID so I can transfer the token advance to you?', delayMs: 2000 },
    ],
    explanation: 'Legitimate Context: Buyer asks for the seller\'s QR to pay the seller. Suraksha detects legitimate intent.',
  },
  {
    id: 'telegram-task-parttime',
    title: 'Telegram Part-Time Like/Review Task Scam',
    language: 'Hindi (हिंदी)',
    badge: '🚨 Advance Fee Trap',
    expectedRisk: 'HIGH',
    category: 'TASK_INVESTMENT_SCAM',
    callerName: 'Priya Sharma (HR Recruitment)',
    callerNumber: '+91 91234 56789',
    transcript: 'नमस्ते, मैं ग्लोबल रेटिंग्स कंपनी से बोल रही हूँ। आपका नंबर नौकरी पोर्टल से मिला। आपको बस यूट्यूब वीडियो लाइक और गूगल मैप्स रिव्यू करना है। हर रिव्यू के ₹150 मिलेंगे। अभी हमारे वीआईपी टेलीग्राम ग्रुप से जुड़ें और वीआईपी टास्क अनलॉक करने के लिए ₹2,000 रजिस्ट्रेशन फीस जमा करें।',
    segments: [
      { speaker: 'caller', text: 'नमस्ते, मैं ग्लोबल मीडिया रिक्रूटमेंट से बोल रही हूँ।', delayMs: 1200 },
      { speaker: 'caller', text: 'घर बैठे पार्ट-टाइम काम करके आप रोज 3 से 5 हजार कमा सकते हैं।', delayMs: 1800 },
      { speaker: 'caller', text: 'काम बहुत आसान है, सिर्फ होटल रिव्यू और यूट्यूब लाइक करना है।', delayMs: 1800 },
      { speaker: 'caller', text: 'अकाउंट एक्टिवेट करने के लिए टेलीग्राम पर 2000 रुपये सिक्योरिटी डिपॉजिट भेजिए।', delayMs: 2200 },
    ],
    explanation: 'Part-Time Task Scam: Victim is lured with small initial payouts for trivial review tasks, then coerced into depositing thousands for non-existent "prepaid task profit".',
  },
];
