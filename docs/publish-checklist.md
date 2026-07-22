# Publish Checklist

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Run `seed-demo`.
4. Validate API at `http://localhost:8000/docs`.
5. Validate UI at `http://localhost:8501`.
6. Run `pytest`.
7. Create Git repo, commit, push, publish.
