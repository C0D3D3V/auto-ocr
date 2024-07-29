# Basisimage
FROM jbarlow83/ocrmypdf:latest
#FROM python:3.11-slim

RUN apt update &&  apt install -y tesseract-ocr-deu

# Define build-time arguments for user ID and group ID
ARG PUID=622
ARG PGID=1000
ARG UMASK=022

# Create a user group and a user to run the application
RUN groupadd -g ${PGID} -r auto-ocr && useradd -u ${PUID} -r -g auto-ocr -m -s /bin/bash auto-ocr

# Setze Arbeitsverzeichnis innerhalb des Containers
WORKDIR /app_auto_ocr

# Kopiere den gesamten aktuellen Code in das Arbeitsverzeichnis
COPY . .

# Installiere Abhängigkeiten
RUN pip install .

# Set the umask permanently for the user
RUN echo "umask ${UMASK}" >> /home/auto-ocr/.bashrc

# Change ownership of the application directory
RUN chown -R auto-ocr:auto-ocr /app_auto_ocr
RUN chown -R auto-ocr:auto-ocr /home/auto-ocr/

# Switch to the non-root user
USER auto-ocr

RUN mkdir -p /home/auto-ocr/.local/share/auto-ocr
RUN mkdir -p /home/auto-ocr/.config/auto-ocr


# Startbefehl für das Python-Skript
ENTRYPOINT ["auto-ocr"]
