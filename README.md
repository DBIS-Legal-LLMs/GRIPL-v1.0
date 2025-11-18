# GRIPL — Master’s Thesis

Identifying GDPR-Critical Tasks in Business Processes using Large Language Models

## Overview

This repository contains the source code and research artifacts for the GRIPL master’s thesis. The system consists of a frontend, a backend, and a PostgreSQL database.

In addition to the code, the repository includes:
- The thesis manuscript in `thesis/`
- A labeled dataset of BPMN files in `experiments/labeled-test-dataset/` for reproducing the evaluation
- Experiment configurations and results in `experiments/`

The datasets are provided as CSV exports of the database and can be imported to run the application with the same data used in the thesis.

## Docker Setup

This project can be run in different environments by **composing multiple docker-compose files**.

This project provides:

* `docker-compose.yml` – base services (frontend, backend, Postgres)
* `docker-compose.local.yml` – local testing and running
* `docker-compose.prod.yml` – production style, with Traefik labels and watchtower labels, expects an existing **external** Traefik network (default: `web`)
* `docker-compose.traefik.yml` – optional Traefik container, in case the host does **not** already run Traefik
* `docker-compose.watchtower.yml` – optional Watchtower container

Environment specific values (like hosts, Traefik network name, email, ports) are provided via `.env` files.

---

### 1. Run locally

```bash
cp .env.local.example .env.local

# Fill out .env.local as needed

docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml up -d
```

You will then have:

* frontend: [http://localhost](http://localhost)
* backend: [http://localhost/api](http://localhost/api)
* Postgres: localhost:5432

### 3. Run in production (server already has Traefik + Watchtower)

```bash
cp .env.prod.example .env.prod
# make sure the external Docker network exists:
# docker network create web
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d
```

This will:

* attach all services to your existing `web` network,
* expose the frontend on `${GRIPL_HOST}` and `www.${GRIPL_HOST}`,
* expose the backend on `${GRIPL_HOST}/api`,
* and enable Watchtower updates for all of them.

---

### 4. Run Watchtower and Traefik alongside (server does not have them yet)

If your host does **not** run Watchtower and Traefik yet, add:

```bash
docker compose --env-file .env.prod \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.traefik.yml \
  -f docker-compose.watchtower.yml up -d
```

Watchtower is configured to only update containers that have the label
`com.centurylinklabs.watchtower.enable=true`, which we add in `docker-compose.prod.yml`.

---

## Run locally without Docker for development

See [gripl/gripl-backend/README.md](gripl/gripl-backend/README.md) for instructions on running the backend locally.

See [gripl/gripl-frontend/README.md](gripl/gripl-frontend/README.md) for instructions on running the frontend locally.

Local development requires a running PostgreSQL database. The simplest option is to start a fresh instance with Docker and set the backend’s database connection via environment variables. On startup, the backend will automatically create any missing tables.

Alternatively, you can use `docker-compose.local.yaml` to bring up the entire stack (frontend, backend, PostgreSQL) with Docker as explained above and point your locally running frontend and backend to that database as well.