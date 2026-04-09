# LLM Instructions

These are the instructions for an LLM coding agent.

This project is a Flask application that uses SQLAlchemy for persistence.

Use modern Python syntax with type annotations.

Don't try to generate Alembic migrations by hand. Just let me run the migration generation script myself.

This project is i18n'ed. Use `_(…)` for user facing strings.

If similar functionality already exist, please asks me to generalize it before creating duplicated code.

## Development Environment

This project runs in **Docker** on the local machine. There is no `pip install`, no `uv run`, no direct Python execution.

### DEV environment (local Docker)

Build and restart after code changes:
```bash
docker-compose up --build -d
```

View logs:
```bash
docker-compose logs -f geo-activity-playground
```

Restart without rebuild (config/template changes only):
```bash
docker-compose restart geo-activity-playground
```

The container mounts `./playground/` as `/data` (database, activities, photos, cache).  
Port: `5000`.  
Dev mode flag: `GAP_DEV=1` (Werkzeug + debugger). Default in `docker-compose.yml` is `GAP_DEV=0` (Waitress, 32 threads).

### PROD environment (remote server)

PROD runs on `192.168.1.176` under `gbosch@192.168.1.176:~/docker/geo-activity-playground`.  
Deploy with:
```bash
./deploy-to-prod.sh
```
This rsyncs source + Docker files to the remote. After deploying, SSH in and run `docker-compose up --build -d` there.  
Use the `/home-server-prod` skill to operate PROD.

### Database migrations

Migrations run automatically on container startup via Alembic.  
**Never generate migration files manually** — ask the user to run the migration generation script.

To create a new migration after changing a model:
```bash
uv run alembic revision --autogenerate -m 'Description'
```
(User runs this locally, not Claude.)

