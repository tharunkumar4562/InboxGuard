# 🚀 Railway Configuration Guide

## ⚠️ CRITICAL: Required Environment Variables

### 1. SESSION PERSISTENCE (🔴 MOST IMPORTANT - FIXES "LOGIN REQUIRED AFTER EVERY DEPLOY")

```
INBOXGUARD_SESSION_SECRET = <super_long_random_string>
```

**What it does**: Locks your session secret so users stay logged in across deployments.

**Why it matters**:  
- Without this, users logout on every deploy
- The default value `"change-me-in-production"` changes = session invalid = forced logout
- This is the #1 cause of "I need to login again after every deployment"

**How to generate**:  
```bash
# Run in terminal once and keep the value
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy the output → paste in INBOXGUARD_SESSION_SECRET
```

**Set in Railway**: Variables → Add → `INBOXGUARD_SESSION_SECRET=<paste_value>`

---

### 2. SESSION SECURITY (Production HTTPS)

```
INBOXGUARD_SESSION_HTTPS_ONLY = 1
```

**What it does**: Forces secure cookies over HTTPS (required for production on Railway).

**Set in Railway**: Variables → Add → `INBOXGUARD_SESSION_HTTPS_ONLY=1`

---

### 3. RAZORPAY LIVE KEYS (Payment Provider)

```
INBOXGUARD_RAZORPAY_KEY = <your_razorpay_key_id>
INBOXGUARD_RAZORPAY_SECRET = <your_razorpay_secret>
INBOXGUARD_RAZORPAY_WEBHOOK_SECRET = <your_webhook_secret>
```

**How to get them**:
1. Login to Razorpay Dashboard
2. Settings → API Keys
3. Copy Key ID → paste as `INBOXGUARD_RAZORPAY_KEY`
4. Copy Secret Key → paste as `INBOXGUARD_RAZORPAY_SECRET`
5. Webhooks section → copy Webhook Secret → paste as `INBOXGUARD_RAZORPAY_WEBHOOK_SECRET`

---

### 4. RAZORPAY PLAN IDS (Subscriptions)

```
INBOXGUARD_RAZORPAY_PLAN_ID = plan_XXXXXXXX
INBOXGUARD_RAZORPAY_ANNUAL_PLAN_ID = plan_YYYYYYYY
```

**⚠️ CRITICAL**: Without these, "Get Access" button returns "subscription not configured"

**How to create plans**:
1. Razorpay Dashboard → Subscriptions → Plans
2. Create monthly plan (e.g., ₹999):
   - Period: Monthly
   - Amount: 1200 (in paise, = ₹12)
   - Copy Plan ID → paste as `INBOXGUARD_RAZORPAY_PLAN_ID`
3. Create annual plan (e.g., ₹9999):
   - Period: Annual
   - Amount: 99999 (in paise, = ₹99.99)
   - Copy Plan ID → paste as `INBOXGUARD_RAZORPAY_ANNUAL_PLAN_ID`

---

### 5. RAZORPAY PRICING DISPLAY

```
INBOXGUARD_RAZORPAY_AMOUNT_INR = 1200
INBOXGUARD_RAZORPAY_DISPLAY_PRICE_USD = $12
```

**Set in Railway**:
- `INBOXGUARD_RAZORPAY_AMOUNT_INR=1200` (amount in paise)
- `INBOXGUARD_RAZORPAY_DISPLAY_PRICE_USD=$12` (what users see)

---

### 6. GOOGLE OAUTH (Optional, but recommended for login)

```
INBOXGUARD_GOOGLE_OAUTH_ENABLED = 1
INBOXGUARD_GOOGLE_CLIENT_ID = <your_client_id>
INBOXGUARD_GOOGLE_CLIENT_SECRET = <your_secret>
```

**How to get them**:
1. Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (Web Application)
3. Authorized redirect URIs: `https://your-site.railway.app/auth/google/callback`
4. Download JSON → copy Client ID and Secret

---

### 7. SITE URL

```
INBOXGUARD_SITE_URL = https://your-domain.railway.app
```

**Set this to your actual Railway URL** (needed for OAuth redirects and links).

---

## ✅ COMPLETE CHECKLIST

Before deploying to production:

- [ ] `INBOXGUARD_SESSION_SECRET` = (generated 32-char string)
- [ ] `INBOXGUARD_SESSION_HTTPS_ONLY` = 1
- [ ] `INBOXGUARD_RAZORPAY_KEY` = (Razorpay Key ID)
- [ ] `INBOXGUARD_RAZORPAY_SECRET` = (Razorpay Secret)
- [ ] `INBOXGUARD_RAZORPAY_WEBHOOK_SECRET` = (Razorpay Webhook Secret)
- [ ] `INBOXGUARD_RAZORPAY_PLAN_ID` = (monthly plan ID from step 4)
- [ ] `INBOXGUARD_RAZORPAY_ANNUAL_PLAN_ID` = (annual plan ID from step 4)
- [ ] `INBOXGUARD_RAZORPAY_AMOUNT_INR` = 1200 (₹12 in paise)
- [ ] `INBOXGUARD_RAZORPAY_DISPLAY_PRICE_USD` = $12

## 🧪 TESTING THE FIX

1. **Session Test**: Login → deploy → refresh page → still logged in? ✅
2. **Payment Test**: Click "Get Access" → Razorpay checkout opens? ✅
3. **Webhook Test**: Complete a test payment → check logs for webhook event? ✅

## 🔧 DEBUGGING

**Session still breaks after deploy?**
- Check Railway logs: `Railway → [your-app] → Logs`
- Look for: `⚠️ SESSION_SECRET is using default value`
- If found → you missed setting `INBOXGUARD_SESSION_SECRET`

**"Subscription not configured" error?**
- Check logs for: `missing_config: ["RAZORPAY_KEY", "RAZORPAY_SECRET", "plan_id_for_monthly"]`
- If `plan_id_for_monthly` in list → you missed step 4 (Razorpay Plan IDs)

**Webhook not firing?**
- Check Razorpay Dashboard → Webhooks
- Ensure endpoint is: `https://your-domain.railway.app/webhook/razorpay`
- Verify secret matches `INBOXGUARD_RAZORPAY_WEBHOOK_SECRET`
