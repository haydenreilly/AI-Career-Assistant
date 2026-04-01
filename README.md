
Contributors: Hayden Reilly and Jayden St. Louis
Project Title: AI Career Assistant

Description:
The AI Career Strategy Planner is an intelligent decision-support tool designed to help early-career professionals—particularly engineering students—navigate the job search process more strategically and efficiently. While traditional job boards provide large volumes of listings, they lack personalization, prioritization, and actionable guidance. This project addresses that gap by combining automated job aggregation with AI-driven analysis to deliver tailored career insights and recommendations.
At its core, the system builds upon an existing job digest pipeline, which aggregates entry-level chemical engineering, process engineering, and related roles across New England using APIs such as Adzuna, Greenhouse, and Workday. The AI Career Strategy Planner extends this functionality by introducing a reasoning layer that interprets both job market data and user-specific inputs (e.g., resume, skills, career goals). Instead of simply listing jobs, the system evaluates and ranks opportunities based on fit, identifies skill gaps, and generates personalized action plans.
Key features include:
Personalized Job Ranking: Using heuristic filtering and optional AI scoring, the system prioritizes roles based on alignment with the user’s background, interests, and preferred locations.
Resume and Skill Analysis: The tool analyzes the user’s resume to identify missing or underdeveloped skills relative to current job postings, providing targeted recommendations for improvement.
Dynamic Career Strategy Generation: Leveraging generative AI, the system produces weekly or daily action plans (e.g., roles to apply to, skills to develop, networking actions) tailored to the evolving job market.
Automated Job Digest Integration: Building on the existing Python-based job digest system, the platform continuously ingests new job postings, deduplicates them via SQLite, and feeds them into the AI decision pipeline.
User-Facing Interface: A lightweight interface (e.g., Streamlit or email-based reports) presents curated job lists, insights, and recommendations in a clear, actionable format.
The practical impact of this project lies in transforming a passive job search into an active, data-driven strategy. Rather than manually filtering through listings or guessing which roles are the best fit, users receive structured guidance grounded in real-time market data and AI reasoning. This is particularly valuable for engineering students entering competitive industries, where aligning skills, applications, and timing can significantly influence outcomes. By integrating automation, personalization, and generative AI, the AI Career Strategy Planner offers a scalable and innovative approach to career development—turning raw job data into meaningful, strategic decisions.

Resources:

The AI Career Strategy Planner will leverage a combination of existing code infrastructure, open-source tools, and external data sources to enable rapid development and scalability.
Open-Source Repositories and Tools
The project will build upon several widely used open-source frameworks and libraries:
LangChain / LangGraph – for orchestrating multi-step reasoning workflows, such as resume analysis, job matching, and strategy generation.
FAISS or Chroma – for implementing a vector database to enable retrieval-augmented generation (RAG), allowing the system to store and query job descriptions and user data efficiently.
Hugging Face Transformers – for optional local model inference or embedding generation.
Streamlit or Gradio – for developing a lightweight user interface to display job recommendations and career insights.
Pandas, NumPy, and SQLite – for data processing, filtering, and persistent storage of job listings (already used in the existing job digest system).
Additionally, the project directly extends a custom-built Python job aggregation pipeline, which serves as the foundation for data ingestion, deduplication, and preprocessing.
Data Sources
The system will utilize both real-time job data and user-specific inputs:
Job Listing APIs:
Adzuna API (broad job search coverage)
Greenhouse job boards (company-specific postings)
Workday CXS endpoints (structured corporate listings)
User Data:
Resume (uploaded or parsed text)
User preferences (location, role type, industry)
Optional External Data:
Salary benchmarks (if available through APIs)
Company metadata (industry, size, reputation)
These data sources will be continuously updated through the existing job digest pipeline, ensuring that recommendations reflect current market conditions.
Relevant Coursework and Framework Adaptation
This project draws heavily from concepts and tools introduced in EGR 404: Building Tools with Generative AI, particularly:
Prompt engineering and structured output generation
API integration and multi-agent system design
Building end-to-end AI pipelines using Python
Additionally, prior experience with:
MATLAB and data analysis workflows (from chemical engineering coursework)
Process modeling and optimization thinking (from capstone and lab courses)
will inform the design of ranking heuristics and decision logic.
The project will also adapt components from previous assignments and personal projects, including:
The job digest automation script (for data ingestion and filtering)
Email-based reporting pipelines (for delivering results to users)
Structured configuration and environment management practices (e.g., JSON configs, .env files)
Final Deliverables
Working Prototype (Core System):
 A complete Python-based pipeline that integrates the existing job digest system with an AI reasoning layer. The system will:
Aggregate and filter job postings in real time
Rank opportunities based on user fit
Generate personalized career strategies and action plans
Demonstration (Live or Recorded):
 A walkthrough showcasing:
Input of a sample resume and preferences
Automated job ingestion and ranking
AI-generated recommendations (e.g., “top jobs this week,” “skills to improve”)
End-to-end workflow from raw job data to actionable insights
Code Repository (GitHub):
 A well-structured repository containing:
Modular Python scripts (data ingestion, filtering, AI reasoning)
Clear README with setup instructions and usage examples
Configuration files (e.g., API keys via .env, JSON configs)
Documentation of system architecture and design decisions
User Documentation:
 A concise guide explaining:
How to run the system locally
How to input user data (resume, preferences)
How to interpret outputs (rankings, strategy plans)
Performance and Evaluation Metrics:
 The system will include basic evaluation criteria such as:
Relevance of job rankings (based on heuristic or AI scoring consistency)
Accuracy of skill gap identification (compared to job requirements)
Runtime performance of the pipeline (speed in “fast” vs. full AI mode)

