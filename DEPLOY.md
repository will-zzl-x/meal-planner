# Deploying the meal planner — phone-only walkthrough

This deploys the app to **Fly.io's free tier** without ever opening a
terminal. You'll do everything from your phone in Safari/Chrome.

You'll do it once. After that, every time changes land in the repo,
GitHub redeploys the app automatically.

## What you'll get

- A URL like `https://meal-planner-zzlx.fly.dev` you can text to friends.
- The database lives on a 1 GB persistent disk that survives restarts
  and redeploys.
- Free tier: the app sleeps after ~15 min of no traffic; the next
  visitor waits 20–30 sec for it to wake up. Then it stays warm.
- 2–10 households fits comfortably inside the free allowance.

## Step 1 — Sign up at Fly.io (5 min)

1. Open **https://fly.io** in Safari and tap **Get Started**.
2. Sign up (email + password, or use GitHub login).
3. Fly asks for a credit card. **They don't charge you unless you
   exceed the free tier** — the card is just to prevent abuse. The app
   at our scale stays well inside free.

## Step 2 — Generate a deploy token (2 min)

A *deploy token* is a long secret string that lets GitHub deploy on
your behalf. Think of it as a password just for deployments.

1. In the Fly dashboard, tap your **avatar (top right) → Account
   Settings → Access Tokens**.
2. Tap **Create access token**. Name it anything (e.g. "github
   deploy").
3. Copy the token that appears — it starts with `FlyV1`. **It's only
   shown once**, so copy it somewhere safe (your Notes app is fine,
   delete it after step 3).

## Step 3 — Add the token to GitHub (2 min)

1. In Safari, open `https://github.com/will-zzl-x/meal-planner`.
2. Tap **Settings** → in the left sidebar, **Secrets and variables →
   Actions**.
3. Tap **New repository secret**.
4. Name: `FLY_API_TOKEN` (exactly that, all caps).
5. Secret: paste the token from Step 2.
6. Tap **Add secret**.

You can now delete the token from your Notes app — GitHub has it.

## Step 4 — Run the deploy (3 min, then ~5 min waiting)

1. Still on GitHub, tap the **Actions** tab at the top of the repo.
2. In the left sidebar, tap **Deploy to Fly.io**.
3. Tap the **Run workflow** dropdown on the right. Pick the branch you
   want to deploy (probably `claude/review-recent-changes-...` for the
   first time, or `main` later). Tap **Run workflow**.
4. Refresh the page after a few seconds. A new run appears at the top
   — tap into it to watch progress. The "Deploy app" job has steps
   like *Create Fly app*, *Create volume*, *Deploy*. They run top to
   bottom.
5. When all steps go green (~5 min total), the last step prints the
   URL. Open it in Safari — that's your live app.

## After the first deploy

Every push to `main` (or to any working branch starting with
`claude/`) automatically redeploys. You can also re-trigger manually
from the Actions tab any time.

## If a step fails

The Actions UI will show a red X on whichever step broke. Tap it to
see the error message. Most common ones:

- **"Name has already been taken"** in *Create Fly app*: the app name
  `meal-planner-zzlx` is in use by someone else on Fly. Tell me and
  I'll change it to something unique.
- **"FLY_API_TOKEN was empty"**: the secret wasn't set in Step 3.
  Re-do that step, then re-run the workflow from the Actions tab.
- **Build error in *Deploy* step**: a Python dependency issue. Copy
  the error and tell me — I'll fix the Dockerfile or requirements.

## Backing up the database (optional, do this every few weeks)

This needs a brief terminal session (a friend's laptop or a one-time
Codespace). One command downloads a snapshot of the live DB:

```bash
fly ssh sftp get /data/meal_planner.db ./backup-$(date +%Y%m%d).db -a meal-planner-zzlx
```

Email yourself the file. Done.

## Upgrading off the free tier (only if cold starts get annoying)

If you outgrow free, change the `min_machines_running` line in
`fly.toml` from `0` to `1`. That keeps the app always-on (~$5/month).
