import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
import pandas as pd
import plotly.express as px
from datetime import date

# ── CONFIG ──────────────────────────────────────────────────────────────────
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="💪 Gym Tracker", layout="wide")

# ── SESSION STATE ────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None
if "token" not in st.session_state:
    st.session_state.token = None

# ── AUTH FUNCTIONS ────────────────────────────────────────────────────────────
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
        res = supabase.auth.sign_up({"email": email, "password": password})
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

# ── LOGIN PAGE ────────────────────────────────────────────────────────────────
def show_login():
    st.title("💪 Gym Tracker")
    st.subheader("Track your workouts, crush your goals!")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", use_container_width=True):
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
        st.title("💪 Gym Tracker")
        st.write(f"👤 {st.session_state.user.email}")
        st.divider()
        page = st.radio("Navigate", ["📝 Log Workout", "📊 My History", "📈 Performance"])
        st.divider()
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()

    # ── PAGE 1: LOG WORKOUT ──────────────────────────────────────────────────
    if page == "📝 Log Workout":
        st.title("📝 Log Today's Workout")

        with st.form("workout_form"):
            col1, col2 = st.columns(2)
            with col1:
                workout_date = st.date_input("Date", value=date.today())
                exercise = st.text_input("Exercise Name", placeholder="e.g. Bench Press, Squat")
                sets = st.number_input("Sets", min_value=1, max_value=20, value=3)
            with col2:
                reps = st.number_input("Reps", min_value=1, max_value=100, value=10)
                weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, value=0.0, step=0.5)
                notes = st.text_area("Notes", placeholder="How did it feel?")

            submitted = st.form_submit_button("💾 Save Workout", use_container_width=True)

            if submitted:
                if not exercise:
                    st.error("Exercise name required!")
                else:
                    try:
                        client.table("workouts").insert({
                            "user_id": user_id,
                            "date": str(workout_date),
                            "exercise_name": exercise,
                            "sets": sets,
                            "reps": reps,
                            "weight_kg": weight,
                            "notes": notes
                        }).execute()
                        st.success(f"✅ {exercise} logged successfully!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {e}")

        # Today's log with Edit & Delete
        st.divider()
        st.subheader(f"📋 Today's Log — {date.today()}")
        try:
            res = client.table("workouts").select("*").eq("user_id", user_id).eq("date", str(date.today())).order("created_at").execute()
            if res.data:
                df = pd.DataFrame(res.data)

                for idx, row in df.iterrows():
                    with st.expander(f"🏋️ {row['exercise_name']} — {row['sets']} sets × {row['reps']} reps @ {row['weight_kg']} kg"):
                        col1, col2, col3 = st.columns(3)

                        new_sets   = col1.number_input("Sets",       value=int(row['sets']),         min_value=1,  key=f"sets_{row['id']}")
                        new_reps   = col2.number_input("Reps",       value=int(row['reps']),         min_value=1,  key=f"reps_{row['id']}")
                        new_weight = col3.number_input("Weight (kg)", value=float(row['weight_kg']), min_value=0.0, step=0.5, key=f"weight_{row['id']}")
                        new_notes  = st.text_area("Notes", value=row['notes'] or "", key=f"notes_{row['id']}")

                        c1, c2 = st.columns(2)

                        if c1.button("✅ Update", key=f"update_{row['id']}", use_container_width=True):
                            client.table("workouts").update({
                                "sets": new_sets,
                                "reps": new_reps,
                                "weight_kg": new_weight,
                                "notes": new_notes
                            }).eq("id", row['id']).execute()
                            st.success("Updated!")
                            st.rerun()

                        if c2.button("🗑️ Delete", key=f"delete_{row['id']}", use_container_width=True, type="primary"):
                            client.table("workouts").delete().eq("id", row['id']).execute()
                            st.success("Deleted!")
                            st.rerun()
            else:
                st.info("No workouts logged today. Start now! 💪")
        except Exception as e:
            st.error(f"Error: {e}")

    # ── PAGE 2: HISTORY ──────────────────────────────────────────────────────
    elif page == "📊 My History":
        st.title("📊 Workout History")

        try:
            res = client.table("workouts").select("*").eq("user_id", user_id).order("date", desc=True).execute()
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

                st.metric("Total Workouts", len(filtered))

                show = filtered[["date", "exercise_name", "sets", "reps", "weight_kg", "notes"]].copy()
                show.columns = ["Date", "Exercise", "Sets", "Reps", "Weight (kg)", "Notes"]
                show["Date"] = show["Date"].dt.strftime("%Y-%m-%d")
                st.dataframe(show, use_container_width=True)

                # Edit & Delete from history
                st.divider()
                st.subheader("✏️ Edit / 🗑️ Delete a workout")

                for idx, row in filtered.iterrows():
                    with st.expander(f"📅 {row['date'].strftime('%Y-%m-%d')} — {row['exercise_name']}"):
                        col1, col2, col3 = st.columns(3)

                        new_sets   = col1.number_input("Sets",        value=int(row['sets']),         min_value=1,   key=f"h_sets_{row['id']}")
                        new_reps   = col2.number_input("Reps",        value=int(row['reps']),         min_value=1,   key=f"h_reps_{row['id']}")
                        new_weight = col3.number_input("Weight (kg)", value=float(row['weight_kg']), min_value=0.0, step=0.5, key=f"h_weight_{row['id']}")
                        new_notes  = st.text_area("Notes", value=row['notes'] or "", key=f"h_notes_{row['id']}")

                        c1, c2 = st.columns(2)

                        if c1.button("✅ Update", key=f"h_update_{row['id']}", use_container_width=True):
                            client.table("workouts").update({
                                "sets": new_sets,
                                "reps": new_reps,
                                "weight_kg": new_weight,
                                "notes": new_notes
                            }).eq("id", row['id']).execute()
                            st.success("Updated!")
                            st.rerun()

                        if c2.button("🗑️ Delete", key=f"h_delete_{row['id']}", use_container_width=True, type="primary"):
                            client.table("workouts").delete().eq("id", row['id']).execute()
                            st.success("Deleted!")
                            st.rerun()
            else:
                st.info("No workout history yet. Log your first workout! 💪")
        except Exception as e:
            st.error(f"Error: {e}")

    # ── PAGE 3: PERFORMANCE ──────────────────────────────────────────────────
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

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Max Weight", f"{ex_df['weight_kg'].max()} kg")
                with col2:
                    st.metric("Max Reps", int(ex_df['reps'].max()))
                with col3:
                    st.metric("Total Sessions", len(ex_df))

                st.subheader(f"🏋️ Weight Progress — {selected}")
                fig1 = px.line(ex_df, x="date", y="weight_kg", markers=True,
                               title="Weight over time", color_discrete_sequence=["#FF4B4B"])
                st.plotly_chart(fig1, use_container_width=True)

                st.subheader("📦 Volume Progress (Sets × Reps × Weight)")
                fig2 = px.bar(ex_df, x="date", y="volume",
                              title="Total Volume per session", color_discrete_sequence=["#0083B8"])
                st.plotly_chart(fig2, use_container_width=True)

                st.subheader("🔁 Reps Progress")
                fig3 = px.line(ex_df, x="date", y="reps", markers=True,
                               color_discrete_sequence=["#00CC96"])
                st.plotly_chart(fig3, use_container_width=True)

            else:
                st.info("No data yet. Log some workouts first! 💪")
        except Exception as e:
            st.error(f"Error: {e}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
if st.session_state.user is None:
    show_login()
else:
    show_app()