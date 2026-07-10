"""
MI Cricket Intelligence — Scouting Dashboard
Password-protected ops dashboard reading from the same Google Sheet.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.sheets import read_all_reports

st.set_page_config(page_title="MI Scout Dashboard", page_icon="📊", layout="wide")

# ── Password Protection ──
DASHBOARD_PASSWORD = st.secrets.get("dashboard_password", "MIops2025")

if "dashboard_authenticated" not in st.session_state:
    st.session_state.dashboard_authenticated = False

if not st.session_state.dashboard_authenticated:
    st.markdown("## 🔒 MI Cricket Intelligence — Dashboard")
    st.caption("Restricted to the ops team.")
    pwd = st.text_input("Enter password", type="password")
    if st.button("Access", type="primary"):
        if pwd == DASHBOARD_PASSWORD:
            st.session_state.dashboard_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# ── Load data ──
st.markdown("## 📊 MI Cricket Intelligence — Scouting Dashboard")
df = read_all_reports()

# Deduplicate: keep latest report per player (by submittedAt)
if not df.empty and "firstName" in df.columns and "lastName" in df.columns:
    if "submittedAt" in df.columns:
        df = df.sort_values("submittedAt", ascending=False).drop_duplicates(
            subset=["firstName", "lastName"], keep="first"
        ).reset_index(drop=True)

if df.empty:
    st.info("No reports yet. File your first report from the Scouting Form.")
    st.stop()

# ── Sidebar Filters ──
st.sidebar.markdown("### 🔍 Filters")

# Team filter (MI Men / MI Women) — prominent at top
teams_available = sorted(df["team"].dropna().unique().tolist()) if "team" in df.columns else []
team_filter = st.sidebar.radio("Team", ["All"] + teams_available, index=0)

grades_available = sorted(df["currentGrade"].dropna().unique().tolist()) if "currentGrade" in df.columns else []
grade_filter = st.sidebar.multiselect("Grade", grades_available, default=grades_available)
recs_available = sorted(df["recommendation"].dropna().unique().tolist()) if "recommendation" in df.columns else []
rec_filter = st.sidebar.multiselect("Recommendation", recs_available, default=recs_available)
states_available = sorted(df["state"].dropna().unique().tolist()) if "state" in df.columns else []
state_filter = st.sidebar.multiselect("State", states_available, default=states_available)
specs_available = sorted(df["specialism"].dropna().unique().tolist()) if "specialism" in df.columns else []
spec_filter = st.sidebar.multiselect("Specialism", specs_available, default=specs_available)

filtered = df.copy()
if team_filter != "All" and "team" in filtered.columns:
    filtered = filtered[filtered["team"] == team_filter]
if "currentGrade" in filtered.columns:
    filtered = filtered[filtered["currentGrade"].isin(grade_filter)]
if "recommendation" in filtered.columns:
    filtered = filtered[filtered["recommendation"].isin(rec_filter)]
if "state" in filtered.columns:
    filtered = filtered[filtered["state"].isin(state_filter)]
if "specialism" in filtered.columns:
    filtered = filtered[filtered["specialism"].isin(spec_filter)]

st.caption(f"Showing {len(filtered)} of {len(df)} reports")

# ── Export CSV ──
if len(filtered) > 0:
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button("📥 Export to CSV", csv, "scout_reports.csv", "text/csv")

st.markdown("---")

# ── KPIs ──
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Reports", len(filtered))
with col2:
    hot = len(filtered[filtered.get("urgency", pd.Series()) == "Hot Prospect"]) if "urgency" in filtered.columns else 0
    st.metric("🔥 Hot Prospects", hot)
with col3:
    sign_now = len(filtered[filtered.get("recommendation", pd.Series()) == "Sign Now"]) if "recommendation" in filtered.columns else 0
    st.metric("Sign Now", sign_now)
with col4:
    scouts = filtered["scoutName"].nunique() if "scoutName" in filtered.columns else 0
    st.metric("Active Scouts", scouts)
with col5:
    states_count = filtered["state"].nunique() if "state" in filtered.columns else 0
    st.metric("States Covered", states_count)

st.markdown("---")

# ── Tabs ──
tab1, tab2, tab3, tab4 = st.tabs(["📋 Players", "📊 Grades", "🗺️ States", "📈 Timeline"])

with tab1:
    display_cols = ["firstName", "lastName", "state", "specialism", "currentGrade",
                    "recommendation", "urgency", "dateWatched", "scoutName", "comparedTo"]
    available_cols = [c for c in display_cols if c in filtered.columns]
    if available_cols:
        st.dataframe(filtered[available_cols], use_container_width=True, hide_index=True)

with tab2:
    if "currentGrade" in filtered.columns and len(filtered) > 0:
        grade_order = ["A+", "A", "B+", "B", "C"]
        grade_counts = filtered["currentGrade"].value_counts().reindex(grade_order).dropna()
        fig = px.bar(x=grade_counts.index, y=grade_counts.values, labels={"x": "Grade", "y": "Count"}, title="Grade Distribution")
        st.plotly_chart(fig, use_container_width=True)
        if "recommendation" in filtered.columns:
            rec_counts = filtered["recommendation"].value_counts()
            fig2 = px.pie(values=rec_counts.values, names=rec_counts.index, title="Recommendations")
            st.plotly_chart(fig2, use_container_width=True)

with tab3:
    if "state" in filtered.columns and len(filtered) > 0:
        state_counts = filtered["state"].value_counts().head(15)
        fig = px.bar(x=state_counts.values, y=state_counts.index, orientation="h", labels={"x": "Reports", "y": "State"}, title="Reports by State")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    if "dateWatched" in filtered.columns and len(filtered) > 0:
        timeline = filtered.copy()
        timeline["dateWatched"] = pd.to_datetime(timeline["dateWatched"], errors="coerce")
        timeline = timeline.dropna(subset=["dateWatched"])
        if len(timeline) > 0:
            daily = timeline.groupby(timeline["dateWatched"].dt.date).size().reset_index(name="count")
            daily.columns = ["date", "count"]
            fig = px.line(daily, x="date", y="count", title="Reports Over Time", markers=True)
            st.plotly_chart(fig, use_container_width=True)

# ── Player Detail ──
st.markdown("---")
st.markdown("### 🔎 Player Detail")
if len(filtered) > 0 and "firstName" in filtered.columns:
    player_names = (filtered["firstName"].fillna("") + " " + filtered["lastName"].fillna("")).tolist()
    selected = st.selectbox("Select player", [""] + player_names)
    if selected:
        idx = player_names.index(selected)
        player = filtered.iloc[idx]
        col1, col2 = st.columns([1, 2])
        with col1:
            grade = player.get("currentGrade", "—")
            st.markdown(f"### Grade: **{grade}**")
            st.markdown(f"**Ceiling:** {player.get('ceilingGrade', '—')}")
            st.markdown(f"**Rec:** {player.get('recommendation', '—')}")
            st.markdown(f"**Urgency:** {player.get('urgency', '—')}")
        with col2:
            st.markdown(f"**{selected}** · {player.get('specialism', '')} · {player.get('state', '')}")
            st.markdown(f"**Watched:** {player.get('dateWatched', '—')} · {player.get('context', '')}")
            if player.get("comparedTo"):
                st.info(f"🔄 {player['comparedTo']}")
            if player.get("finalWord"):
                st.markdown(f"> ✍️ *\"{player['finalWord']}\"*")

        # Media
        media_ids = player.get("mediaFileIds", "")
        if media_ids and str(media_ids).strip():
            st.markdown("#### 📸 Media")
            file_ids = [fid.strip() for fid in str(media_ids).split(",") if fid.strip()]
            cols = st.columns(min(len(file_ids), 3))
            for i, fid in enumerate(file_ids):
                with cols[i % 3]:
                    view_url = f"https://drive.google.com/file/d/{fid}/view"
                    img_url = f"https://drive.google.com/thumbnail?id={fid}&sz=w400"
                    st.markdown(f'<a href="{view_url}" target="_blank"><img src="{img_url}" style="width:100%;border-radius:8px" /></a>', unsafe_allow_html=True)

        videos = player.get("videos", "")
        if videos and str(videos).strip():
            st.markdown("#### 🎥 Videos")
            for link in str(videos).strip().split("\n"):
                link = link.strip()
                if "youtube.com" in link or "youtu.be" in link:
                    st.video(link)
                elif link:
                    st.markdown(f"🔗 [{link}]({link})")

# ── Refresh ──
st.markdown("---")
if st.button("🔄 Refresh data"):
    read_all_reports.clear()
    st.rerun()


# ══════════════════════════════════════
# MEDIA BROWSER
# ══════════════════════════════════════
st.markdown("---")
st.markdown("### 📁 Media Browser")
st.caption("Browse all uploaded videos and photos by player")

R2_PUBLIC_URL = "https://pub-baf64f6313b2499eae38dee9c711ffb3.r2.dev"

# Get media links from the sheet data
if "mediaFileLinks" in filtered.columns:
    media_df = filtered[filtered["mediaFileLinks"].fillna("").str.strip() != ""]
    if len(media_df) > 0:
        # Group by player
        players_with_media = {}
        for _, row in media_df.iterrows():
            name = f"{row.get('firstName', '')} {row.get('lastName', '')}".strip()
            links = str(row["mediaFileLinks"]).split(", ")
            if name not in players_with_media:
                players_with_media[name] = []
            players_with_media[name].extend(links)

        st.write(f"**{len(players_with_media)} players** with uploaded media")

        for player, links in sorted(players_with_media.items()):
            with st.expander(f"📂 {player} ({len(links)} files)"):
                for link in links:
                    filename = link.split("/")[-1] if "/" in link else link
                    is_video = any(ext in filename.lower() for ext in [".mp4", ".mov", ".avi", ".webm"])
                    if is_video:
                        st.video(link)
                    else:
                        st.image(link, width=300)
                    st.caption(f"[⬇ Download]({link})")
    else:
        st.info("No media uploaded yet.")
else:
    st.info("No media column found in the data.")
