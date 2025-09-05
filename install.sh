#!/bin/bash

# Indexer Hook Installation Launcher
# This script checks for uv and runs the Python installer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_SCRIPT="$SCRIPT_DIR/install.py"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌${NC} uv is not installed"
    echo ""
    echo "UV is required to run the indexer hooks."
    echo ""
    echo "Please install UV first:"
    echo "  ${BLUE}curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    echo "  or"
    echo "  ${BLUE}brew install uv${NC} (on macOS)"
    echo ""
    exit 1
fi

# Check if install.py exists
if [ ! -f "$INSTALL_SCRIPT" ]; then
    echo -e "${RED}❌${NC} install.py not found at: $INSTALL_SCRIPT"
    echo "Make sure you're running this from the project root directory"
    exit 1
fi

# Run the Python installer with uv
echo -e "${BLUE}Running Python installer...${NC}"
echo ""
exec uv run "$INSTALL_SCRIPT" "$@"