import streamlit as st
import json
import sys
import os
import csv
import io
from pypdf import PdfReader

st.set_page_config(
    page_title="AI Career Assistant",
    page_icon="briefcase",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Global typography ───────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background-color: #f0f4f8;
}
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* ── Sidebar ─────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #1e3a5f;
    padding-top: 1.5rem;
}

/* Target only specific text nodes — avoids white-on-white inside form widgets */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] summary,
[data-testid="stSidebar"] summary span,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #e2eaf4 !important;
}
[data-testid="stSidebar"] h1 {
    font-size: 1.3rem !important;
    font-weight: 700 !important;
}

/* Input fields */
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea {
    background-color: #2a4a72 !important;
    color: #ffffff !important;
    border: 1px solid #3d6499 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder,
[data-testid="stSidebar"] .stTextArea textarea::placeholder {
    color: #93afd4 !important;
}

/* Dividers */
[data-testid="stSidebar"] hr {
    border-color: #2a4a72 !important;
}

/* File uploader — target the dropzone and the Browse button inside it */
[data-testid="stSidebar"] [data-testid="stFileUploader"],
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background-color: #2a4a72 !important;
    border: 2px dashed #3d6499 !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] small,
[data-testid="stSidebar"] [data-testid="stFileUploader"] span,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] p {
    color: #93afd4 !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
    background-color: #3d6499 !important;
    color: #e2eaf4 !important;
    border: 1px solid #5b9bd5 !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button:hover {
    background-color: #4a7ab5 !important;
}

/* Expander (AI Suggestions) — cover the outer wrapper, details element, and inner content div */
[data-testid="stSidebar"] [data-testid="stExpander"],
[data-testid="stSidebar"] [data-testid="stExpander"] details,
[data-testid="stSidebar"] [data-testid="stExpander"] > div,
[data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
    background-color: #2a4a72 !important;
    border: 1px solid #3d6499 !important;
    border-radius: 8px !important;
}

/* Alert boxes (st.success, st.info, st.error) */
[data-testid="stSidebar"] [data-testid="stAlert"] {
    background-color: #2a4a72 !important;
    border: 1px solid #3d6499 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stAlert"] p {
    color: #e2eaf4 !important;
}

/* ── Page headers ────────────────────────────────────── */
h1 { font-weight: 700 !important; font-size: 2rem !important; letter-spacing: -0.02em; }
h2 { font-weight: 600 !important; }
h3 { font-weight: 600 !important; font-size: 1.1rem !important; }
/* Sidebar headers override the theme's textColor */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #ffffff !important; }

/* ── Metric cards ────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff;
    border-radius: 14px;
    padding: 1.25rem 1.5rem !important;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.8rem !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { color: #1e3a5f !important; font-weight: 700 !important; font-size: 1.8rem !important; }

/* ── Job cards (bordered containers) ────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff !important;
    border-radius: 14px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 6px 20px rgba(0,0,0,0.04) !important;
    padding: 0.25rem 0.5rem !important;
    transition: box-shadow 0.2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.08), 0 12px 32px rgba(0,0,0,0.08) !important;
}

/* ── Buttons ─────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    border: 1px solid #e2e8f0 !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    border-color: #cbd5e1 !important;
}
/* Primary button — solid bright blue so it stands out on both the dark sidebar and light main area */
[data-testid="baseButton-primary"] {
    background-color: #2e86de !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}
/* Streamlit renders button label as a <p>, so override the sidebar p rule explicitly */
[data-testid="baseButton-primary"] p {
    color: #ffffff !important;
}
[data-testid="baseButton-primary"]:hover {
    background-color: #1a6fc4 !important;
    box-shadow: 0 6px 20px rgba(46,134,222,0.35) !important;
}
[data-testid="stDownloadButton"] > button {
    background-color: #059669 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background-color: #047857 !important;
    box-shadow: 0 4px 12px rgba(5,150,105,0.3) !important;
    transform: translateY(-1px) !important;
}

/* ── Progress bars ───────────────────────────────────── */
.stProgress > div {
    background-color: #e2e8f0 !important;
    border-radius: 999px !important;
    height: 8px !important;
}
.stProgress > div > div {
    border-radius: 999px !important;
    background: linear-gradient(90deg, #2e86de, #1e3a5f) !important;
}

/* ── Tabs ────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 2px solid #e2e8f0 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0 !important;
    font-weight: 500 !important;
    color: #64748b !important;
    padding: 10px 20px !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #1e3a5f !important;
    font-weight: 700 !important;
    border-bottom: 2px solid #1e3a5f !important;
}

/* ── Expanders ───────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    background: #f8fafc !important;
}
[data-testid="stExpander"]:hover {
    border-color: #cbd5e1 !important;
}

/* ── Alerts ──────────────────────────────────────────── */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* ── Dividers ────────────────────────────────────────── */
hr { border-color: #e2e8f0 !important; margin: 1.25rem 0 !important; }
</style>
""", unsafe_allow_html=True)

_BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(_BASE_DIR)

from src.job_aggregator import JobAggregator
from src.database import JobDatabase
from src.ai_analyzer import AIAnalyzer


@st.cache_resource
def load_components():
    config_path = os.path.join(_BASE_DIR, 'config', 'config.json')
    with open(config_path) as f:
        config = json.load(f)
    db_path = os.path.join(_BASE_DIR, config['database']['path'])
    return JobAggregator(config), JobDatabase(db_path), AIAnalyzer(config)


aggregator, db, analyzer = load_components()


def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    return "".join(page.extract_text() or "" for page in reader.pages)




def score_to_pct(score):
    """Convert ChromaDB cosine distance (0–2) to a 0–100 match percentage."""
    return max(0, min(100, round((1 - score / 2) * 100)))


# --- Session state ---
_defaults = {
    'user_profile': {'resume_text': '', 'preferences': '', 'goals': '', 'saved_jobs': []},
    'skill_analyses': {},
    'interview_questions': {},
    'action_plan': None,
    'ai_profile': None,
    'suggested_job_titles': [],
    'suggested_locations': [],
    'suggestion_version': 0,
    'experience_level': 'Any level',
}
for key, default in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

_EXPERIENCE_OPTIONS = {
    "Any level":   None,
    "Internship":  "intern",
    "Entry level": "entry level",
    "Mid level":   "mid level",
    "Senior":      "senior",
    "Manager":     "manager",
    "Director":    "director",
}

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Your Profile")
    st.divider()

    uploaded_file = st.file_uploader("Resume (PDF)", type="pdf", label_visibility="collapsed")

    resume = ""
    if uploaded_file is not None:
        new_resume = extract_text_from_pdf(uploaded_file)
        if new_resume != st.session_state.user_profile['resume_text']:
            st.session_state.user_profile['resume_text'] = new_resume
            st.session_state.ai_profile = None  # reset for new resume
        resume = st.session_state.user_profile['resume_text']
        st.success("Resume loaded")

        if st.session_state.ai_profile is None:
            with st.spinner("Analyzing resume..."):
                profile = analyzer.suggest_profile(resume)
            st.session_state.ai_profile = profile
            st.session_state.suggested_job_titles = profile['job_titles']
            st.session_state.suggested_locations = profile['locations']
            st.session_state.suggestion_version += 1
            if profile.get('preferences'):
                st.session_state.user_profile['preferences'] = profile['preferences']
            if profile.get('goals'):
                st.session_state.user_profile['goals'] = profile['goals']
    else:
        resume = st.session_state.user_profile.get('resume_text', '')
        if resume:
            st.info("Using saved resume")
        else:
            st.caption("Upload a PDF resume to get started.")

    st.divider()

    preferences = st.text_input(
        "Career preferences",
        placeholder="e.g. remote-friendly, New England",
        value=st.session_state.user_profile.get('preferences', ''),
    )
    goals = st.text_area(
        "Career goals",
        placeholder="e.g. Secure a role within 3 months",
        value=st.session_state.user_profile.get('goals', ''),
        height=80,
    )
    st.session_state.user_profile['preferences'] = preferences
    st.session_state.user_profile['goals'] = goals

    st.divider()
    st.caption("Search settings")

    ver = st.session_state.suggestion_version
    title_opts = st.session_state.suggested_job_titles or ["Chemical Engineer"]
    loc_opts   = st.session_state.suggested_locations   or ["Boston"]

    selected_titles = st.multiselect(
        "Job titles",
        options=title_opts,
        default=title_opts,
        key=f"titles_{ver}",
        accept_new_options=True,
        help="All resume-suggested titles are pre-selected. Type to add your own.",
    )
    selected_locations = st.multiselect(
        "Locations",
        options=loc_opts,
        default=loc_opts,
        key=f"locations_{ver}",
        accept_new_options=True,
        help="Type to add custom locations. Regions like 'New England' auto-expand.",
    )
    experience_label = st.selectbox(
        "Experience level",
        options=list(_EXPERIENCE_OPTIONS.keys()),
        index=list(_EXPERIENCE_OPTIONS.keys()).index(st.session_state.experience_level),
    )
    st.session_state.experience_level = experience_label

    st.divider()

    if st.button("Find & Rank Jobs", type="primary", use_container_width=True):
        if not resume:
            st.error("Please upload your resume first.")
        elif not selected_titles:
            st.error("Select at least one job title.")
        elif not selected_locations:
            st.error("Select at least one location.")
        else:
            with st.spinner("Fetching jobs..."):
                jobs = aggregator.aggregate_jobs(
                    queries=selected_titles,
                    locations=selected_locations,
                    experience_level=_EXPERIENCE_OPTIONS[experience_label],
                )
            if not jobs:
                st.error(
                    f"No jobs found for {selected_titles} in {selected_locations}. "
                    "Try different titles or locations."
                )
            else:
                db.insert_jobs(jobs)
                with st.spinner("Building embeddings..."):
                    analyzer.add_jobs_to_db(jobs)
                with st.spinner("Ranking by fit..."):
                    ranked_jobs = analyzer.rank_jobs(resume, preferences)
                st.session_state.user_profile['saved_jobs'] = ranked_jobs
                st.session_state.skill_analyses = {}
                st.session_state.interview_questions = {}
                st.session_state.action_plan = None

# ── Main panel ───────────────────────────────────────────────────────────────
st.title("AI Career Strategy Planner")
st.caption("Personalized job ranking and career guidance powered by AI.")

saved_jobs = st.session_state.user_profile['saved_jobs']

if not saved_jobs:
    st.info("Upload your resume and click **Find & Rank Jobs** in the sidebar to get started.")
    st.stop()

# Summary metrics row
top_pct = score_to_pct(saved_jobs[0]['score'])
avg_pct = round(sum(score_to_pct(j['score']) for j in saved_jobs) / len(saved_jobs))
jobs_with_salary = [j for j in saved_jobs if j.get('salary')]
avg_salary = (
    f"${round(sum(j['salary'] for j in jobs_with_salary) / len(jobs_with_salary)):,}/yr"
    if jobs_with_salary else "N/A"
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Jobs Ranked", len(saved_jobs))
m2.metric("Top Match", f"{top_pct}%")
m3.metric("Avg Match", f"{avg_pct}%")
m4.metric("Avg Salary", avg_salary)

st.divider()

tab_jobs, tab_plan = st.tabs(["Job Matches", "Weekly Action Plan"])

# ── Tab 1: Job cards ──────────────────────────────────────────────────────────
with tab_jobs:
    # CSV export
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["Rank", "Title", "Company", "Location", "Match %", "Salary", "URL"])
    writer.writeheader()
    for i, job in enumerate(saved_jobs):
        salary = job.get('salary')
        writer.writerow({
            "Rank": i + 1,
            "Title": job['title'],
            "Company": job['company'],
            "Location": job['location'],
            "Match %": score_to_pct(job['score']),
            "Salary": f"${salary:,.0f}" if salary else "",
            "URL": job['url'],
        })
    st.download_button(
        "Download as CSV",
        data=buf.getvalue(),
        file_name="ranked_jobs.csv",
        mime="text/csv",
    )

    for idx, job in enumerate(saved_jobs):
        pct = score_to_pct(job['score'])
        match_color = "green" if pct >= 70 else "orange" if pct >= 50 else "red"

        with st.container(border=True):
            header_left, header_right = st.columns([3, 1])

            with header_left:
                st.subheader(f"{idx + 1}. {job['title']}")
                st.caption(f"**{job['company']}**  ·  {job['location']}")

            with header_right:
                salary = job.get('salary')
                salary_str = f"${salary:,.0f}/yr" if salary else "Salary not listed"
                st.markdown(f"**{salary_str}**")
                st.markdown(f":{match_color}[**{pct}% match**]")
                st.progress(pct / 100)

            with st.expander("Job description"):
                st.write(job['description'][:600] + ("..." if len(job['description']) > 600 else ""))

            st.markdown(f"[Apply here]({job['url']})")

            btn1, btn2 = st.columns(2)
            with btn1:
                if st.button("Analyze Skills", key=f"skill_{idx}", use_container_width=True):
                    with st.spinner("Analyzing skill gaps..."):
                        st.session_state.skill_analyses[idx] = analyzer.analyze_skills(
                            resume, job['description']
                        )
            with btn2:
                if st.button("Interview Prep", key=f"interview_{idx}", use_container_width=True):
                    with st.spinner("Generating questions..."):
                        st.session_state.interview_questions[idx] = analyzer.generate_interview_questions(
                            job['description']
                        )

            if idx in st.session_state.skill_analyses:
                with st.expander("Skill Analysis", expanded=True):
                    st.write(st.session_state.skill_analyses[idx])

            if idx in st.session_state.interview_questions:
                with st.expander("Interview Questions", expanded=True):
                    st.write(st.session_state.interview_questions[idx])

# ── Tab 2: Action plan ────────────────────────────────────────────────────────
with tab_plan:
    if not goals:
        st.info("Enter your career goals in the sidebar, then come back here.")
    else:
        if st.button("Generate Weekly Action Plan", type="primary"):
            with st.spinner("Building your action plan..."):
                st.session_state.action_plan = analyzer.generate_action_plan(saved_jobs, goals)

        if st.session_state.action_plan:
            st.write(st.session_state.action_plan)
