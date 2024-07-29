#!/bin/sh
set -e

# Set the umask based on the UMASK environment variable, default to 0027 if not set
UMASK=${UMASK:-0027}
umask $UMASK

# Execute the auto-ocr command with all provided arguments
exec auto-ocr "$@"