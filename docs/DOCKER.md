# Docker deployment

The project ships with a non-root Docker image and a Compose deployment. The image contains the application and Python dependencies; the warehouse and generated artifacts live in named volumes so a container rebuild does not erase them.

## Start the demo

```bash
docker compose up --build
```

Open <http://127.0.0.1:8501>. On first start, the entrypoint creates the deterministic synthetic warehouse when `/app/data/warehouse.duckdb` is absent. Subsequent restarts reuse the named `customer360-data` volume.

For a background service:

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f customer360
```

The service health endpoint is `/_stcore/health`. The image and Compose service both define a health check for it.

## Configuration

Copy `.env.example` to `.env` and adjust values before starting. Defaults are suitable for a local demo. Set `C360_PORT=9000` to expose the app on host port 9000; the container still listens on 8501.

Set `C360_BOOTSTRAP_DEMO=0` when supplying a warehouse or importing real data. A real-data manifest still needs `classification: real`, and the app fails closed unless `C360_AUTH_REQUIRED=1` with a configured `C360_USERS_JSON` secret. Do not commit production password hashes or user data in `.env`; inject them through a deployment secret store.

## Import a real snapshot

Keep the service stopped, mount a complete canonical snapshot, and run the pipeline in a one-off container:

```bash
docker compose run --rm \
  -e C360_BOOTSTRAP_DEMO=0 \
  -v "${PWD}/source-snapshot:/app/imports/source-snapshot:ro" \
  customer360 python -m customer360 ingest /app/imports/source-snapshot
```

The pipeline publishes the warehouse atomically inside `/app/data`. Review the Data quality page after restarting the service. The snapshot must follow [the data dictionary](DATA_DICTIONARY.md).

## Build and inspect

```bash
docker build -t customer360:local .
docker run --rm -p 8501:8501 customer360:local
docker image inspect customer360:local --format '{{.Config.User}}'
```

The expected image user is `appuser` (UID 10001). The container does not require Docker socket access, host networking, or privileged mode. Enterprise capacity still requires the benchmark and acceptance plan in [architecture](ARCHITECTURE.md).

