#!/bin/sh
set -e

USER_NAME=appuser
GROUP_NAME=appgroup

# Create group if it doesn't exist
if ! getent group "$GID" >/dev/null; then
    addgroup --gid "$GID" "$GROUP_NAME"
else
    GROUP_NAME=$(getent group "$GID" | cut -d: -f1)
fi

# Create user if it doesn't exist
if ! getent passwd "$UID" >/dev/null; then
    adduser \
        --disabled-password \
        --gecos "" \
        --uid "$UID" \
        --gid "$GID" \
        "$USER_NAME"
else
    USER_NAME=$(getent passwd "$UID" | cut -d: -f1)
fi

# Fix ownership (only where needed)
chown -R "$UID:$GID" /app

# Drop privileges and run CMD
exec gosu "$UID:$GID" "$@"
