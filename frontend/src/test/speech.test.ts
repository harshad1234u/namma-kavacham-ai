import { describe, expect, it } from "vitest";
import { buildSpokenReport, pickVoice, redactForSpeech } from "../services/speech";
import { makeResponse } from "./fixtures";

const voice = (lang: string, name = lang, localService = true) => ({ lang, name, localService }) as SpeechSynthesisVoice;

describe("redactForSpeech", () => {
  it.each([
    ["Call +91 98765 43210 now", "98765"],
    ["Call 9876543210 now", "9876543210"],
    ["Aadhaar 1234 5678 9012 will be blocked", "5678"],
    ["Account 123456789012 is frozen", "123456789012"],
    ["Card 4111-1111-1111-1111", "4111"],
    ["PAN ABCDE1234F must be updated", "ABCDE1234F"],
    ["Your OTP is 4829 today", "4829"],
    ["Share code: 482913", "482913"],
    ["உங்கள் கடவுச்சொல் 4829 ஐப் பகிரவும்", "4829"],
    ["Write to victim.name@gmail.com", "@"],
    ["key gsk_abcdefghijklmnopqrstuvwxyz0123", "gsk_"],
    ["token 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b", "9f86d081"],
    ["Sender ******3210", "3210"],
  ])("hides sensitive data in %j", (text, secret) => {
    const spoken = redactForSpeech(text, "en");
    expect(spoken).not.toContain(secret);
    expect(spoken).toContain("(hidden)");
  });

  it("reads only the site name of a link, never its path or query", () => {
    const spoken = redactForSpeech("Visit http://sbi-kyc.example.cc/login?acct=12345&otp=9999 now", "en");
    expect(spoken).toBe("Visit sbi-kyc.example.cc now");
    expect(redactForSpeech("Open pm-kisan-gov.in/verify?id=AB12 today", "en")).toBe("Open pm-kisan-gov.in today");
  });

  it("keeps official guidance, short amounts, and the score", () => {
    const text = "Call 1930 or report at cybercrime.gov.in. Do not pay the ₹50 fee. Score 88 out of 100.";
    expect(redactForSpeech(text, "en")).toBe(text);
  });

  it("uses a Tamil placeholder for Tamil speech", () => {
    expect(redactForSpeech("அழைக்கவும் 9876543210", "ta")).toBe("அழைக்கவும் (மறைக்கப்பட்டது)");
  });
});

describe("pickVoice", () => {
  const voices = [voice("en-US", "US"), voice("en-IN", "India"), voice("hi-IN")];

  it("prefers Indian English, then any English voice", () => {
    expect(pickVoice(voices, "en")?.name).toBe("India");
    expect(pickVoice([voice("en-GB", "UK")], "en")?.name).toBe("UK");
  });

  it("picks a ta-IN voice, including underscore-style tags", () => {
    expect(pickVoice([...voices, voice("ta-IN", "Tamil")], "ta")?.name).toBe("Tamil");
    expect(pickVoice([voice("ta_IN", "Tamil2")], "ta")?.name).toBe("Tamil2");
  });

  it("never substitutes another language when no Tamil voice exists", () => {
    expect(pickVoice(voices, "ta")).toBeNull();
  });

  it("ignores online voices, which would send the text to a remote service", () => {
    expect(pickVoice([voice("ta-IN", "Google Tamil", false)], "ta")).toBeNull();
    expect(pickVoice([voice("en-IN", "Google", false), voice("en-US", "Local")], "en")?.name).toBe("Local");
  });
});

describe("buildSpokenReport", () => {
  it("reads level, action, score, explanation, steps and helpline — not the evidence excerpt or URL path", () => {
    const text = buildSpokenReport(makeResponse(), "en").join(" ");
    expect(text).toContain("Risk level: Critical.");
    expect(text).toContain("Indicator strength: 88 out of 100.");
    expect(text).toContain("not a probability");
    expect(text).toContain("Strong scam indicators were detected.");
    expect(text).toContain("1. Do not share any OTP.");
    expect(text).toContain("1930");
    expect(text).not.toContain("share the otp"); // evidence "observed" excerpt of the original message
    expect(text).not.toContain("pay.apk");
  });

  it("uses the Tamil explanation and steps for Tamil", () => {
    const text = buildSpokenReport(makeResponse(), "ta").join(" ");
    expect(text).toContain("வலுவான மோசடிக் குறிகள் கண்டறியப்பட்டன.");
    expect(text).toContain("எந்த OTP-யையும் பகிர வேண்டாம்.");
    expect(text).toContain("மிக அதிகம்");
    expect(text).not.toContain("Strong scam indicators");
  });

  it("redacts sensitive data that reaches the explanation", () => {
    const response = makeResponse({
      explanation: { en: "Do not call 98765 43210 or open http://x.cc/a?otp=1234.", ta: "", generated_by: "groq", note: null },
    });
    const text = buildSpokenReport(response, "en").join(" ");
    expect(text).not.toMatch(/98765|otp=1234|\/a\?/);
    expect(text).toContain("x.cc");
  });

  it("gives no score for insufficient content", () => {
    const response = makeResponse({ risk: { ...makeResponse().risk, assessment_status: "insufficient_content" } });
    const text = buildSpokenReport(response, "en").join(" ");
    expect(text).toContain("Not enough content to assess");
    expect(text).not.toContain("out of 100");
  });

  it("splits long text into short chunks and keeps numbered steps whole", () => {
    const long = Array.from({ length: 30 }, (_, i) => `Clause ${i} about a risky link`).join(", ");
    const chunks = buildSpokenReport(makeResponse({ explanation: { en: long, ta: "", generated_by: "groq", note: null } }), "en");
    expect(Math.max(...chunks.map((c) => c.length))).toBeLessThanOrEqual(160);
    expect(chunks).toContain("1. Do not share any OTP.");
  });
});
