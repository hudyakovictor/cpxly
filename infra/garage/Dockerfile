# Development ONLY: official Garage binary plus a secret-file startup wrapper.
FROM docker.io/dxflrs/garage:v2.4.1@sha256:9c96caa2612d3411acc5b0e6701fb238dbfba33e533a6d7d3d811a4b12d0d020 AS garage
FROM docker.io/library/python:3.14.0-slim-bookworm@sha256:d13fa0424035d290decef3d575cea23d1b7d5952cdf429df8f5542c71e961576
COPY --from=garage /garage /garage
COPY infra/garage/start.py /opt/garage-start.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Storage daemon runs as root inside the local dev container to initialize its
# own named volumes. No privileged mode, host directories, or Docker socket.
CMD ["python", "/opt/garage-start.py"]
