import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
import time

# ── CONFIG ──────────────────────────────────────────────────────────────────
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="💪 Gym Tracker", layout="wide", initial_sidebar_state="collapsed")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { max-width: 100%; }
    .stButton>button { border-radius: 12px; font-weight: 600; transition: all 0.2s; }
    [data-testid="metric-container"] {
        background: #1e2130; border-radius: 12px;
        padding: 12px; border: 1px solid #2e3250;
    }
    .timer-box {
        background: #0e1117; border: 2px solid #FF4B4B;
        border-radius: 12px; padding: 16px;
        text-align: center; font-size: 32px;
        font-weight: 700; color: #FF4B4B;
    }
    .day-banner {
        background: linear-gradient(135deg, #FF4B4B, #FF8C00);
        border-radius: 12px; padding: 16px;
        text-align: center; color: white;
        font-size: 20px; font-weight: 700;
        margin-bottom: 16px;
    }
    .rest-banner {
        background: linear-gradient(135deg, #2196F3, #00BCD4);
        border-radius: 12px; padding: 16px;
        text-align: center; color: white;
        font-size: 20px; font-weight: 700;
        margin-bottom: 16px;
    }
    @media (max-width: 768px) {
        .stSidebar { width: 80% !important; }
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ── 6-DAY WORKOUT PLAN ───────────────────────────────────────────────────────
WORKOUT_PLAN = {
    "Day 1 - Chest + Triceps": [
        "Bench Press", "Incline Dumbbell Press", "Machine Chest Press",
        "Cable Fly", "Tricep Pushdown", "Overhead Extension", "Dips"
    ],
    "Day 2 - Back + Biceps": [
        "Deadlift", "Lat Pulldown", "Seated Cable Row",
        "Single-arm DB Row", "Barbell Curl", "Hammer Curl", "Preacher Curl"
    ],
    "Day 3 - Legs": [
        "Squats", "Leg Press", "Romanian Deadlift",
        "Lunges", "Leg Curl", "Leg Extension", "Standing Calf Raises"
    ],
    "Day 4 - Shoulders": [
        "Military Press", "DB Shoulder Press", "Lateral Raises",
        "Front Raises", "Rear Delt Fly", "Shrugs"
    ],
    "Day 5 - Upper Body": [
        "Incline Bench Press", "Pull-ups", "Dumbbell Row",
        "Chest Fly", "Biceps Curl", "Skull Crushers"
    ],
    "Day 6 - Biceps + Triceps + Abs": [
        "Barbell Curl", "Incline Curl", "Cable Curl",
        "Rope Pushdown", "Overhead Rope Extension", "Close Grip Bench",
        "Hanging Leg Raises", "Cable Crunch", "Plank"
    ],
    "Custom": []
}

# Auto day detection — Monday=0 ... Sunday=6
DAY_MAP = {
    0: "Day 1 - Chest + Triceps",
    1: "Day 2 - Back + Biceps",
    2: "Day 3 - Legs",
    3: "Day 4 - Shoulders",
    4: "Day 5 - Upper Body",
    5: "Day 6 - Biceps + Triceps + Abs",
    6: None   # Sunday = Rest Day
}

DAY_NAMES = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday",
    3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
}

MOODS = ["💪 Great", "🔥 On Fire", "😐 Average", "😴 Tired", "😤 Pushed Through"]

# ── SESSION STATE ────────────────────────────────────────────────────────────
for key in ["user", "token", "timer_start", "timer_running", "rest_duration"]:
    if key not in st.session_state:
        st.session_state[key] = None
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False

# ── AUTH ─────────────────────────────────────────────────────────────────────
def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        st.session_state.token = res.session.access_token
        return True, "Login successful!"
    except Exception as e:
        return False, str(e)

def register(email, password):
    try:
        supabase.auth.sign_up({"email": email, "password": password})
        return True, "Registered! You can now login."
    except Exception as e:
        return False, str(e)

def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.token = None

def get_client():
    if st.session_state.token:
        supabase.auth.set_session(st.session_state.token, st.session_state.token)
    return supabase

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_streak(client, user_id):
    try:
        res = client.table("workouts").select("date").eq("user_id", user_id).order("date", desc=True).execute()
        if not res.data:
            return 0
        dates = sorted(set(r["date"] for r in res.data), reverse=True)
        streak = 0
        today = date.today()
        for i, d in enumerate(dates):
            d = date.fromisoformat(d)
            if d == today - timedelta(days=i):
                streak += 1
            else:
                break
        return streak
    except:
        return 0

def get_pr(client, user_id, exercise):
    try:
        res = client.table("workouts").select("weight_kg,reps,date")\
            .eq("user_id", user_id).eq("exercise_name", exercise)\
            .order("weight_kg", desc=True).limit(1).execute()
        return res.data[0] if res.data else None
    except:
        return None

# ── LOGIN PAGE ────────────────────────────────────────────────────────────────
def show_login():
    st.markdown("<h1 style='text-align:center'>💪 Gym Tracker</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#888'>Track your workouts. Crush your goals.</p>", unsafe_allow_html=True)
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", use_container_width=True, type="primary"):
                ok, msg = login(email, password)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        with tab2:
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password (min 6 chars)", type="password", key="reg_pass")
            if st.button("Register", use_container_width=True):
                ok, msg = register(email, password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

# ── MAIN APP ──────────────────────────────────────────────────────────────────
def show_app():
    client = get_client()
    user_id = st.session_state.user.id

    # Sidebar
    with st.sidebar:
        st.markdown("### 💪 Gym Tracker")
        st.markdown(f"👤 `{st.session_state.user.email}`")
        streak = get_streak(client, user_id)
        st.markdown(f"🔥 **Streak: {streak} days**")
        st.divider()
        page = st.radio("Navigate", [
            "📝 Log Workout",
            "📊 My History",
            "📈 Performance",
            "🏆 Personal Records",
            "⚖️ Body Weight",
            "📅 Weekly Summary",
            "🔢 1RM Calculator"
        ])
        st.divider()
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1: LOG WORKOUT
    # ══════════════════════════════════════════════════════════════════════════
    if page == "📝 Log Workout":
        st.title("📝 Log Workout")

        # Auto detect today's day
        today_weekday = date.today().weekday()
        auto_day = DAY_MAP.get(today_weekday)
        today_name = DAY_NAMES.get(today_weekday)

        if auto_day:
            st.markdown(f"""
            <div class='day-banner'>
                📅 Today is {today_name} — {auto_day}
            </div>
            """, unsafe_allow_html=True)
            default_idx = list(WORKOUT_PLAN.keys()).index(auto_day)
        else:
            st.markdown(f"""
            <div class='rest-banner'>
                😴 Today is {today_name} — REST DAY! Recovery is key 💤
            </div>
            """, unsafe_allow_html=True)
            default_idx = len(WORKOUT_PLAN) - 1

        day_plan = st.selectbox(
            "📅 Change Plan (optional)",
            list(WORKOUT_PLAN.keys()),
            index=default_idx
        )

        if day_plan == "Custom":
            exercise_options = []
        else:
            exercise_options = WORKOUT_PLAN[day_plan]

        col1, col2 = st.columns(2)
        with col1:
            workout_date = st.date_input("Date", value=date.today())
            if exercise_options:
                exercise = st.selectbox("Exercise", exercise_options)
                custom_ex = st.text_input("Or type custom exercise", placeholder="Leave blank to use above")
                if custom_ex:
                    exercise = custom_ex
            else:
                exercise = st.text_input("Exercise Name", placeholder="Enter exercise name")
            mood = st.selectbox("Mood Today", MOODS)

        with col2:
            sets = st.number_input("Number of Sets", min_value=1, max_value=10, value=3)
            st.markdown("**Weight & Reps per set:**")
            set_weights = []
            set_reps = []
            for i in range(sets):
                c1, c2 = st.columns(2)
                w = c1.number_input(f"Set {i+1} Weight (kg)", min_value=0.0, max_value=500.0, value=0.0, step=0.5, key=f"sw_{i}")
                r = c2.number_input(f"Set {i+1} Reps", min_value=1, max_value=100, value=10, key=f"sr_{i}")
                set_weights.append(w)
                set_reps.append(r)

        notes = st.text_area("Notes", placeholder="How did it feel?")

        if st.button("💾 Save Workout", type="primary", use_container_width=True):
            if not exercise:
                st.error("Exercise name required!")
            else:
                try:
                    avg_reps = sum(set_reps) // len(set_reps) if set_reps else 10
                    max_weight = max(set_weights) if set_weights else 0

                    res = client.table("workouts").insert({
                        "user_id": user_id,
                        "date": str(workout_date),
                        "exercise_name": exercise,
                        "sets": sets,
                        "reps": avg_reps,
                        "weight_kg": max_weight,
                        "notes": notes,
                        "mood": mood,
                        "day_plan": day_plan
                    }).execute()

                    workout_id = res.data[0]["id"]

                    for i, (w, r) in enumerate(zip(set_weights, set_reps)):
                        client.table("workout_sets").insert({
                            "user_id": user_id,
                            "workout_id": workout_id,
                            "set_number": i + 1,
                            "weight_kg": w,
                            "reps": r
                        }).execute()

                    pr = get_pr(client, user_id, exercise)
                    if pr and max_weight >= pr["weight_kg"] and max_weight > 0:
                        st.success(f"🏆 NEW PR! {exercise} — {max_weight} kg!")
                        st.balloons()
                    else:
                        st.success(f"✅ {exercise} logged!")

                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        # ── REST TIMER ────────────────────────────────────────────────────────
        st.divider()
        st.subheader("⏱️ Rest Timer")
        rest_time = st.select_slider(
            "Rest Duration",
            options=[30, 45, 60, 90, 120, 180, 240, 300],
            value=90,
            format_func=lambda x: f"{x//60}m {x%60}s" if x >= 60 else f"{x}s"
        )

        c1, c2 = st.columns(2)
        if c1.button("▶️ Start Timer", use_container_width=True, type="primary"):
            st.session_state.timer_start = time.time()
            st.session_state.timer_running = True
            st.session_state.rest_duration = rest_time

        if c2.button("⏹️ Stop", use_container_width=True):
            st.session_state.timer_running = False
            st.session_state.timer_start = None

        if st.session_state.timer_running and st.session_state.timer_start:
            elapsed = time.time() - st.session_state.timer_start
            remaining = max(0, st.session_state.rest_duration - elapsed)
            mins = int(remaining) // 60
            secs = int(remaining) % 60
            st.markdown(f"<div class='timer-box'>⏱️ {mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)
            st.progress(1 - remaining / st.session_state.rest_duration)
            if remaining <= 0:
                st.success("✅ Rest done! Time to lift! 💪")
                st.session_state.timer_running = False
            else:
                time.sleep(1)
                st.rerun()

        # ── TODAY'S LOG ───────────────────────────────────────────────────────
        st.divider()
        st.subheader(f"📋 Today's Log — {date.today()}")
        try:
            res = client.table("workouts").select("*").eq("user_id", user_id)\
                .eq("date", str(date.today())).order("created_at").execute()
            if res.data:
                for row in res.data:
                    mood_val = row.get('mood', '💪 Great')
                    with st.expander(f"🏋️ {row['exercise_name']} — {row['sets']} sets | {mood_val}"):
                        sets_res = client.table("workout_sets").select("*")\
                            .eq("workout_id", row["id"]).order("set_number").execute()
                        if sets_res.data:
                            sets_df = pd.DataFrame(sets_res.data)[["set_number", "weight_kg", "reps"]]
                            sets_df.columns = ["Set", "Weight (kg)", "Reps"]
                            st.dataframe(sets_df, use_container_width=True)

                        col1, col2, col3 = st.columns(3)
                        new_sets = col1.number_input("Sets", value=int(row['sets']), min_value=1, key=f"s_{row['id']}")
                        new_reps = col2.number_input("Reps", value=int(row['reps']), min_value=1, key=f"r_{row['id']}")
                        new_weight = col3.number_input("Weight (kg)", value=float(row['weight_kg']), min_value=0.0, step=0.5, key=f"w_{row['id']}")
                        new_notes = st.text_area("Notes", value=row.get('notes') or "", key=f"n_{row['id']}")

                        c1, c2 = st.columns(2)
                        if c1.button("✅ Update", key=f"u_{row['id']}", use_container_width=True):
                            client.table("workouts").update({
                                "sets": new_sets, "reps": new_reps,
                                "weight_kg": new_weight, "notes": new_notes
                            }).eq("id", row['id']).execute()
                            st.success("Updated!")
                            st.rerun()
                        if c2.button("🗑️ Delete", key=f"d_{row['id']}", use_container_width=True, type="primary"):
                            client.table("workouts").delete().eq("id", row['id']).execute()
                            st.rerun()
            else:
                st.info("No workouts today. Start now! 💪")
        except Exception as e:
            st.error(f"Error: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2: HISTORY
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "📊 My History":
        st.title("📊 Workout History")
        try:
            res = client.table("workouts").select("*").eq("user_id", user_id)\
                .order("date", desc=True).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                col1, col2 = st.columns(2)
                with col1:
                    start = st.date_input("From", value=pd.to_datetime(df["date"]).min())
                with col2:
                    end = st.date_input("To", value=date.today())

                df["date"] = pd.to_datetime(df["date"])
                mask = (df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))
                filtered = df[mask]

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Sessions", len(filtered))
                c2.metric("Unique Exercises", filtered["exercise_name"].nunique())
                c3.metric("Total Sets", int(filtered["sets"].sum()))

                show_cols = ["date", "exercise_name", "sets", "reps", "weight_kg"]
                if "mood" in filtered.columns:
                    show_cols.append("mood")
                if "notes" in filtered.columns:
                    show_cols.append("notes")

                show = filtered[show_cols].copy()
                show["date"] = show["date"].dt.strftime("%Y-%m-%d")
                st.dataframe(show, use_container_width=True)

                st.divider()
                st.subheader("✏️ Edit / 🗑️ Delete")
                for idx, row in filtered.iterrows():
                    with st.expander(f"📅 {row['date'].strftime('%Y-%m-%d')} — {row['exercise_name']}"):
                        col1, col2, col3 = st.columns(3)
                        new_sets = col1.number_input("Sets", value=int(row['sets']), min_value=1, key=f"hs_{row['id']}")
                        new_reps = col2.number_input("Reps", value=int(row['reps']), min_value=1, key=f"hr_{row['id']}")
                        new_weight = col3.number_input("Weight (kg)", value=float(row['weight_kg']), min_value=0.0, step=0.5, key=f"hw_{row['id']}")
                        new_notes = st.text_area("Notes", value=row.get('notes') or "", key=f"hn_{row['id']}")
                        c1, c2 = st.columns(2)
                        if c1.button("✅ Update", key=f"hu_{row['id']}", use_container_width=True):
                            client.table("workouts").update({
                                "sets": new_sets, "reps": new_reps,
                                "weight_kg": new_weight, "notes": new_notes
                            }).eq("id", row['id']).execute()
                            st.success("Updated!")
                            st.rerun()
                        if c2.button("🗑️ Delete", key=f"hd_{row['id']}", use_container_width=True, type="primary"):
                            client.table("workouts").delete().eq("id", row['id']).execute()
                            st.rerun()
            else:
                st.info("No history yet. Log your first workout! 💪")
        except Exception as e:
            st.error(f"Error: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3: PERFORMANCE
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "📈 Performance":
        st.title("📈 Performance Tracker")
        try:
            res = client.table("workouts").select("*").eq("user_id", user_id).order("date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                df["date"] = pd.to_datetime(df["date"])
                df["volume"] = df["sets"] * df["reps"] * df["weight_kg"]

                exercises = df["exercise_name"].unique().tolist()
                selected = st.selectbox("Select Exercise", exercises)
                ex_df = df[df["exercise_name"] == selected]

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Max Weight", f"{ex_df['weight_kg'].max()} kg")
                col2.metric("Max Reps", int(ex_df['reps'].max()))
                col3.metric("Total Sessions", len(ex_df))
                col4.metric("Best Volume", f"{ex_df['volume'].max():.0f}")

                fig1 = px.line(ex_df, x="date", y="weight_kg", markers=True,
                               title="🏋️ Weight Progress", color_discrete_sequence=["#FF4B4B"])
                st.plotly_chart(fig1, use_container_width=True)

                fig2 = px.bar(ex_df, x="date", y="volume",
                              title="📦 Volume Progress", color_discrete_sequence=["#0083B8"])
                st.plotly_chart(fig2, use_container_width=True)

                fig3 = px.line(ex_df, x="date", y="reps", markers=True,
                               title="🔁 Reps Progress", color_discrete_sequence=["#00CC96"])
                st.plotly_chart(fig3, use_container_width=True)

                if "mood" in df.columns:
                    mood_counts = df["mood"].value_counts().reset_index()
                    mood_counts.columns = ["Mood", "Count"]
                    fig4 = px.pie(mood_counts, names="Mood", values="Count", title="😊 Mood Distribution")
                    st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("No data yet. Log some workouts! 💪")
        except Exception as e:
            st.error(f"Error: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4: PERSONAL RECORDS
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "🏆 Personal Records":
        st.title("🏆 Personal Records")
        try:
            res = client.table("workouts").select("*").eq("user_id", user_id).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                prs = df.groupby("exercise_name").agg(
                    Max_Weight=("weight_kg", "max"),
                    Max_Reps=("reps", "max"),
                    Total_Sessions=("id", "count")
                ).reset_index()
                prs.columns = ["Exercise", "Max Weight (kg)", "Max Reps", "Total Sessions"]
                prs = prs.sort_values("Max Weight (kg)", ascending=False)
                st.dataframe(prs, use_container_width=True)

                top5 = prs.head(5)
                fig = px.bar(top5, x="Exercise", y="Max Weight (kg)",
                             title="🏆 Top 5 Lifts", color="Max Weight (kg)",
                             color_continuous_scale="Reds")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No PRs yet. Start lifting! 💪")
        except Exception as e:
            st.error(f"Error: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 5: BODY WEIGHT
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "⚖️ Body Weight":
        st.title("⚖️ Body Weight Tracker")
        with st.form("bw_form"):
            col1, col2 = st.columns(2)
            bw_date = col1.date_input("Date", value=date.today())
            bw_weight = col2.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=70.0, step=0.1)
            bw_notes = st.text_input("Notes", placeholder="Morning weight, after meal, etc.")
            if st.form_submit_button("💾 Save", use_container_width=True):
                try:
                    client.table("body_weight").insert({
                        "user_id": user_id,
                        "date": str(bw_date),
                        "weight_kg": bw_weight,
                        "notes": bw_notes
                    }).execute()
                    st.success("Weight logged!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        try:
            res = client.table("body_weight").select("*").eq("user_id", user_id).order("date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                df["date"] = pd.to_datetime(df["date"])
                col1, col2, col3 = st.columns(3)
                col1.metric("Current", f"{df['weight_kg'].iloc[-1]} kg")
                col2.metric("Min", f"{df['weight_kg'].min()} kg")
                col3.metric("Max", f"{df['weight_kg'].max()} kg")
                fig = px.line(df, x="date", y="weight_kg", markers=True,
                              title="⚖️ Body Weight Progress", color_discrete_sequence=["#00CC96"])
                st.plotly_chart(fig, use_container_width=True)
                show = df[["date", "weight_kg", "notes"]].copy()
                show["date"] = show["date"].dt.strftime("%Y-%m-%d")
                show.columns = ["Date", "Weight (kg)", "Notes"]
                st.dataframe(show, use_container_width=True)
            else:
                st.info("No body weight data yet.")
        except Exception as e:
            st.error(f"Error: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 6: WEEKLY SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "📅 Weekly Summary":
        st.title("📅 Weekly Summary")

        # Weekly plan overview
        st.subheader("📋 Your Weekly Plan")
        plan_data = {
            "Day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "Workout": [
                "Day 1 - Chest + Triceps",
                "Day 2 - Back + Biceps",
                "Day 3 - Legs",
                "Day 4 - Shoulders",
                "Day 5 - Upper Body",
                "Day 6 - Biceps + Triceps + Abs",
                "😴 Rest Day"
            ]
        }
        st.dataframe(pd.DataFrame(plan_data), use_container_width=True)
        st.divider()

        try:
            week_start = date.today() - timedelta(days=date.today().weekday())
            week_end = week_start + timedelta(days=6)
            st.markdown(f"**This Week: {week_start} → {week_end}**")

            res = client.table("workouts").select("*").eq("user_id", user_id)\
                .gte("date", str(week_start)).lte("date", str(week_end)).execute()

            if res.data:
                df = pd.DataFrame(res.data)
                df["date"] = pd.to_datetime(df["date"])
                df["volume"] = df["sets"] * df["reps"] * df["weight_kg"]

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Days Trained", df["date"].nunique())
                col2.metric("Total Exercises", len(df))
                col3.metric("Total Sets", int(df["sets"].sum()))
                col4.metric("Total Volume", f"{df['volume'].sum():.0f} kg")

                daily = df.groupby(df["date"].dt.strftime("%A")).agg(
                    Exercises=("exercise_name", "count"),
                    Volume=("volume", "sum")
                ).reset_index()
                daily.columns = ["Day", "Exercises", "Volume"]
                fig = px.bar(daily, x="Day", y="Volume",
                             title="📊 Daily Volume This Week",
                             color="Volume", color_continuous_scale="Reds")
                st.plotly_chart(fig, use_container_width=True)

                show_cols = ["date", "exercise_name", "sets", "reps", "weight_kg"]
                if "mood" in df.columns:
                    show_cols.append("mood")
                show = df[show_cols].copy()
                show["date"] = show["date"].dt.strftime("%Y-%m-%d")
                st.dataframe(show, use_container_width=True)
            else:
                st.info("No workouts this week yet. Get to the gym! 💪")
        except Exception as e:
            st.error(f"Error: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 7: 1RM CALCULATOR
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "🔢 1RM Calculator":
        st.title("🔢 1 Rep Max Calculator")
        st.markdown("Epley Formula: `1RM = weight × (1 + reps/30)`")

        col1, col2 = st.columns(2)
        weight = col1.number_input("Weight Lifted (kg)", min_value=1.0, max_value=500.0, value=100.0, step=0.5)
        reps = col2.number_input("Reps Performed", min_value=1, max_value=30, value=8)

        one_rm = weight if reps == 1 else weight * (1 + reps / 30)

        st.markdown(f"""
        <div style='background:#1e2130;padding:20px;border-radius:12px;
                    text-align:center;margin:16px 0;border:2px solid #FF4B4B'>
            <h3 style='color:#888;margin:0'>Estimated 1RM</h3>
            <h1 style='color:#FF4B4B;margin:8px 0'>{one_rm:.1f} kg</h1>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("📊 Training Percentages")
        percentages = [100, 95, 90, 85, 80, 75, 70, 65, 60]
        table_data = {
            "% of 1RM": [f"{p}%" for p in percentages],
            "Weight (kg)": [f"{one_rm * p / 100:.1f}" for p in percentages],
            "Suggested Reps": ["1", "2-3", "3-4", "4-6", "6-8", "8-10", "10-12", "12-15", "15-20"]
        }
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)


# ── MAIN ──────────────────────────────────────────────────────────────────────
if st.session_state.user is None:
    show_login()
else:
    show_app()