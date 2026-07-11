# Incident: Kafka connectivity after redeploy

On June 12, reddit_service consumers began timing out immediately after the broker container was redeployed.

Observed error: `KafkaTimeoutError: Failed to update metadata after 60.0 secs` from reddit_service.

Root cause: the broker advertised `localhost:9092` while containers connected through the Docker network at `kafka:9092`. The advertised listener mismatch returned an unreachable address to reddit_service.

Recovery procedure:

1. Inspect the latest consumer logs with `docker logs --tail=200 reddit_service`.
2. Verify the broker listener and advertised listener values in docker-compose.yml.
3. Check broker health with `docker compose ps kafka`.
4. After validating configuration, restart reddit_service with `docker restart reddit_service`.

Restarting a production consumer requires approval from the on-call incident commander.
