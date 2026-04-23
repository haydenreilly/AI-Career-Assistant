import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

class AIAnalyzer:
    def __init__(self, config):
        self.config = config
        self.llm_model = config['ai']['llm_model']
        self.embedding_model = SentenceTransformer(config['ai']['embedding_model'])
        chroma_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'chroma')
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_or_create_collection(name="jobs")
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def embed_text(self, text):
        return self.embedding_model.encode(text).tolist()

    def add_jobs_to_db(self, jobs):
        # Clear previous search results so stale jobs don't pollute the ranking
        existing = self.collection.get()
        if existing['ids']:
            self.collection.delete(ids=existing['ids'])

        ids = [hashlib.md5(job['url'].encode()).hexdigest() for job in jobs]
        documents = [job['description'] for job in jobs]
        embeddings = [self.embed_text(doc) for doc in documents]
        metadatas = [
            {
                'title': job['title'],
                'company': job['company'],
                'location': job['location'],
                'url': job['url'],
                'salary': job['salary'],
            }
            for job in jobs
        ]
        # upsert avoids duplicate-ID errors on repeated analysis runs
        self.collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

    def rank_jobs(self, user_resume, user_preferences, top_k=10):
        user_text = user_resume + " " + user_preferences
        user_embedding = self.embed_text(user_text)
        results = self.collection.query(query_embeddings=[user_embedding], n_results=top_k)
        ranked_jobs = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            score = results['distances'][0][i]
            ranked_jobs.append({
                'title': metadata['title'],
                'company': metadata['company'],
                'location': metadata['location'],
                'description': doc,
                'url': metadata['url'],
                'salary': metadata['salary'],
                'score': score,
            })
        return ranked_jobs

    def analyze_skills(self, resume, job_description):
        resume_snippet = resume[:2000]
        prompt = (
            f"Compare the user's resume with the job description. "
            f"Identify missing skills and suggest improvements.\n\n"
            f"Resume: {resume_snippet}\n\nJob: {job_description}\n\nAnalysis:"
        )
        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error in skill analysis: {str(e)}"

    def generate_interview_questions(self, job_description):
        prompt = (
            f"Generate 5 common interview questions for a job with this description:\n\n"
            f"{job_description}\n\nQuestions:"
        )
        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating questions: {str(e)}"

    def suggest_profile(self, resume_text):
        import json as _json
        prompt = (
            "Based on this resume, generate job search suggestions.\n\n"
            f"Resume: {resume_text[:2000]}\n\n"
            "Return ONLY valid JSON in this exact format — no markdown, no extra text:\n"
            '{"job_titles": ["Title1", "Title2", "Title3"], '
            '"locations": ["City1", "State1"], '
            '"preferences": "one sentence", '
            '"goals": "one sentence"}\n\n'
            "job_titles: 4-5 specific roles this person is qualified for\n"
            "locations: 2-3 specific US cities or states (e.g. Boston, Massachusetts)\n"
            "preferences: brief career preference summary\n"
            "goals: brief career goal summary"
        )
        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
            )
            content = response.choices[0].message.content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:].strip()
            return _json.loads(content)
        except Exception:
            return {
                "job_titles": ["Engineer", "Analyst", "Consultant"],
                "locations": ["Boston", "Massachusetts"],
                "preferences": "",
                "goals": "",
            }

    def generate_action_plan(self, ranked_jobs, goals):
        jobs_summary = "\n".join(
            f"- {job['title']} at {job['company']} in {job['location']}"
            for job in ranked_jobs[:5]
        )
        prompt = (
            f"Based on these top job matches and the user's goals, create a weekly action plan "
            f"for job searching.\n\nGoals: {goals}\n\nTop Jobs:\n{jobs_summary}\n\nWeekly Action Plan:"
        )
        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating action plan: {str(e)}"
