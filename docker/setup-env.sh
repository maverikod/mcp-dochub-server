#!/bin/bash

# Setup environment file for docker-compose
USER_ID=$(id -u)
GROUP_ID=$(id -g)

cat > .env << EOF
# User mapping for container
# Auto-generated on $(date)
USER_ID=${USER_ID}
GROUP_ID=${GROUP_ID}
EOF

echo "✅ Generated .env file with USER_ID=${USER_ID}, GROUP_ID=${GROUP_ID}" 