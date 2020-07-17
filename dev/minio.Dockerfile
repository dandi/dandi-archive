FROM minio/minio:latest AS builder
# Install MinIO Client (mc)
RUN \
  wget https://dl.min.io/client/mc/release/linux-amd64/mc && \
  chmod +x mc
# Get variable args
# Note, do not set MINIO_BACKEND_DIR to "/data"! This path is defined as a VOLUME by the base
# image, which breaks the ability to write additional data to it during RUN commands within a build.
# See: https://stackoverflow.com/a/55516433
ARG MINIO_BACKEND_DIR
# The config is encryped with the admin credentials MINIO_ACCESS_KEY / MINIO_SECRET_KEY, so
# these must be the same as at runtime
ARG MINIO_ACCESS_KEY
ARG MINIO_SECRET_KEY
ARG MINIO_USER_ACCESS_KEY
ARG MINIO_USER_SECRET_KEY
# * Start the MinIO server in the background
# * Wait for it bo be ready
# * Connect MinIO Client to the running MinIO server
# * Use MinIO Client to add an ordinary user
# * Use MinIO Client to grant the user read-write access to resources on the server
RUN \
  sh -c "/usr/bin/docker-entrypoint.sh minio server ${MINIO_BACKEND_DIR} &" && \
  until nc -z localhost 9000; do sleep 1; done && \
  ./mc config host add minio http://localhost:9000 ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY} && \
  ./mc admin user add minio ${MINIO_USER_ACCESS_KEY} ${MINIO_USER_SECRET_KEY} && \
  ./mc admin policy set minio readwrite user=${MINIO_USER_ACCESS_KEY}

FROM minio/minio:latest
ARG MINIO_BACKEND_DIR
COPY --from=builder ${MINIO_BACKEND_DIR} ${MINIO_BACKEND_DIR}
