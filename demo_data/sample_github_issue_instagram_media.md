# Issue #84: instagram_service media disappears after container replacement

instagram_service currently writes downloaded media under `/tmp/media` inside its application container. Files disappear whenever the container is replaced.

Root cause: `/tmp/media` is ephemeral container storage rather than the mounted media volume.

The service contract says downloaded media belongs at `/var/lib/instagram/media`, backed by the `instagram_media` named volume.

Resolution steps:

1. Inspect the active volume mounts before changing configuration.
2. Verify `MEDIA_STORAGE_PATH=/var/lib/instagram/media`.
3. Draft a docker-compose change that mounts `instagram_media:/var/lib/instagram/media`.
4. Deploy the mount change only with production approval.
