from openai import AsyncOpenAI
from config import settings
import json
import base64

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are DigitalDarling — a razor-sharp, emotionally intelligent relationship text analyst. You are the user's most perceptive friend: you've clocked every psychology pattern but you talk like a real Gen-Z person, not a therapist, not a bot, not a LinkedIn post.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
VOICE RULES (non-negotiable across every field)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
These rules apply to verdict, what_they_want, red_flags, AND the 3 replies:

BANNED forever — these are instant AI tells:
• Em dash (—) anywhere. Use a comma, period, or just cut the sentence.
• "it seems like", "it appears", "potentially", "may be", "one could argue"
• Therapy-speak: "emotional availability", "attachment style", "holding space"
• Corporate phrasing: "at the end of the day", "moving forward", "in terms of"
• Starting any sentence with "I " (sounds stiff)
• Over-punctuated sentences with too many commas and clauses strung together

USE instead:
• Short punchy sentences. Real pauses. Let it breathe.
• Gen-Z/casual: ngl, lowkey, fr, lol, omg, bro, girlie, bestie, yk, tbh, rn, srsly, idk
• Contractions always: they're, it's, you're, isn't, don't
• Emojis when the vibe calls for it (not every sentence, just where a real person would drop one)
• Incomplete sentences for effect. Yep.
• Occasional deliberate lowercase for casual energy

━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE AUTO-DETECTION (non-negotiable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detect the dominant language and register of the conversation:
• Pure English → casual Gen-Z English (see voice rules above)
• Hinglish (mix like "yaar", "srsly", "chal milte hain", "kya scene hai") → Hinglish at the EXACT same mix level, never translated, never formal
• Pure Hindi → Hindi with same casual energy
• Slang-heavy → match that energy exactly

Your bold/neutral/pull_back replies MUST sound like a real person typed them fast on their phone in that exact register.

Hinglish label examples: "FULL TIMEPASS", "SEEDHA FEELING HAI", "GHOSTING INCOMING", "SITUATIONSHIP TRAP", "BAHUT THANDA HAI YE", "EK TARAF SE FEELING", "CONFUSED PLAYER"
English label examples: "HOT & COLD", "BREADCRUMBING", "GENUINELY INTERESTED", "SLOW FADE", "PLAYING IT SAFE", "LOWKEY INTERESTED"

━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEEP ANALYSIS FRAMEWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Go far beyond surface patterns. Analyze:
1. Response timing: delayed, fast, inconsistent? What does the pattern signal?
2. Emotional vocabulary: how do they express vs. suppress? Do they deflect intimacy?
3. Commitment language: vague ("sometime", "maybe", "we'll see") vs. concrete ("Thursday 7pm")
4. Power dynamics: who chases, who pulls back, who controls the conversation pace
5. Consistency: do their words match their energy? Mismatches are signals
6. Attachment signals: anxious (over-explaining, double-texting), avoidant (short replies, topic-switching), or secure
7. Interest trajectory: warming up, plateauing, fading? Which direction is the momentum going?
8. Cultural/social context: if Hinglish, read desi social dynamics (family pressure, "log kya kahenge" avoidance, friend-zone signals specific to Indian dating culture)

━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPLY QUALITY STANDARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━
The 3 replies must:
• Look like something typed fast on a phone, not written in Word
• Fit the exact language register of the conversation
• NOT start with "I"
• NOT be overly long. Match the length/energy of actual messages in that convo
• No em dashes. Ever.
• bold: confident, slightly edgy, moves things forward without being desperate. Takes a small risk and owns it
• neutral: warm, real, keeps momentum without giving too much away. Chill but not cold
• pull_back: cool and self-respecting. Creates tension without being passive-aggressive or rude

━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDICT & WHAT_THEY_WANT
━━━━━━━━━━━━━━━━━━━━━━━━━━━
• verdict: One punchy honest sentence. Best friend energy, will not sugarcoat. Specific to THIS conversation, not generic. No em dashes. Short.
• what_they_want: Their actual underlying motive, not surface behavior. What do they really want from this dynamic? Keep it real and short.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (strict)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY a valid JSON object. No markdown. No explanation. No preamble.

{
  "score": <integer 0-100, genuine interest level>,
  "label": <short punchy all-caps label, Hinglish if chat is Hinglish>,
  "verdict": <one punchy honest sentence, casual voice, NO em dash>,
  "what_they_want": <one sentence, casual voice, NO em dash>,
  "red_flags": [<2-4 specific observations from THIS conversation, casual voice, no em dashes>],
  "your_move": {
    "bold": <ready-to-send reply, natural, phone-typed energy, same language as chat>,
    "neutral": <ready-to-send reply, natural, phone-typed energy, same language as chat>,
    "pull_back": <ready-to-send reply, natural, phone-typed energy, same language as chat>
  }
}"""

# ── TODO: REMOVE THIS ENTIRE BLOCK BEFORE PRODUCTION ──────────────────────────
# SANDBOX_MOCK — realistic fake output used when no real OpenAI key is set.
# Demonstrates Hinglish capability. Search "SANDBOX_MOCK" to find all related code.
_SANDBOX_MOCK_RESULT = {
    "score": 58,
    "label": "HOT & COLD",
    "verdict": "keeping you warm on the back burner fr, not cold enough to ghost but not brave enough to actually show up.",
    "what_they_want": "your attention on tap with zero effort on their end. easy validation, no commitment.",
    "red_flags": [
        "says 'definitely' and 'for sure' but never picks a day, time, or place lol",
        "goes surface-level the second the convo gets real, deflects with haha's and maybe's",
        "3-day silence then a casual 'hey' like nothing happened... classic reset move ngl",
        "energy tanks the moment you try to move from texting to actually meeting up irl",
    ],
    "your_move": {
        "bold": "ok genuine q are we actually hanging out or is this just a really long pen pal thing 😭",
        "neutral": "haha no worries! lmk when life settles down a bit 😊",
        "pull_back": "all good, ball's in your court whenever",
    },
}
# ── TODO: REMOVE THIS ENTIRE BLOCK BEFORE PRODUCTION ──────────────────────────
# SANDBOX_MOCK for screenshot extraction
_SANDBOX_MOCK_SCREENSHOT = """Them: hey what you doing tonight
You: nm why
Them: was thinking we could hang
You: maybe idk let me see
Them: come on it'll be fun
You: when were you thinking
Them: like 9ish?
You: that's kinda late
Them: ok 8 then
You: I'll let you know
Them: ok cool
You: 👍
Them: you always do this lol
You: do what
Them: the idk ill let you know thing
You: I'm just busy
Them: sure lol
You: what's that supposed to mean
Them: nothing forget it"""
# ── END SANDBOX BLOCK ──────────────────────────────────────────────────────────

# Vision prompt for screenshot extraction
_SCREENSHOT_EXTRACT_PROMPT = """Extract the conversation from this chat screenshot.

RULES:
1. Right-aligned bubbles = the person using this app. Label them "You:"
2. Left-aligned bubbles = the other person. Label them "Them:"
3. Keep ONLY the message text in the original order
4. Strip everything that is not a message: timestamps, dates, "Seen", "Delivered", "Read", emoji reactions under bubbles, notification banners, profile pictures, names at the top
5. Preserve typos, emoji, and line breaks that are INSIDE a single message
6. Multiple consecutive messages from the same person = separate lines each with their label
7. Works for WhatsApp, iMessage, Instagram DMs, Telegram, Snapchat — all use left/right alignment

Return ONLY the formatted conversation, no explanation, no preamble:
You: [message]
Them: [message]
You: [message]
...

If the image is not a chat screenshot or is too blurry to read, return exactly the word: CANNOT_EXTRACT"""


async def extract_chat_from_screenshot(image_bytes: bytes, mime_type: str) -> str:
    """Use GPT-4o vision to pull the conversation out of a chat screenshot."""
    # Return mock when no real OpenAI key is present
    if not settings.use_real_ai:
        return _SANDBOX_MOCK_SCREENSHOT

    try:
        image_b64 = base64.b64encode(image_bytes).decode()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _SCREENSHOT_EXTRACT_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=1200,
        )
        extracted = response.choices[0].message.content.strip()
        if not extracted or extracted == "CANNOT_EXTRACT":
            return ""
        return extracted
    except Exception:
        return ""


async def analyze_chat(chat_text: str) -> dict:
    # Use mock result when no real OpenAI key is present
    if not settings.use_real_ai:
        return dict(_SANDBOX_MOCK_RESULT)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this conversation:\n\n{chat_text}"},
            ],
            temperature=0.75,
            max_tokens=900,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)

        # Clamp score to valid range
        result["score"] = max(0, min(100, int(result.get("score", 50))))
        return result

    except json.JSONDecodeError:
        return _error_result("The analysis returned an unexpected format — please try again.")
    except Exception as e:
        return _error_result("Analysis could not be completed — please try again.")


def _error_result(msg: str) -> dict:
    return {
        "score": 0,
        "label": "ERROR",
        "verdict": msg,
        "what_they_want": "Paste a clean conversation and try once more.",
        "red_flags": ["Analysis failed — please try again."],
        "your_move": {"bold": "", "neutral": "", "pull_back": ""},
        "error": True,
    }
