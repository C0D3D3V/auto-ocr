# Basisimage
FROM jbarlow83/ocrmypdf:latest
#FROM python:3.11-slim

#RUN apt update &&  apt install -y tesseract-ocr-deu

# Define build-time arguments for user ID and group ID
ARG PUID=622
ARG PGID=1000

# Create a user group and a user to run the application
# groupadd -g ${PGID} -r auto-ocr
RUN useradd -u ${PUID} -r -g ${PGID} -m -s /bin/bash auto-ocr

# Setze Arbeitsverzeichnis innerhalb des Containers
WORKDIR /app_auto_ocr


# Copy uv from ghcr
COPY --from=ghcr.io/astral-sh/uv:0.5.5 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Installiere Abhängigkeiten
#RUN pip install .
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
COPY . .
# Installing separately from its dependencies allows optimal layer caching 
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen \
        --no-dev

RUN rm -rf /app_auto_ocr/.git 

# Change ownership of the application directory
#RUN chown -R auto-ocr:auto-ocr /app_auto_ocr
#RUN chown -R auto-ocr:auto-ocr /home/auto-ocr/
RUN chown -R auto-ocr:1000 /app_auto_ocr
RUN chown -R auto-ocr:1000 /home/auto-ocr/

# Switch to the non-root user
USER auto-ocr

RUN mkdir -p /home/auto-ocr/.local/share/auto-ocr
RUN mkdir -p /home/auto-ocr/.config/auto-ocr


# Use the custom entrypoint script
ENTRYPOINT ["/app_auto_ocr/docker-entrypoint.sh"]