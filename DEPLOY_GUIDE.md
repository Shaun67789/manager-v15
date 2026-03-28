# 🚀 Production Deployment Guide (Supabase + Render)

Follow these steps exactly to deploy your bot with permanent, non-wiped database storage!

---

### Step 1: Database Setup (Supabase)
1.  **Create Project:** Go to [Supabase.com](https://supabase.com) and create a new project. 
2.  **Run SQL Script:** 
    *   Open the **SQL Editor** tab on the left.
    *   **Open the file:** `supabase_setup.sql` from this bot's folder.
    *   **Copy & Paste** its entire contents into the SQL Editor and click **"Run"**.
3.  **Get Connection String (`DATABASE_URL`):**
    *   Go to **Project Settings** (Gear icon) -> **Database**.
    *   Find the **Connection String** section and click the **URI** tab.
    *   Copy it. (It looks like `postgresql://postgres.xxx:[PASSWORD]@aws-0-xxx.pooler.supabase.com:6543/postgres`).
    *   **VERY IMPORTANT:** Replace `[PASSWORD]` with the database password you chose when creating the Supabase project!

---

### Step 2: Render Deployment
1.  **Push Code:** Push all these files to your private GitHub repository.
2.  **Create Web Service:** 
    *   In [Render.com](https://render.com), click **"New" -> "Web Service"**.
    *   Select your bot repository.
    *   The **"Runtime"** should be Python 3.
    *   **"Build Command"**: `pip install -r requirements.txt`
    *   **"Start Command"**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
3.  **Add Configuration (Environment Variables):**
    Add these in the **"Environment"** tab of your Render service:
    *   `DATABASE_URL`: *(Your Supabase URI from Step 1)*
    *   `SUPABASE_URL`: *(Project Settings > API -> Project URL)*
    *   `SUPABASE_KEY`: *(Project Settings > API -> anon public key)*
    *   `BOT_TOKEN`: *(Your Telegram Bot Token)*
    *   `OWNER_USERNAME`: *(Your Username without @)*
    *   `BOT_AUTOSTART`: `true`

---

### Step 3: Test
1.  Once Render finished deploying ("Live" status), visit the generated URL.
2.  Start your bot on Telegram! 
3.  Add it to a group and use `/setwelcome Hello {name}!` 
4.  Even if Render restarts or sleeps, your settings are now **Safe & Permanent** in Supabase!

---
*Note: If you have already deployed, just adding the `DATABASE_URL` in the Render Environment Variables is enough to switch over.*
