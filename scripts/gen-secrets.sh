#!/bin/sh
# Prints a fresh application secret. Paste it into the local environment file.
set -e
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
