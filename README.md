# KRISHIL Studio — Manager + 2 employees (₹0/month)

```
   YOU (phone app)  ──upload photo/video + note──▶  📤 MANAGER
                                                    looks at it with AI, decides who gets it
                                        ┌──────────────────┴──────────────────┐
                              own copy of the job                    own copy of the job
                                        ▼                                     ▼
                           📸 INSTAGRAM EMPLOYEE                  💬 WHATSAPP EMPLOYEE
                           rules/instagram_rules.json             rules/whatsapp_rules.json
                           4:5 edit + caption + ≤5 hashtags       Gujarati + English message
                           schedules 1–5 posts/day                morning education-news update
                           POSTS BY ITSELF (needs Instagram key)  you send with 1 tap (Share)
```

**The wall:** each employee has its own rule book, its own folders and its own run.
`common/lanes.py` stops a run if one employee even tries to read or write the other's files.
Only the Instagram employee ever gets the Instagram key. One failing never stops the other.

| Part | Free service | Cost |
|---|---|---|
| Manager app (phone/PC) | GitHub Pages | ₹0 |
| Manager + employees on a timer | GitHub Actions (public repo) | ₹0 |
| AI: understand photos, write captions | Google Gemini free tier | ₹0 |
| Instagram posting | Instagram API | ₹0 |
| WhatsApp | you tap Share (no paid API, no ban risk) | ₹0 |

---

## Setup checklist

| # | Step | Needed for | Status |
|---|---|---|---|
| 1 | Put the project on GitHub (public) | everything | ✅ done |
| 2 | Gemini AI key → secret `GEMINI_API_KEY` | captions, sorting | ✅ done |
| 3 | Turn on the app (GitHub Pages) | phone app | ✅ done |
| 4 | App key (fine-grained token) → app Settings | uploading from the app | ✅ done |
| 5 | Install update 1 (fix stuck uploads) | drafts appearing | ⬜ do now |
| 6 | Instagram key → secrets `IG_ACCESS_TOKEN`, `IG_USER_ID` | **auto-posting** | ⬜ next |
| 7 | Auto-renew key → secret `GH_ADMIN_TOKEN` | Instagram key not expiring | ⬜ after 6 |
| 8 | Logo → `assets/logo.png` | logo on every post | ⬜ optional |
| 9 | WhatsApp group / Channel | sending updates | ✅ group made |
| 10 | Phone alerts (ntfy app + secret `NTFY_TOPIC`) | morning news without copy-paste | ⬜ now |

**Without step 6** everything still works except the final posting: drafts are made,
you approve them, and they wait until the Instagram key is added.
**WhatsApp has no key to add** — it is ready as soon as step 5 is done.

---

### 1. GitHub (done)
- Repo: `github.com/krishil9316k/krishil-studio` — must say **Public**.
- Published from VS Code: open the folder that directly contains `common`, `docs`, `manager`…
  → **Ctrl+Shift+G → Publish to GitHub → public repository**.

### 2. Gemini AI key (done)
- **aistudio.google.com → Get API key → Create API key**.
- Repo **Settings → Secrets and variables → Actions → New repository secret** → `GEMINI_API_KEY`.

### 3. The app (done)
- Repo **Settings → Pages → Deploy from a branch → main → /docs → Save**.
- App: **https://krishil9316k.github.io/krishil-studio/** → on phone: Chrome ⋮ → **Add to Home screen**.

### 4. App key (done)
- **github.com/settings/personal-access-tokens/new**
- Name `krishil app` · Expiration **Custom, max 1 year ahead** (a later date makes the button freeze)
- **Only select repositories → krishil-studio** · Permissions **Contents** + **Actions** → **Read and write**
- If that page freezes: classic token at **github.com/settings/tokens/new** → tick only **repo**.
- In the app **⚙️ Settings**: username `krishil9316k`, repo `krishil-studio`, branch `main`, token → **Save & test**.
- Do the same once on your phone. The token stays only on that device. Never share it.

### 5. Install an update
1. VS Code → open the `krishil-studio` folder → **Ctrl+Shift+G → Sync Changes 🔄** (always first —
   the employees save their work to GitHub, so get their latest files before changing anything).
2. Copy the update's folders into the project folder → **Replace**.
3. Source Control → message → **✔ Commit → Sync Changes**.
4. App → **Upload** tab → **▶ Run Manager now** (photos already waiting are picked up).

### 6. Instagram key (for auto-posting)
**a. Make the account Professional (phone):** Instagram → Profile → ☰ → **Settings → Account type and tools →
Switch to professional account → Business** → category e.g. "Printing Service". Keep it **public**.

**b. Create the Meta app (computer):**
1. **developers.facebook.com** → log in → register as developer if asked.
2. **My Apps → Create App** → use case **Other** → **Next** → type **Business** → **Next**.
3. Name `KRISHIL Studio`, your email → **Create app**.
4. On the dashboard find **Instagram → Set up** ("API setup with Instagram login" is added).

**c. Get the key:**
1. Left menu **Instagram → API setup with Instagram login**.
2. **Generate access tokens → Add account** → log in to **@krishil_edu_hub** → allow everything.
3. If it sends a tester invite: Instagram app → Settings → **Website permissions → Apps and websites →
   Tester invites → Accept**, then repeat step 2.
4. Copy the **Instagram user ID** (number) and click **Generate token** → copy the token.
5. Repo secrets: `IG_USER_ID` = the number, `IG_ACCESS_TOKEN` = the token.

**d. Test:** app → Instagram tab → a draft → **Post next run** → within 30 min it appears on @krishil_edu_hub.

### 7. Keep the Instagram key alive
Instagram keys expire after ~60 days. Make one more fine-grained token (only this repo,
permission **Secrets → Read and write**, expiry ≤ 1 year) → repo secret `GH_ADMIN_TOKEN`.
The workflow "4 · Instagram token keep-alive" then renews the Instagram key every Monday.

### 8. Logo
Repo → `assets` folder → **Add file → Upload files** → a transparent PNG named exactly `logo.png`.

### 9. WhatsApp Channel
WhatsApp Business → **Updates → Channels + → Create channel** ("KRISHIL edu hub Updates") → share its link
with teachers, professors and trustees. Your normal groups work too.

### 10. Phone alerts for WhatsApp (no copy-paste)
1. Phone → Play Store → install **ntfy** (free, by Philipp Heckel).
2. Open ntfy → **+** → topic name: your secret topic (e.g. `krishil-edu-` + 8 random letters/numbers) → **Subscribe**.
3. GitHub repo → Settings → Secrets and variables → Actions → New secret: `NTFY_TOPIC` = the same topic name.
4. Every morning (~6:45–7:45) and whenever a photo message is ready, your phone buzzes.
   Tap **Send on WhatsApp** → WhatsApp opens with the message typed → pick your group → **Send**.
   No alerts after 9:30 PM. Keep the topic name secret — anyone who knows it can read the alerts.

---

## Daily use
1. **📤 Upload** → photos/videos → note (e.g. "New gel pens ₹10") → **Hand over to Manager**.
2. About 5–10 minutes later:
   - **📸 Instagram → draft** → check caption → **✅ Approve** → it takes the next time slot
     (08:30 / 13:00 / 19:30) and posts by itself. **Post next run** = within 30 min.
     Turn on *Post automatically* in Settings once you trust the captions.
   - **💬 WhatsApp** → **📲 Share to WhatsApp** → pick Channel/group → send → **✔ Mark sent**.
3. Every morning by 7:30 a **🌅 education update** (GSEB, GTU, university news) waits in the WhatsApp tab.

## Rules each employee follows
- **Instagram:** max 5 hashtags (Instagram limit), 1–5 posts/day in your slots, only rate-card prices,
  mixes categories, one post per run, never the same post twice.
- **WhatsApp:** max 1 promo per day, short and respectful, Gujarati first, news only summarised with
  the link, never invents exam dates, no bots.
- **Manager:** holds back blurry photos and anything showing customer documents or personal details.
- If the AI is busy, a simple caption is used (marked ℹ️ on the draft) — nothing gets stuck.
Change rules in the app's **⚙️ Settings** or in `rules/*.json`.

## If something goes wrong
| What you see | Fix |
|---|---|
| App: "Could not connect" | check username, repo name, token (Contents + Actions: Read and write) |
| Nothing in Instagram/WhatsApp tabs | Upload tab → Manager box shows waiting count + red error → **▶ Run Manager now** |
| "AI not working" in red | check the `GEMINI_API_KEY` secret; drafts still come with simple captions |
| Instagram tab: "Instagram not connected yet" | step 6 not done, or secret names misspelled |
| Instagram error about token/permission | redo step 6c and update `IG_ACCESS_TOKEN` |
| Any ❌ in the repo's **Actions** tab | click it → screenshot the red step → send to Claude |

## Later: online selling
A third employee ("Shop") can be added the same way — its own lane and rules — with a product page
and UPI orders, linked from your Instagram bio. Nothing above needs to change.

## Testing
`python tests/test_offline.py` runs the whole flow without any keys and checks the walls between lanes.
