import psycopg2
import psycopg2.extras
import os
import json
import threading
from datetime import datetime

class Database:
    def __init__(self):
        self.db_url = os.environ.get("DATABASE_URL")
        self.sb_url = os.environ.get("SUPABASE_URL")
        self.sb_key = os.environ.get("SUPABASE_KEY")
        self.lock = threading.Lock()
        
        if not self.db_url:
            print("WARNING: DATABASE_URL not set! Database functions will fail.")
            return
            
        self.conn = psycopg2.connect(self.db_url, cursor_factory=psycopg2.extras.RealDictCursor)
        self.conn.autocommit = True
        self._init_db()
        self._migrate_db()

    def _init_db(self):
        # We don't actually need init_db since Supabase UI covers schema, but we can leave it for safety!
        pass

    def _migrate_db(self):
        pass
        
    def get_config(self):
        if not hasattr(self, 'conn'): return {}
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("SELECT key, value FROM config")
                conf = {
                    "bot_token": "",
                    "is_running": False,
                    "owner_username": "",
                    "support_channel": ""
                }
                for row in c.fetchall():
                    try:
                        conf[row['key']] = json.loads(row['value'])
                    except json.JSONDecodeError:
                        conf[row['key']] = row['value']

                env_token   = os.environ.get("BOT_TOKEN", "").strip()
                env_owner   = os.environ.get("OWNER_USERNAME", "").strip()
                env_running = os.environ.get("BOT_AUTOSTART", "").strip().lower()
                env_support = os.environ.get("SUPPORT_CHANNEL", "").strip()

                if env_token: conf["bot_token"] = env_token
                if env_owner: conf["owner_username"] = env_owner.replace("@", "")
                if env_running in ("1", "true", "yes"): conf["is_running"] = True
                if env_support: conf["support_channel"] = env_support.replace("@", "")

                return conf

    def update_config(self, key, value):
        if not hasattr(self, 'conn'): return
        with self.lock:
            with self.conn.cursor() as c:
                c.execute(
                    "INSERT INTO config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                    (key, json.dumps(value))
                )

    def ensure_group(self, chat_id, name=None):
        if not hasattr(self, 'conn'): return
        str_id = str(chat_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute(
                    "INSERT INTO groups (chat_id, name, max_warnings, strict_mode, language, log_channel_id) VALUES (%s, %s, 3, false, 'en', NULL) ON CONFLICT (chat_id) DO NOTHING",
                    (str_id, name or 'Unknown Group')
                )
                if name:
                    c.execute(
                        "UPDATE groups SET name=%s WHERE chat_id=%s AND (name IS NULL OR name='Unknown Group')",
                        (name, str_id)
                    )

    def get_group(self, chat_id):
        if not hasattr(self, 'conn'): return {}
        self.ensure_group(chat_id)
        str_id = str(chat_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("SELECT * FROM groups WHERE chat_id=%s", (str_id,))
                row = c.fetchone()
                if not row:
                    return {}
                group = dict(row)
                
                # Filters
                c.execute("SELECT trigger, filter_data FROM filters WHERE chat_id=%s", (str_id,))
                group["filters"] = {r['trigger']: json.loads(r['filter_data']) for r in c.fetchall()}

                # Bad Words
                c.execute("SELECT word FROM bad_words WHERE chat_id=%s", (str_id,))
                group["bad_words"] = [r['word'] for r in c.fetchall()]

                return group

    def update_group_setting(self, chat_id, key, value):
        if not hasattr(self, 'conn'): return
        self.ensure_group(chat_id)
        str_id = str(chat_id)
        with self.lock:
            with self.conn.cursor() as c:
                if key == "bad_words":
                    c.execute("DELETE FROM bad_words WHERE chat_id=%s", (str_id,))
                    for w in value:
                        c.execute("INSERT INTO bad_words (chat_id, word) VALUES (%s, %s) ON CONFLICT DO NOTHING", (str_id, w.lower()))
                else:
                    valid_keys = {"antispam", "rules", "name", "welcome_message", "welcome_type", "welcome_file_id", "leave_message", "leave_type", "leave_file_id", "strict_mode", "max_warnings", "language"}
                    if key in valid_keys:
                        c.execute(f"UPDATE groups SET {key}=%s WHERE chat_id=%s", (value, str_id))

    def add_filter(self, chat_id, trigger, filter_data):
        if not hasattr(self, 'conn'): return
        self.ensure_group(chat_id)
        str_id = str(chat_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute(
                    "INSERT INTO filters (chat_id, trigger, filter_data) VALUES (%s, %s, %s) ON CONFLICT (chat_id, trigger) DO UPDATE SET filter_data = EXCLUDED.filter_data",
                    (str_id, trigger.lower(), json.dumps(filter_data))
                )

    def remove_filter(self, chat_id, trigger):
        if not hasattr(self, 'conn'): return
        self.ensure_group(chat_id)
        str_id = str(chat_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("DELETE FROM filters WHERE chat_id=%s AND trigger=%s", (str_id, trigger.lower()))

    def get_user_info(self, user_id):
        if not hasattr(self, 'conn'): return {}
        str_id = str(user_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("SELECT name, username, reputation, is_banned, banned_reason, warnings FROM users WHERE user_id=%s", (str_id,))
                row = c.fetchone()
                if not row:
                    return {"name": "Unknown", "username": None, "reputation": 0, "is_banned": False}
                return dict(row)

    def ensure_user(self, user_id, name="Unknown", username=None, role="member"):
        if not hasattr(self, 'conn'): return
        str_id = str(user_id)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            with self.conn.cursor() as c:
                c.execute(
                    "INSERT INTO users (user_id, name, username, role, first_seen, last_active) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET name=EXCLUDED.name, username=EXCLUDED.username, last_active=EXCLUDED.last_active",
                    (str_id, name or "Unknown", username or None, role, now, now)
                )

    def add_message_count(self, chat_id):
        if not hasattr(self, 'conn'): return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            with self.conn.cursor() as c:
                c.execute(
                    "UPDATE groups SET message_count = message_count + 1, last_active = %s WHERE chat_id=%s",
                    (now, str(chat_id))
                )

    def get_extra_group_info(self):
        if not hasattr(self, 'conn'): return {}
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("SELECT chat_id, name, message_count, member_count, last_active, antispam, strict_mode, max_warnings FROM groups")
                return {row['chat_id']: dict(row) for row in c.fetchall()}

    def get_user(self, user_id):
        if not hasattr(self, 'conn'): return {}
        str_id = str(user_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("SELECT * FROM users WHERE user_id=%s", (str_id,))
                row = c.fetchone()
                return dict(row) if row else {}

    def add_warning(self, user_id, name="Unknown"):
        if not hasattr(self, 'conn'): return 0
        self.ensure_user(user_id, name)
        str_id = str(user_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("UPDATE users SET warnings = warnings + 1 WHERE user_id=%s RETURNING warnings", (str_id,))
                row = c.fetchone()
                return row['warnings'] if row else 0

    def reset_warnings(self, user_id):
        if not hasattr(self, 'conn'): return
        str_id = str(user_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("UPDATE users SET warnings = 0 WHERE user_id=%s", (str_id,))

    def get_all_stats(self):
        base = {
            "total_users": 0, "total_groups": 0, "total_messages": 0,
            "total_logs": 0, "total_filters": 0, "total_bad_words": 0,
            "total_warned_users": 0
        }
        if not hasattr(self, 'conn'): return base
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("SELECT COUNT(*) as cu FROM users")
                base['total_users'] = c.fetchone()['cu']
                c.execute("SELECT COUNT(*) as cg FROM groups")
                base['total_groups'] = c.fetchone()['cg']
                c.execute("SELECT SUM(message_count) as cm FROM groups")
                row = c.fetchone()
                base['total_messages'] = row['cm'] if row['cm'] else 0
                c.execute("SELECT COUNT(*) as cl FROM logs")
                base['total_logs'] = c.fetchone()['cl']
                c.execute("SELECT COUNT(*) as cf FROM filters")
                base['total_filters'] = c.fetchone()['cf']
                c.execute("SELECT COUNT(*) as cb FROM bad_words")
                base['total_bad_words'] = c.fetchone()['cb']
                c.execute("SELECT COUNT(*) as cw FROM users WHERE warnings > 0")
                base['total_warned_users'] = c.fetchone()['cw']
                return base

    def get_all_users(self):
        if not hasattr(self, 'conn'): return {}
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("SELECT * FROM users ORDER BY first_seen DESC")
                return {row['user_id']: dict(row) for row in c.fetchall()}

    def get_all_groups(self):
        if not hasattr(self, 'conn'): return {}
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("""
                    SELECT g.chat_id, g.name, g.message_count, g.member_count,
                           g.last_active, g.antispam, g.welcome_message, g.welcome_type, g.welcome_file_id,
                           g.leave_message, g.leave_type, g.leave_file_id, g.strict_mode, g.max_warnings,
                           (SELECT COUNT(*) FROM filters WHERE chat_id = g.chat_id) as filter_count,
                           (SELECT COUNT(*) FROM bad_words WHERE chat_id = g.chat_id) as bad_words_count
                    FROM groups g
                    ORDER BY g.last_active DESC
                """)
                return {row['chat_id']: dict(row) for row in c.fetchall()}

    def search_items(self, query):
        if not hasattr(self, 'conn'): return {}, {}
        with self.lock:
            with self.conn.cursor() as c:
                q = f"%{query}%"
                c.execute(
                    "SELECT user_id, name, username, warnings, first_seen, reputation, is_banned FROM users WHERE user_id LIKE %s OR name ILIKE %s OR username ILIKE %s",
                    (q, q, q)
                )
                users = {row['user_id']: dict(row) for row in c.fetchall()}
                c.execute(
                    "SELECT chat_id, name, message_count, member_count, antispam, strict_mode FROM groups WHERE chat_id LIKE %s OR name ILIKE %s",
                    (q, q)
                )
                groups = {row['chat_id']: dict(row) for row in c.fetchall()}
                return users, groups

    def get_warnings_leaderboard(self, limit=10):
        if not hasattr(self, 'conn'): return []
        with self.lock:
            with self.conn.cursor() as c:
                c.execute(
                    "SELECT user_id, name, warnings FROM users WHERE warnings > 0 ORDER BY warnings DESC LIMIT %s",
                    (limit,)
                )
                return [dict(row) for row in c.fetchall()]

    def log_event(self, event):
        if not hasattr(self, 'conn'): return
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("INSERT INTO logs (event) VALUES (%s)", (str(event),))

    def get_recent_logs(self, limit=30):
        if not hasattr(self, 'conn'): return []
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("SELECT event, timestamp FROM logs ORDER BY id DESC LIMIT %s", (limit,))
                return [dict(row) for row in c.fetchall()]

    def delete_user(self, user_id):
        if not hasattr(self, 'conn'): return
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("DELETE FROM users WHERE user_id=%s", (str(user_id),))

    def delete_group(self, chat_id):
        if not hasattr(self, 'conn'): return
        str_id = str(chat_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("DELETE FROM groups WHERE chat_id=%s", (str_id,))
                c.execute("DELETE FROM filters WHERE chat_id=%s", (str_id,))
                c.execute("DELETE FROM bad_words WHERE chat_id=%s", (str_id,))

    def clear_logs(self):
        if not hasattr(self, 'conn'): return
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("DELETE FROM logs")

    def global_ban_user(self, user_id, reason="Admin banned", banner="System"):
        if not hasattr(self, 'conn'): return
        str_id = str(user_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("UPDATE users SET is_banned=TRUE, banned_reason=%s WHERE user_id=%s", (reason, str_id))
                c.execute(
                    "INSERT INTO global_bans (user_id, reason, banned_by) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET reason=EXCLUDED.reason",
                    (str_id, reason, banner)
                )

    def global_unban_user(self, user_id):
        if not hasattr(self, 'conn'): return
        str_id = str(user_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("UPDATE users SET is_banned=FALSE, banned_reason=NULL WHERE user_id=%s", (str_id,))
                c.execute("DELETE FROM global_bans WHERE user_id=%s", (str_id,))

    def get_global_bans(self):
        if not hasattr(self, 'conn'): return []
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("SELECT * FROM global_bans ORDER BY banned_at DESC")
                return [dict(r) for r in c.fetchall()]

    def update_reputation(self, user_id, amount):
        if not hasattr(self, 'conn'): return 0
        str_id = str(user_id)
        with self.lock:
            with self.conn.cursor() as c:
                c.execute("UPDATE users SET reputation = reputation + %s WHERE user_id=%s RETURNING reputation", (amount, str_id))
                row = c.fetchone()
                return row['reputation'] if row else 0

    def replace_database(self, raw_data):
        return False

db = Database()
