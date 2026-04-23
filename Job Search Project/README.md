Contributors: Hayden Reilly and Jayden St. Louis
Project Title: AI Career Assistant
AI Career Strategy Planner
The AI Career Strategy Planner is an intelligent decision-support tool designed to help early-career professionals—especially engineering students—navigate the job search more strategically. Traditional job boards provide large volumes of listings but lack personalization and actionable guidance. This project addresses that gap by combining automated job aggregation with AI-driven analysis to deliver tailored recommendations. The system builds on an existing Python-based job digest pipeline that aggregates entry-level chemical engineering and related roles across New England using APIs such as Adzuna, Greenhouse, and Workday. It extends this by adding an AI reasoning layer that evaluates job listings alongside user-specific inputs (resume, skills, career goals). Rather than simply listing jobs, the system ranks opportunities based on fit, identifies skill gaps, and generates personalized action plans.
Key features include:
Personalized Job Ranking: Prioritizes roles based on alignment with user background, interests, and location.
Resume & Skill Analysis: Identifies missing or underdeveloped skills relative to job requirements.
Dynamic Career Strategy: Generates daily or weekly action plans (applications, skills, networking).
User Interface: Presents curated jobs and insights via a lightweight interface (e.g., Streamlit or email reports).
Resources
Tools & Frameworks:
LangChain / LangGraph (AI workflows)
FAISS or Chroma (vector database for RAG)
Hugging Face Transformers (embeddings/inference)
Streamlit or Gradio (UI)
Pandas, NumPy, SQLite (data processing & storage)
Data Sources:
Job APIs: Adzuna, Workday User inputs: resume, preferences 
Hayden: Working Prototype: End-to-end system integrating job aggregation with AI-driven ranking and strategy generation. Demonstration: Showcase of resume input, job ranking, and AI-generated recommendations. Implementing APIs into code.
Jayden: GitHub Repository: Modular codebase with README, configs, and documentation. User Guide: Instructions for setup, inputs, and interpreting outputs. Evaluation Metrics: Job ranking relevance, skill gap accuracy, and runtime performance. Optimizing code output.

## New Features Added
- **Interview Preparation**: AI-generated mock interview questions for job roles.
- **Personalized Dashboard**: Session-based user profiles for saving preferences and job history.

## Setup Instructions

1. Install dependencies: `pip install -r requirements.txt`
2. Set up API keys in `.env` file (get from respective services: Adzuna, OpenAI)
3. Run the app: `streamlit run src/ui.py`

## User Guide

### Inputs
- **Resume**: Upload a PDF file of your resume. The app will automatically extract the text.
- **Preferences**: Enter or edit career preferences (e.g., location, job type). AI suggestions are provided based on your resume.
- **Goals**: Enter or edit career goals (e.g., short-term objectives). AI suggestions are provided based on your resume.

### Interpreting Outputs
- **Ranked Jobs**: Jobs are ranked by relevance to your resume and preferences. Lower scores indicate better matches.
- **Skill Analysis**: Click on a job to see AI-generated analysis of skill gaps and improvement suggestions.
- **Interview Preparation**: Generate mock interview questions for specific jobs.
- **Action Plan**: Weekly plan based on your goals and ranked jobs.

### Requirements
- Valid API keys for job fetching and AI features.
- Internet connection for API calls.
- PDF resume file.

## Evaluation Metrics

Run `python tests/test_evaluation.py` to evaluate:
- **Job Ranking Relevance**: Mock metric based on embedding similarity scores.
- **Skill Gap Accuracy**: Qualitative assessment via AI responses.
- **Runtime Performance**: Time taken for aggregation, ranking, analysis, and planning.

## Optimization
- Vector database (ChromaDB) for fast similarity searches.
- Modular code for easy extension.
- Asynchronous potential for API calls.