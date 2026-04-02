# Deploying MedPort Dashboard to Streamlit Community Cloud

Step-by-step for the team. Takes about 20 minutes first time.

---

## Prerequisites

- GitHub repo with `medport_dashboard.py` and `requirements.txt` pushed
- Supabase project already running (you have this)
- A Google account to create OAuth credentials

---

## Step 1 — Google OAuth credentials (10 min)

1. Go to https://console.cloud.google.com
2. Create a new project: `medport-dashboard` (or use existing)
3. **APIs & Services → OAuth consent screen**
   - User type: **External**
   - App name: `MedPort Dashboard`
   - Support email: your Gmail
   - Add your team emails under **Test users** (required while app is in testing mode)
   - Save and continue (skip optional fields)
4. **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Name: `Streamlit Dashboard`
   - Authorised redirect URIs: `https://medport-prospects.streamlit.app/oauth2callback`
     _(replace `medport-prospects` with whatever slug you pick in Step 2)_
   - Click Create → copy the **Client ID** and **Client Secret**

---

## Step 2 — Deploy on Streamlit Community Cloud (5 min)

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. **New app** → select your repo → branch: `main` → main file: `medport_dashboard.py`
4. Pick a URL slug (e.g. `medport-prospects`) → Deploy

---

## Step 3 — Add secrets in Streamlit Cloud (5 min)

In the app dashboard → **Settings → Secrets**, paste this (fill in real values):

```toml
SUPABASE_URL = "https://tzvmdwjhzebgqxorkjms.supabase.co"
SUPABASE_ANON_KEY = "your_anon_key_here"
GROQ_API_KEY = "your_groq_key_here"

# Comma-separated list of emails allowed to log in
ALLOWED_EMAILS = "arav@medport.ca,teammate2@gmail.com,teammate3@gmail.com"

[auth]
redirect_uri = "https://medport-prospects.streamlit.app/oauth2callback"
cookie_secret = "paste-output-of-command-below"

[[auth.providers]]
name = "google"
client_id = "your-client-id.apps.googleusercontent.com"
client_secret = "your-client-secret"
```

To generate `cookie_secret`, run in terminal:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Save → the app will reboot automatically.

---

## Step 4 — Test login

Open the URL. You should see the Google sign-in button. Sign in with a team email. If it works, share the URL with the rest of the team.

If you get "Access denied" even with a valid email, check that the email is spelled correctly in `ALLOWED_EMAILS`.

---

## Local development (no auth)

```bash
LOCAL_DEV=true streamlit run medport_dashboard.py
```

The `LOCAL_DEV=true` flag bypasses Google auth entirely.

---

## Adding a new team member

1. Add their email to `ALLOWED_EMAILS` in Streamlit Cloud secrets
2. If the Google OAuth app is still in **Testing** mode, also add them under
   Google Cloud Console → OAuth consent screen → Test users
3. That's it — no code change needed

---

## Troubleshooting

| Error                           | Fix                                                                                                                 |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `redirect_uri_mismatch`         | The redirect URI in Google Cloud must exactly match the one in secrets, including `https://` and `/oauth2callback`  |
| `StreamlitSecretNotFoundError`  | You're running locally without `LOCAL_DEV=true` and without a `.streamlit/secrets.toml` file. Set `LOCAL_DEV=true`. |
| `Access denied` after login     | Email not in `ALLOWED_EMAILS`. Add it in Streamlit Cloud secrets.                                                   |
| App shows CSV data not Supabase | `SUPABASE_URL` or `SUPABASE_ANON_KEY` is wrong. Check the secrets.                                                  |
