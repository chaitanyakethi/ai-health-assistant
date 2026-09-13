# 🚀 Deploy AI Health Assistance (free, ~5 minutes)

## Option A — Streamlit Community Cloud (RECOMMENDED for tomorrow)

Free, public link, judges can open it on their phones.

1. **Go to** → https://share.streamlit.io
2. **Sign up / Sign in** → choose **"Continue with Google"** → use your GitHub-linked Google account (or sign in with GitHub directly)
3. Click **"Create app"** (or "New app")
4. **"Deploy a public app from GitHub"** — fill in:
   - **Repository:** `chaitanyakethi/ai-health-assistant`
   - **Branch:** `main`
   - **Main file path:** `prototype/app.py`
   - **App URL:** pick something like `ai-health-assistant`
5. Click **"Deploy!"**
6. Wait ~3–5 minutes (first build installs Streamlit, Plotly, pypdf…)
7. 🎉 Your live link: `https://chaitanyakethi-ai-health-assistant.streamlit.app`

**Important notes:**
- The alarm sound now works on the cloud (absolute path fix, pushed).
- Accounts created on the cloud are stored on Streamlit's server (fresh users.json there) — create your `chaitanya` account once after it deploys.
- The `?google=1` demo sign-in works the same on the cloud link.
- If the build fails, check the "Manage app" → logs; the usual cause is a missing package — everything needed is already in `prototype/requirements.txt`.

## Option A2 — Render (free, in addition to Streamlit Cloud)

Render's free tier hosts one Streamlit service — public link, HTTPS, no credit card. The repo already contains a **`render.yaml`** blueprint, so Render auto-fills everything.

### Deploy steps (≈5 minutes)

1. **Go to** → https://dashboard.render.com → **Sign up with GitHub** (recommended, it links your repo access automatically)
2. Click **"New +"** → choose **"Blueprint"**
3. Select repository: `chaitanyakethi/ai-health-assistant` → click **"Connect"**
4. Render reads `render.yaml` and shows the service pre-filled — click **"Apply"** (nothing to type)
5. First build takes ~5 minutes (installs streamlit, plotly, pypdf, fpdf2, streamlit-autorefresh)
6. 🎉 Your live link appears on the service page, like: `https://ai-health-assistant-xxxx.onrender.com`

### If you prefer manual setup (no blueprint)

New + → **Web Service** → connect repo, then:

| Field | Value |
|---|---|
| Root Directory | `prototype` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true` |
| Instance Type | Free |

Leave every other field default (Render injects `$PORT` automatically).

### Render free-tier caveats

- **Sleeps after 15 min idle** — first visitor after a nap waits ~30–60 s while it spins up. Before the demo, open the link once yourself to wake it.

- **accounts (users.json) live on the server disk** — create your `chaitanya` account once after deploying; a redeploy or restart wipes it (re-creating takes 10 seconds).
- **Manual deploy trigger**: after pushing new commits, Render auto-deploys on push. To force it: service page → **Manual Deploy** → *Deploy latest commit*.

## Option B — Run locally on stage (most reliable)

No internet dependency at the expo:

```cmd
cd C:\05D0\mini project\prototype
.venv\Scripts\activate
streamlit run app.py --server.address 0.0.0.0
```

- Laptop screen: http://localhost:8501
- Phone on same Wi-Fi: http://192.168.0.192:8501

**Tip:** do BOTH — present from your laptop, but give judges the cloud link as "scan to try it yourself."

## Option C — Expo mobile app (optional, later)

```cmd
cd "C:\05D0\mini project"
npm start
```
Scan the QR with the **Expo Go** app (phone + laptop on same Wi-Fi). Publishing to app stores needs an Expo/EAS account and is not needed for the demo.

---

## ⚠️ Cloud caveats to mention if asked

| Topic | Answer |
|---|---|
| Data on cloud | Demo state lives in each visitor's browser session; accounts go to the server's users.json — fine for a demo, production would use a real DB (see architecture doc) |
| Alarm sound | Browsers allow audio after the user interacts with the page once (judge clicks anything first — normally already true) |
| Offline demo | Use Option B locally if venue Wi-Fi is bad — rehearse both |

## 📋 Pre-deploy checklist
- [x] Alarm sound path fixed for cloud (`806526d`)
- [x] requirements.txt has all packages (streamlit, plotly, pypdf, fpdf2, streamlit-autorefresh)
- [x] Code pushed to `main` on GitHub
- [ ] Deploy on Streamlit Cloud, create your account, run the 45-second demo flow once
- [ ] Bookmark the cloud link on your phone
