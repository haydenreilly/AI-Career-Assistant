import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

# Maps common region names to the individual cities/states Adzuna accepts.
_REGION_ALIASES = {
    "new england":       ["boston", "massachusetts", "connecticut", "rhode island",
                          "new hampshire", "vermont", "maine"],
    "northeast":         ["new york", "new jersey", "pennsylvania", "massachusetts",
                          "connecticut", "rhode island", "new hampshire", "vermont", "maine"],
    "mid-atlantic":      ["new york", "new jersey", "pennsylvania", "maryland", "delaware"],
    "southeast":         ["florida", "georgia", "north carolina", "south carolina",
                          "virginia", "tennessee"],
    "midwest":           ["illinois", "ohio", "michigan", "indiana", "wisconsin", "minnesota"],
    "southwest":         ["texas", "arizona", "new mexico", "oklahoma"],
    "west coast":        ["california", "oregon", "washington"],
    "pacific northwest": ["oregon", "washington"],
    "mountain west":     ["colorado", "utah", "nevada", "idaho", "montana", "wyoming"],
    "south":             ["texas", "florida", "georgia", "north carolina", "south carolina",
                          "virginia", "tennessee", "alabama", "louisiana"],
}


class JobAggregator:
    def __init__(self, config):
        self.config = config

    def fetch_adzuna_jobs(self, query="chemical engineering", location="boston", max_results=10, experience_level=None):
        app_id = os.getenv('ADZUNA_APP_ID')
        app_key = os.getenv('ADZUNA_APP_KEY')
        if not app_id or not app_key:
            return []
        params = {
            'app_id': app_id,
            'app_key': app_key,
            'results_per_page': max_results,
            'what': query,
            'where': location,
        }
        if experience_level:
            params['what_and'] = experience_level
        try:
            response = requests.get(
                "https://api.adzuna.com/v1/api/jobs/us/search/1",
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            jobs = []
            for result in response.json().get('results', []):
                jobs.append({
                    'title': result.get('title', 'Unknown'),
                    'company': result.get('company', {}).get('display_name', 'Unknown'),
                    'location': result.get('location', {}).get('display_name', 'Unknown'),
                    'description': result.get('description', ''),
                    'url': result.get('redirect_url', ''),
                    'salary': result.get('salary_min') or 0,
                })
            return jobs
        except requests.RequestException:
            return []

    def fetch_workday_jobs(self):
        return []

    def aggregate_jobs(self, queries=None, locations=None, experience_level=None):
        if not queries:
            queries = ["chemical engineering"]
        if not locations:
            locations = ["boston"]

        # Expand region aliases and deduplicate across all selected locations
        seen_locs = set()
        expanded_locations = []
        for loc in locations:
            for expanded in _REGION_ALIASES.get(loc.lower().strip(), [loc]):
                key = expanded.lower()
                if key not in seen_locs:
                    seen_locs.add(key)
                    expanded_locations.append(expanded)

        # Cap results per task so total stays manageable
        total_tasks = len(queries) * len(expanded_locations)
        per_task = max(3, min(10, 30 // max(total_tasks, 1)))

        def fetch(query, location):
            return self.fetch_adzuna_jobs(
                query=query, location=location,
                max_results=per_task, experience_level=experience_level,
            )

        seen_urls = set()
        jobs = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(fetch, q, loc)
                for q in queries
                for loc in expanded_locations
            ]
            for future in as_completed(futures):
                for job in future.result():
                    if job['url'] not in seen_urls:
                        seen_urls.add(job['url'])
                        jobs.append(job)

        jobs.extend(self.fetch_workday_jobs())
        return jobs
