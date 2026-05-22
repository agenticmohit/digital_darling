<div align="center">

<img src="static/images/hero.png" alt="DigitalDarling" width="300" />

# digital*darling*

**Paste a chat. Get the truth.**

*AI-powered relationship text analyst — interest score, red flags, and three ready-to-send replies.*

<br/>

[![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![HTMX](https://img.shields.io/badge/HTMX-3D72D7?style=for-the-badge)](https://htmx.org)
[![OpenAI](https://img.shields.io/badge/GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)

</div>

---

## 🚀 Try it live — no sign-up required

<div align="center">

### **[digitaldarling.app](https://digitaldarling.app)**

Use the beta account to experience the full app with real GPT-4o-mini analysis.

| | |
|:---:|:---|
| 📧 **Email** | `beta_user@dd.com` |
| 🔑 **Password** | `beta1234` |
| ⚡ **Limit** | 5 reads / day · resets midnight UTC |
| 💳 **Payment** | Not required |

*Paste any real conversation or drop a screenshot — live GPT-4o-mini reads the vibe instantly.*

</div>

---

## 🔍 The Problem

Everyone has had *that* conversation — the one you can't stop re-reading.

> *Are they interested or just bored? Do I reply now or wait? What do I even say?*

The emotional labour of decoding texts is **real, constant, and exhausting**. You screenshot it to five friends and still don't know. Existing AI tools give generic advice that ignores tone, timing, and the specific patterns in *this* conversation.

---

## 💡 What I Built

A mobile-first web app that reads a conversation the way your most perceptive friend would — and then actually tells you what to do about it.

<br/>

<div align="center">

| Output | What you get |
|:---:|:---|
| 🎯 **Interest Score** | `0–100` genuine engagement level — not just surface politeness |
| 🏷️ **Label** | Punchy all-caps vibe read: `HOT & COLD` · `BREADCRUMBING` · `GENUINELY INTERESTED` |
| ⚡ **Verdict** | One honest sentence. No sugarcoating |
| 🧠 **True Intent** | What they actually want from this dynamic |
| 🚩 **Red Flags** | 2–4 observations pulled from *this specific* conversation |
| 💬 **3 Replies** | `bold` / `neutral` / `pull back` — written in the exact tone of the chat |

</div>

<br/>

> [!NOTE]
> The AI speaks like a real person — Gen-Z casual, no therapy-speak, no corporate hedging. It auto-detects language register, including **Hinglish**, and matches the tone of the input conversation exactly.

---

## 🏗️ Architecture

```
Browser  ──── HTMX ────▶  FastAPI  ──── async ────▶  OpenAI GPT-4o-mini
                              │
                          Supabase
                       Auth + Postgres
```

This is a **server-rendered SPA** — no React, no Next.js, no build tooling. HTMX handles navigation and partial updates. FastAPI returns HTML fragments. The result is React-level interactivity at a fraction of the complexity.

---

## ⚙️ Key Engineering Decisions

<details>
<summary><strong>HTMX as a SPA alternative — and one sharp edge</strong></summary>
<br/>

`hx-boost="true"` on the body turns every anchor into an XHR that swaps only `#page`, giving full pushState navigation without a client-side router.

**The sharp edge:** HTMX's XHR follows HTTP 303 redirects at the browser level — any `HX-Redirect` header on a 303 is invisible to HTMX. Auth success responses return `200 + HX-Redirect` instead, which is the correct pattern.

</details>

<details>
<summary><strong>Auth without a JS framework</strong></summary>
<br/>

Two flows, handled entirely server-side:
- **Email + password** — Supabase `sign_in_with_password`, JWT stored in an `httponly` cookie
- **Magic link** — Supabase `sign_in_with_otp`, callback verifies `token_hash` server-side

No auth state in `localStorage`. No client-side token handling. JWT validated on every request in `get_current_user()`.

</details>

<details>
<summary><strong>GPT-4o-mini for analysis and screenshot extraction</strong></summary>
<br/>

Upload any chat screenshot — WhatsApp, iMessage, Instagram DMs, Telegram, Snapchat. GPT-4o-mini extracts the conversation using the left/right bubble alignment heuristic (right = You, left = Them). Works universally across all major platforms.

</details>

<details>
<summary><strong>In-memory TTL cache</strong></summary>
<br/>

Identical conversations return cached results instantly. SHA-256 hash as key, `cachetools.TTLCache` with 1-hour expiry and 500-item cap. Prevents redundant OpenAI calls on repeat submissions.

</details>

<details>
<summary><strong>Sandbox mode for local development</strong></summary>
<br/>

`settings.is_sandbox_mode` checks whether credentials are real. If not, the entire auth and AI layer is mocked — realistic fake output, auto-login, zero external calls. The app runs fully locally with just a `.env` file, no accounts needed.

</details>

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Choice | Why |
|:---|:---:|:---|
| Web framework | **FastAPI** | Async, typed, fast — production-grade with minimal boilerplate |
| Templates | **Jinja2** | Server-rendered, pairs perfectly with HTMX |
| Frontend | **HTMX** | SPA feel without a JavaScript build pipeline |
| Styling | **Tailwind CDN** + CSS custom props | Dark/light theme, zero config |
| AI | **OpenAI GPT-4o-mini** | Vision + text in one model; best JSON adherence at low cost |
| Auth + DB | **Supabase** | Instant Postgres + auth, row-level security out of the box |
| Payments | **Razorpay** | Native INR, no card data on our servers |
| Rate limiting | **SlowAPI** | Per-route limits, one decorator |
| Cache | **cachetools** | Zero-dependency in-memory TTL cache |
| Packaging | **uv** | ~10× faster than pip |
| Deploy | **Railway** | Auto-detects Dockerfile, injects `$PORT` |

</div>

---

## 📁 Project Structure

```
digital_darling/
├── main.py                    # App entry, page routes, exception handlers
├── config.py                  # Pydantic settings, sandbox mode detection
│
├── routers/
│   ├── auth.py                # Login, signup, magic link, callback, logout
│   ├── decode.py              # Screenshot upload + chat analysis
│   └── payments.py            # Razorpay order creation + webhook
│
├── services/
│   ├── ai.py                  # GPT-4o-mini analysis + vision extraction
│   ├── supabase_client.py     # Auth helpers, profile/usage/history CRUD
│   ├── beta.py                # In-memory beta user tracking (no DB needed)
│   └── cache.py               # SHA-256 keyed TTLCache
│
├── templates/
│   ├── base.html              # Shell: top bar, nav, theme, PWA, HTMX
│   ├── decode.html            # Chat input + screenshot upload
│   ├── history.html           # Saved reads list
│   ├── pricing.html           # Free vs Paid, Razorpay checkout
│   ├── profile.html           # Auth hub + user settings
│   ├── privacy.html           # Privacy Policy
│   ├── terms.html             # Terms & Conditions
│   ├── refund.html            # Cancellation & Refund Policy
│   └── partials/              # HTMX fragments: result, paywall, error
│
├── static/                    # PWA icons, manifest, service worker
├── Dockerfile                 # Railway-ready, uv install, non-root user
└── pyproject.toml             # uv project config
```

---

## 🚀 Running Locally

**Prerequisites:** Python 3.12+ · [uv](https://github.com/astral-sh/uv)

```bash
git clone https://github.com/yourusername/digital-darling
cd digital-darling

uv pip install -r requirements.txt
cp .env.example .env          # fill in your keys
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

> [!TIP]
> **Sandbox mode** — if `ENVIRONMENT=development` or your Supabase keys are placeholders, the app runs with mocked auth and AI responses. No real credentials needed to explore locally.

### Environment variables

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_JWT_SECRET=your_jwt_secret
OPENAI_API_KEY=sk-...
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=your_secret
APP_URL=http://localhost:8000
ENVIRONMENT=development
```

---

## ☁️ Deployment

1. Push to GitHub
2. New Railway project → **Deploy from GitHub repo**
3. Add env vars in the **Variables** tab (`ENVIRONMENT=production`, `APP_URL=https://your-app.up.railway.app`)
4. Deploy — Railway auto-detects the `Dockerfile`

---

## ✅ Production Checklist

- 🔒 JWT in `httponly` cookie — no secrets in `localStorage`
- 🛡️ All inputs validated before any AI call (length, type, MIME type)
- 📉 Rate limited per route — prevents abuse and runaway OpenAI costs
- 🚫 Error messages sanitised — stack traces never reach the client
- ⚡ Cache prevents duplicate AI calls on the same conversation
- 🐳 Non-root Docker user — container security best practice
- 📱 PWA-ready — installable on iOS and Android
- 🌙 Dark / light theme with zero flash on load

---

## 🗺️ Roadmap

- [ ] Shareable result cards — export as image
- [ ] Conversation tracking — score trend over time for the same person
- [ ] Relationship timeline — aggregate interest graph
- [ ] Native app wrapper (Capacitor)

---

<div align="center">

**MIT License** — build on it, learn from it, just don't use it to manipulate people.

*That's literally the whole point of building the opposite.*

</div>
