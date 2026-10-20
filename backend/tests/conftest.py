import os


# Keep the application's unused default engine away from any configured database in tests.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"