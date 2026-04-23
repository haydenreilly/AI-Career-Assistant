"""
Evaluation test suite for the AI Career Assistant.
Run with:  pytest tests/test_evaluation.py -v
"""
import time
import json
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
_SAMPLE_RESUME = (
    "Chemical engineering student with experience in process design, thermodynamics, "
    "reaction kinetics, and Python scripting. Seeking entry-level role in New England."
)
_REQUIRED_JOB_FIELDS = {'title', 'company', 'location', 'description', 'url', 'salary'}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def config():
    with open(_CONFIG_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def aggregator(config):
    from src.job_aggregator import JobAggregator
    return JobAggregator(config)


@pytest.fixture(scope="session")
def analyzer(config):
    from src.ai_analyzer import AIAnalyzer
    return AIAnalyzer(config)


@pytest.fixture(scope="session")
def jobs(aggregator):
    return aggregator.aggregate_jobs()


@pytest.fixture(scope="session")
def ranked_jobs(analyzer, jobs):
    if jobs:
        analyzer.add_jobs_to_db(jobs)
    return analyzer.rank_jobs(_SAMPLE_RESUME, "New England, entry-level")


# ── Job aggregation ───────────────────────────────────────────────────────────

class TestJobAggregation:
    def test_returns_list(self, jobs):
        assert isinstance(jobs, list)

    def test_jobs_not_empty(self, jobs):
        assert len(jobs) > 0, "No jobs returned — check Adzuna API keys"

    def test_jobs_have_required_fields(self, jobs):
        for job in jobs:
            missing = _REQUIRED_JOB_FIELDS - job.keys()
            assert not missing, f"Job missing fields: {missing}"

    def test_job_titles_are_nonempty_strings(self, jobs):
        for job in jobs:
            assert isinstance(job['title'], str) and job['title'].strip()

    def test_job_urls_are_strings(self, jobs):
        for job in jobs:
            assert isinstance(job['url'], str)

    def test_aggregation_completes_within_15s(self, aggregator):
        start = time.time()
        aggregator.aggregate_jobs()
        assert time.time() - start < 15, "Aggregation exceeded 15-second budget"


# ── Job ranking ───────────────────────────────────────────────────────────────

class TestJobRanking:
    def test_returns_list(self, ranked_jobs):
        assert isinstance(ranked_jobs, list)

    def test_results_not_empty(self, ranked_jobs):
        assert len(ranked_jobs) > 0, "Ranking returned no results"

    def test_each_result_has_score(self, ranked_jobs):
        for job in ranked_jobs:
            assert 'score' in job
            assert isinstance(job['score'], float)

    def test_scores_sorted_ascending(self, ranked_jobs):
        scores = [j['score'] for j in ranked_jobs]
        assert scores == sorted(scores), "Jobs must be sorted by score ascending (lower = better)"

    def test_top_score_is_reasonable(self, ranked_jobs):
        top = ranked_jobs[0]['score']
        assert top < 1.5, f"Top score {top:.3f} is unexpectedly high — check embeddings"

    def test_ranking_completes_within_5s(self, analyzer):
        start = time.time()
        analyzer.rank_jobs(_SAMPLE_RESUME, "New England, entry-level")
        assert time.time() - start < 5, "Ranking exceeded 5-second budget"


# ── AI analysis ───────────────────────────────────────────────────────────────

class TestAIAnalysis:
    def test_skill_analysis_returns_nonempty_string(self, analyzer, jobs):
        if not jobs:
            pytest.skip("No jobs available")
        result = analyzer.analyze_skills(_SAMPLE_RESUME, jobs[0]['description'])
        assert isinstance(result, str) and len(result) > 20

    def test_skill_analysis_does_not_return_error(self, analyzer, jobs):
        if not jobs:
            pytest.skip("No jobs available")
        result = analyzer.analyze_skills(_SAMPLE_RESUME, jobs[0]['description'])
        assert not result.startswith("Error"), f"Skill analysis errored: {result}"

    def test_interview_questions_returns_nonempty_string(self, analyzer, jobs):
        if not jobs:
            pytest.skip("No jobs available")
        result = analyzer.generate_interview_questions(jobs[0]['description'])
        assert isinstance(result, str) and len(result) > 20

    def test_action_plan_returns_nonempty_string(self, analyzer, ranked_jobs):
        result = analyzer.generate_action_plan(ranked_jobs, "Get a chemical engineering job")
        assert isinstance(result, str) and len(result) > 20

    def test_action_plan_does_not_return_error(self, analyzer, ranked_jobs):
        result = analyzer.generate_action_plan(ranked_jobs, "Get a chemical engineering job")
        assert not result.startswith("Error"), f"Action plan errored: {result}"

    def test_skill_analysis_completes_within_30s(self, analyzer, jobs):
        if not jobs:
            pytest.skip("No jobs available")
        start = time.time()
        analyzer.analyze_skills(_SAMPLE_RESUME, jobs[0]['description'])
        assert time.time() - start < 30, "Skill analysis exceeded 30-second budget"
