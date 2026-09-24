// Fictional demo messages modelled on common Indian scam patterns. Numbers and domains are
// illustrative; they are shown as plain text and never rendered as clickable links.

export interface Sample {
  id: string;
  tag: { en: string; ta: string };
  tone: "critical" | "caution" | "advisory";
  title: { en: string; ta: string };
  body: string;
}

export const SAMPLES: Sample[] = [
  {
    id: "tneb",
    tag: { en: "Critical Risk", ta: "மிக அதிக ஆபத்து" },
    tone: "critical",
    title: { en: "TNEB Power Disconnection", ta: "மின் இணைப்புத் துண்டிப்பு" },
    body:
      "Dear Customer, Your electricity power will be disconnected tonight at 9:30 PM due to unpaid bill of Rs480. " +
      "Immediately pay or call electricity officer at 98765-43210 or download update app at http://tneb-billupdate.in/pay.apk",
  },
  {
    id: "pmkisan",
    tag: { en: "Phishing Risk", ta: "மோசடி இணைப்பு" },
    tone: "critical",
    title: { en: "PM-Kisan Benefit Fee", ta: "PM-Kisan நலத்திட்டக் கட்டணம்" },
    body:
      "URGENT: Your PM-Kisan 16th installment benefit of ₹5,000 is on hold. Pay ₹50 processing & verification charge " +
      "immediately to release payment. Click http://pm-kisan-gov.in.payment-desk.cc/verify or call 91234-56789. Do not ignore.",
  },
  {
    id: "aadhaar",
    tag: { en: "Credential Theft", ta: "OTP திருட்டு" },
    tone: "critical",
    title: { en: "Aadhaar Suspension / OTP", ta: "ஆதார் முடக்கம் / OTP" },
    body:
      "UIDAI ALERT: உங்கள் ஆதார் இன்று இரவு இடைநிறுத்தப்படும். Your Aadhaar will be suspended today. " +
      "Share the OTP sent to your mobile with our verification officer to stop this.",
  },
  {
    id: "advisory",
    tag: { en: "Safety Advisory", ta: "பாதுகாப்பு அறிவுரை" },
    tone: "advisory",
    title: { en: "Official-style Bank Advisory", ta: "வங்கி அறிவுரை" },
    body:
      "Your bank will never ask for your PIN, OTP, or password over phone, SMS, or email. Do not share your OTP with anyone.",
  },
];
