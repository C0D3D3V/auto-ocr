# Basisimage
FROM jbarlow83/ocrmypdf:latest
#FROM python:3.11-slim

RUN apt update &&  apt install -y tesseract-ocr-deu

# Define build-time arguments for user ID and group ID
ARG PUID=622
ARG PGID=1000

# Create a user group and a user to run the application
# groupadd -g ${PGID} -r auto-ocr
RUN useradd -u ${PUID} -r -g ${PGID} -m -s /bin/bash auto-ocr

# Setze Arbeitsverzeichnis innerhalb des Containers
WORKDIR /app_auto_ocr

# Kopiere den gesamten aktuellen Code in das Arbeitsverzeichnis
COPY . .

# Installiere Abhängigkeiten
RUN pip install .

# Change ownership of the application directory
RUN chown -R auto-ocr:auto-ocr /app_auto_ocr
RUN chown -R auto-ocr:auto-ocr /home/auto-ocr/

# Switch to the non-root user
USER auto-ocr

RUN mkdir -p /home/auto-ocr/.local/share/auto-ocr
RUN mkdir -p /home/auto-ocr/.config/auto-ocr


# Use the custom entrypoint script
ENTRYPOINT ["/app_auto_ocr/docker-entrypoint.sh"]