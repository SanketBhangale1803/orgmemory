# Slack export: #reddit-operations

Maya 09:12: reddit_service stopped consuming again after the Kafka redeploy. The logs say the broker returned localhost:9092.

Devon 09:15: This matches the previous advertised-listener incident. Containers must receive kafka:9092, not localhost.

Maya 09:18: Checklist before changing anything:

- Inspect reddit_service logs and record the first timeout.
- Compare KAFKA_BOOTSTRAP_SERVERS with the broker's advertised listener.
- Verify Kafka is healthy before restarting the consumer.
- Restart reddit_service only after production approval.
