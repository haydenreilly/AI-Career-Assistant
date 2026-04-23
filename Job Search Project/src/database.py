import sqlite3

class JobDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    company TEXT,
                    location TEXT,
                    description TEXT,
                    url TEXT UNIQUE,
                    salary REAL
                )
            ''')

    def insert_jobs(self, jobs):
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                '''INSERT OR REPLACE INTO jobs (title, company, location, description, url, salary)
                   VALUES (:title, :company, :location, :description, :url, :salary)''',
                jobs,
            )

    def get_all_jobs(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT * FROM jobs').fetchall()
        return [dict(row) for row in rows]
