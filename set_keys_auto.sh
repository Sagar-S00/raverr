#!/bin/bash

# ============================================
# Rave SDK Environment Variables Setup Script (Auto)
# ============================================
# This script automatically sets environment variables from:
# 1. Existing environment variables
# 2. .env file in the current directory
# 3. .env file in the script directory
#
# Usage:
#   source set_keys_auto.sh    # Export to current shell
#   ./set_keys_auto.sh         # Run standalone
# ============================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Loading environment variables...${NC}\n"

# ============================================
# Load from .env file if it exists
# ============================================
ENV_FILES=(
    "$SCRIPT_DIR/.env"
    "$(pwd)/.env"
    "$HOME/.rave_sdk.env"
)

for env_file in "${ENV_FILES[@]}"; do
    if [ -f "$env_file" ]; then
        echo -e "${GREEN}Loading from: $env_file${NC}"
        # Export variables from .env file
        # This handles KEY=value format (no spaces around =)
        set -a
        source "$env_file"
        set +a
        break
    fi
done

# ============================================
# Export all keys (if they exist in environment)
# ============================================

# Cloudflare Workers AI
if [ -n "$CLOUDFLARE_API_KEY" ]; then
    export CLOUDFLARE_API_KEY
    echo -e "${GREEN}✓ CLOUDFLARE_API_KEY loaded${NC}"
fi

if [ -n "$CLOUDFLARE_ACCOUNT_ID" ]; then
    export CLOUDFLARE_ACCOUNT_ID
    echo -e "${GREEN}✓ CLOUDFLARE_ACCOUNT_ID loaded${NC}"
fi

# Perplexity API (optional)
if [ -n "$PERPLEXITY_API_KEY" ]; then
    export PERPLEXITY_API_KEY
    echo -e "${GREEN}✓ PERPLEXITY_API_KEY loaded${NC}"
fi

# YouTube API
if [ -n "$YOUTUBE_API_KEY" ]; then
    export YOUTUBE_API_KEY
    echo -e "${GREEN}✓ YOUTUBE_API_KEY loaded${NC}"
fi

echo -e "\n${GREEN}Environment variables loaded!${NC}\n"

