# Deploying the meal planner so friends can use it

This walks through hosting the app on **Fly.io's free tier**, with a
public HTTPS URL, a persistent database that survives restarts, and
auto-deploys on every push to `main`.

You'll do this once. After that, sharing changes is just `git push`.

## What you'll get

- A URL like `https://meal-planner.fly.dev` you can text to friends.
- The SQLite database lives on a 1 GB persistent volume — restarts and
  redeploys don't wipe it.
- Free tier: the app sleeps after ~15 min of no traffic; the next
  visitor waits 20–30 sec for it to wake up. Then it stays warm.
- 2–10 households fits easily inside the free allowance.

## Step 1 — One-time setup (needs a terminal)

You need a terminal **once** to create the Fly app and the storage
volume. After this, you can do everything from a phone via GitHub.

If you don't have a laptop handy, you can use **GitHub Codespaces**:
open the repo on github.com from your phone → green "Code" button →
"Codespaces" tab → "Create codespace". That gives you a terminal in
your browser.

In the terminal:

```bash
# 1. Install flyctl (Fly.io's CLI).
curl -L https://fly.io/install.sh | sh

# 2. Sign up / log in. Opens a browser tab the first time.
fly auth signup    # or `fly auth login` if you already have an account

# 3. From inside this repo, create the app.
#    Fly will read fly.toml, prompt for an app name (default: meal-planner —
#    pick something unique), and a region (default: iad = Virginia).
#    When it asks "Would you like to deploy now?" — say NO. We need to
#    create the storage volume first.
fly launch --copy-config --no-deploy

# 4. Create the persistent volume that holds the database.
#    Use the same region you picked above (replace iad if different).
fly volumes create meal_planner_data --size 1 --region iad

# 5. Deploy.
fly deploy

# 6. Open the live app.
fly open
```

That last command opens the URL in your browser. Copy it — that's what
you share with friends.

## Step 2 — Set up auto-deploy from GitHub (so you never need the terminal again)

After the first manual deploy works, set this up so future updates
deploy themselves:

```bash
# Generate a deploy token.
fly tokens create deploy
# Copy the long string it prints (starts with "FlyV1 ...").
```

Then on your phone:

1. Open `github.com/will-zzl-x/meal-planner` in any browser.
2. Settings → Secrets and variables → Actions → **New repository secret**.
3. Name: `FLY_API_TOKEN`. Value: paste the token from above. Save.

From now on, every time changes land on the `main` branch, GitHub
runs `.github/workflows/fly-deploy.yml`, which redeploys to Fly. You'll
see a green check (or red X) on the commit.

## Common operations

```bash
# See logs (helpful when something's wrong):
fly logs

# Restart the app (e.g. after a config change):
fly apps restart meal-planner

# Connect to the live SQLite DB (advanced — read-only safer):
fly ssh console
sqlite3 /data/meal_planner.db
```

## Backing up the database

The volume is durable, but it's still a single copy. To download a
backup of the live DB to your laptop:

```bash
fly ssh sftp get /data/meal_planner.db ./backup-$(date +%Y%m%d).db
```

Worth doing every few weeks, or before risky migrations.

## If something breaks

- **App won't start after deploy**: `fly logs` shows the crash. Most
  likely a missing dependency in `requirements.txt`.
- **Database wiped after deploy**: the volume isn't mounted. Check
  `fly volumes list` — should show `meal_planner_data` attached.
- **Cold start feels slow**: that's the free tier. Upgrade with
  `fly scale count 1` + paid plan to keep it always warm (~$5/month).
