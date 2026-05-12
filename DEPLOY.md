# Deploying the meal planner — phone-only, free forever

This guide gets the app live on **Streamlit Community Cloud** (hosts
the app) backed by a **Neon** database (holds the data). Both have
generous free-forever tiers — no credit card on file anywhere, no
"trial that ends in N days" gotcha.

You'll do it once. After that, every push to `main` (or to whichever
branch you tell Streamlit Cloud to track) redeploys the app
automatically — no clicks needed.

## What you'll get

- A URL like `https://meal-planner-yourname.streamlit.app` you can
  text to friends.
- The database is a separate Postgres instance on Neon; it survives
  every restart and redeploy.
- Free tier: app sleeps after about a week of total inactivity (rare
  for a friends-and-family meal planner). Neon's free DB pauses after
  5 min idle but wakes in ~1 second on the first query.

## Step 1 — Sign up at Neon (3 min)

Neon is a hosted Postgres service. We just need the *connection
string* — a single URL the app uses to talk to the database.

1. Open **https://neon.tech** in Safari and tap **Sign up**. Use
   GitHub login for the fastest path.
2. After signup, Neon creates a default project. If it asks you to
   name it, use whatever you like (e.g. "meal-planner").
3. From the project page, find **Connection Details** (usually a
   box on the dashboard, or under **Settings → Connection Details**).
4. Make sure the dropdown shows the **psql** or **Connection String**
   view, not just host/user separately.
5. Copy the full string. It looks like:
   ```
   postgresql://alex:abc123XYZ@ep-cool-name-1234.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   Save it in your Notes app for the next step.

That's it for Neon. The database is already running.

## Step 2 — Sign up at Streamlit Cloud (3 min)

Streamlit Cloud is a free service for hosting Streamlit apps directly
from GitHub.

1. Open **https://streamlit.io/cloud** in Safari and tap **Sign up**.
2. Sign in with GitHub. Grant access to the repos Streamlit can
   read — at minimum, your **meal-planner** repo.

## Step 3 — Create the app on Streamlit Cloud (2 min)

1. From Streamlit Cloud's main screen, tap **Create app** (or **New
   app**).
2. Fill in:
   - **Repository**: `will-zzl-x/meal-planner`
   - **Branch**: `main` (or whichever branch you want live).
   - **Main file path**: `src/web/app.py`
   - **App URL** (subdomain): pick something memorable — this becomes
     `https://<that>.streamlit.app`.
3. **Don't tap Deploy yet** — first add the database secret in the
   next step.

## Step 4 — Add the database secret (1 min)

1. On the create-app screen, expand **Advanced settings** (or
   **Secrets**, depending on UI version).
2. In the secrets box, paste exactly this (substituting your Neon
   string from Step 1):
   ```toml
   DATABASE_URL = "postgresql://alex:abc123XYZ@ep-cool-name-1234.us-east-2.aws.neon.tech/neondb?sslmode=require"
   ```
   Note the quotes around the URL. The format is TOML.
3. Save the secret.

## Step 5 — Deploy (~5 min, then you're done)

1. Tap **Deploy**.
2. Streamlit Cloud now: clones the repo, installs dependencies, runs
   `streamlit run src/web/app.py`. You'll see a build log scroll by.
3. The first deploy takes ~3-5 min. When it's done, you'll land on
   the live app. The very first request runs the database migrations
   (creating your tables on Neon) — give it 5-10 seconds extra on
   first load.
4. Copy the URL — that's what you share with friends.

## After the first deploy

Every git push to your tracked branch (default: `main`) automatically
redeploys. To make a change:

- Edit the code locally, commit, push to `main`.
- Streamlit Cloud picks it up within ~30 seconds and rebuilds.
- ~1 minute later your friends see the new version.

You can also force a redeploy from the Streamlit Cloud dashboard:
your app → **Manage app** → **Reboot**.

## If something breaks

The Streamlit Cloud dashboard shows logs for every deploy and at
runtime. The most common issues:

- **"could not connect to server" / "FATAL: password authentication
  failed"**: the `DATABASE_URL` secret has a typo. Re-copy from Neon
  and re-paste in Settings → Secrets.
- **"relation does not exist"**: migrations didn't run. Restart the
  app (Manage app → Reboot). The repo constructors auto-run
  migrations on first connection.
- **"module not found"**: a Python dependency missing from
  `requirements.txt`. Send me the error and I'll add it.

## Backing up the database (optional)

Neon's free tier includes point-in-time recovery for the last 24
hours by default. For longer-term snapshots, install `pg_dump` on any
laptop and run:

```bash
pg_dump "<your DATABASE_URL>" > backup-$(date +%Y%m%d).sql
```

Worth doing every few weeks. The file is plain text SQL — keep it
somewhere safe (cloud drive, email to yourself, etc).

## Costs

- **Neon free tier**: 0.5 GB storage, 1 project. Fits 2–10
  households for years.
- **Streamlit Cloud free**: 1 GB RAM per app, unlimited public apps.
  Plenty for this size.

Neither service charges anything unless you actively upgrade. There's
no card on file by default for either.
