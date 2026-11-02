# KRISHIL Studio — Manager + 2 employees (₹0/month)

```
            YOU (phone)  ──upload photo/video + note──▶  📤 MANAGER
                                                         looks at it with AI, decides who gets it
                                                ┌───────────────┴───────────────┐
                                     own copy of brief                 own copy of brief
                                                ▼                               ▼
                                   📸 INSTAGRAM EMPLOYEE            💬 WHATSAPP EMPLOYEE
                                   rules/instagram_rules.json       rules/whatsapp_rules.json
                                   4:5 edit + caption + ≤5 tags     Gujarati+English message
                                   schedules 1–5 posts/day          morning education-news update
                                   POSTS AUTOMATICALLY              ready for 1-tap Share
```

**The wall:** each worker has its own rule book, its own folders and its own run.
`common/lanes.py` stops the run if any worker even tries to read or write the other's
files. Only the Instagram employee gets the Instagram password (token). They can never
mix up, and one failing never stops the other.

| Part | Free service used | Cost |
|---|---|---|
| Manager app (phone/PC) | GitHub Pages | ₹0 |
| Manager + employees running on a timer | GitHub Actions (public repo) | ₹0 |
| AI: understand photos, write captions | Google Gemini API free tier | ₹0 |
| Instagram posting | Instagram Graph API | ₹0 |
| WhatsApp | You share with 1 tap (no paid API, no ban risk) | ₹0 |

---

## Setup (one time, about 30–40 minutes)

### 1. GitHub
1. Make a free account at **github.com**.
2. Click **+ → New repository** → name it `krishil-studio` → choose **Public** → Create.
   *Public is needed for free unlimited runs and so Instagram can fetch the photo.
   Only put shop promo photos here — never customer documents.*
3. Click **uploading an existing file** and drag in **all** the files and folders from this zip
   (including the `.github` folder; on Mac press `Cmd+Shift+.` to see hidden folders) → **Commit**.
4. Go to the **Actions** tab → click **"I understand… enable them"**.

### 2. Free AI key (Gemini)
1. Open **aistudio.google.com** → sign in with Google → **Get API key → Create API key**. Copy it.
2. In your repo: **Settings → Secrets and variables → Actions → New repository secret**
   Name: `GEMINI_API_KEY`  Value: the key.

### 3. Instagram (the employee needs a key to post)
1. In the Instagram app: **Settings → Account type and tools → Switch to professional → Business**.
2. Go to **developers.facebook.com** → **My Apps → Create app** → pick the use case
   **"Manage messaging & content on Instagram"**.
3. In the app: **Instagram → API setup with Instagram login → Generate access tokens → Add account**
   → log in to `@krishil_edu_hub` → copy the **token** and the **Instagram user ID** shown there.
4. Add two more repo secrets: `IG_ACCESS_TOKEN` and `IG_USER_ID`.
   *(Tell me when you reach this step — I'll walk you through each screen.)*

### 4. Keep the Instagram key alive (optional but recommended)
Instagram keys expire after ~60 days. To renew it automatically every week:
GitHub → your photo → **Settings → Developer settings → Fine-grained tokens → Generate**
→ only this repo → permission **Secrets: Read and write** → copy → add as repo secret `GH_ADMIN_TOKEN`.

### 5. Turn on the Manager app
1. Repo **Settings → Pages** → Source: **Deploy from a branch** → Branch `main`, folder **/docs** → Save.
2. After ~1 minute your app is at `https://YOUR-USERNAME.github.io/krishil-studio/`.
   Open it on your phone → browser menu → **Add to Home screen**.
3. Make the app's key: **Fine-grained tokens → Generate** → only this repo → permissions
   **Contents: Read and write** and **Actions: Read and write** → copy.
4. In the app's **Settings** tab: your GitHub username, repo name, paste the token → **Save & test**.
   (The token stays only on your phone. Don't share it.)

### 6. Your logo
Upload a transparent PNG as `assets/logo.png` in the repo. Every edited post gets it in the corner.

### 7. WhatsApp
In WhatsApp Business: **Updates tab → Channels → + → Create channel** (e.g. "KRISHIL edu hub Updates").
Share the channel link with teachers, professors and trustees. Your normal group still works too.

---

## Daily use
1. **Upload tab** → add photos/videos → optional note ("New gel pens ₹10") → *Hand over to Manager*.
2. A few minutes later:
   - **Instagram tab → draft**: check the caption → ✅ **Approve**. It gets the next free time slot and
     posts by itself. (Turn on *Post automatically* in Settings once you trust it.)
   - **WhatsApp tab**: tap **📲 Share to WhatsApp** → pick your Channel / group → send → **Mark sent**.
3. Every morning before 7:30 AM a **🌅 education update** (GSEB, GTU, university news, in Gujarati
   with links) is waiting in the WhatsApp tab.

## Rules each employee follows
- **Instagram:** max 5 hashtags (Instagram's limit since Dec 2025), 1–5 posts/day in your time slots,
  2-hour gap, only prices from your rate card, mixes categories, never two posts in one run,
  never the same post twice.
- **WhatsApp:** max 1 promo message per day, short and respectful, Gujarati first, news only
  summarised in its own words with the link, never invents exam dates, no bots.
- **Manager:** holds back blurry photos and anything showing customer documents or personal details
  (you'll see them under *Held back*).
Change any rule in `rules/*.json` or in the app's Settings tab.

## Later: online selling
When you're ready, a third employee ("Shop") can be added the same way — its own lane, its own rules —
with a product page and UPI orders, linked from your Instagram bio. Nothing above needs to change.

## Testing
`python tests/test_offline.py` runs the whole flow without any keys and checks the walls between lanes.
