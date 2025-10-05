#!/bin/bash
# Fifth Symphony - Template-Based Script Security Generator
# 🔒 CRITICAL: This script generates working scripts with real paths/domains from templates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${CYAN}🔐 Fifth Symphony Script Generator${NC}"
    echo -e "${BLUE}======================================${NC}"
}

print_status() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_header

# Load environment variables for real values
if [ -f ".env" ]; then
    print_status "Loading environment variables from .env..."
    set -a  # automatically export all variables
    source .env
    set +a  # stop auto-exporting
    print_success "Environment variables loaded"
else
    print_warning ".env file not found - using defaults"
fi

# Default values (override with .env)
PROJECT_NAME="${PROJECT_NAME:-Fifth Symphony}"
USER_PATH="${USER_PATH:-/Users/yourusername}"
EXTERNAL_VOLUME="${EXTERNAL_VOLUME:-/Volumes/yourvolume}"
COMMUNICATION_PATH="${COMMUNICATION_PATH:-$EXTERNAL_VOLUME/path/to/communication}"

print_status "Configuration:"
echo -e "  Project Name: ${CYAN}$PROJECT_NAME${NC}"
echo -e "  User Path: ${CYAN}$USER_PATH${NC}"
echo -e "  External Volume: ${CYAN}$EXTERNAL_VOLUME${NC}"
echo -e "  Communication Path: ${CYAN}$COMMUNICATION_PATH${NC}"
echo

# Function to generate script from template
generate_script() {
    local template_file="$1"
    local output_file="${template_file%.template}"

    if [ ! -f "$template_file" ]; then
        print_error "Template file not found: $template_file"
        return 1
    fi

    print_status "Generating: $output_file"

    # Use sed to replace template variables
    sed \
        -e "s|{{PROJECT_NAME}}|$PROJECT_NAME|g" \
        -e "s|{{USER_PATH}}|$USER_PATH|g" \
        -e "s|{{EXTERNAL_VOLUME}}|$EXTERNAL_VOLUME|g" \
        -e "s|{{COMMUNICATION_PATH}}|$COMMUNICATION_PATH|g" \
        -e "s|yourdomain\.com|yourrealdomain.com|g" \
        -e "s|/path/to/user|$USER_PATH|g" \
        -e "s|/path/to/external|$EXTERNAL_VOLUME|g" \
        "$template_file" > "$output_file"

    # Make executable (shell scripts should be executable)
    chmod +x "$output_file"

    print_success "Generated: $output_file"
}

# Function to generate config from template
generate_config() {
    local template_file="$1"
    local output_file="${template_file%.template}"

    if [ ! -f "$template_file" ]; then
        print_error "Config template not found: $template_file"
        return 1
    fi

    print_status "Generating config: $output_file"

    # Use envsubst to replace environment variables
    if command -v envsubst >/dev/null 2>&1; then
        envsubst < "$template_file" > "$output_file"
    else
        # Fallback to sed if envsubst not available
        sed \
            -e "s|\${PROJECT_NAME}|$PROJECT_NAME|g" \
            -e "s|\${USER_PATH}|$USER_PATH|g" \
            -e "s|\${EXTERNAL_VOLUME}|$EXTERNAL_VOLUME|g" \
            -e "s|\${COMMUNICATION_PATH}|$COMMUNICATION_PATH|g" \
            "$template_file" > "$output_file"
    fi

    print_success "Generated config: $output_file"
}

# Find and process all template files
print_status "Scanning for template files..."

template_count=0
config_count=0

# Process .sh.template files
for template in $(find . -name "*.sh.template" -type f); do
    generate_script "$template"
    ((template_count++))
done

# Process .yaml.template and .yml.template files
for template in $(find . -name "*.yaml.template" -o -name "*.yml.template" -type f); do
    generate_config "$template"
    ((config_count++))
done

# Process symlink templates
if [ -d "scripts/symlinks" ]; then
    print_status "Processing symlink configurations..."

    # Create real symlinks based on configuration
    if [ -f "scripts/symlinks/.symlink_metadata.json.template" ]; then
        generate_config "scripts/symlinks/.symlink_metadata.json.template"

        # Parse and create symlinks from metadata
        if command -v python3 >/dev/null 2>&1; then
            python3 -c "
import json
import os
import subprocess

try:
    with open('scripts/symlinks/.symlink_metadata.json', 'r') as f:
        metadata = json.load(f)

    for symlink_name, target_path in metadata.get('symlinks', {}).items():
        symlink_path = f'scripts/symlinks/{symlink_name}'

        # Remove existing symlink if it exists
        if os.path.islink(symlink_path):
            os.unlink(symlink_path)

        # Create new symlink
        if os.path.exists(target_path):
            os.symlink(target_path, symlink_path)
            print(f'✓ Created symlink: {symlink_name} -> {target_path}')
        else:
            print(f'⚠ Target not found: {target_path}')

except Exception as e:
    print(f'✗ Error processing symlinks: {e}')
"
        fi
    fi
fi

echo
print_header
print_success "Script generation complete!"
echo -e "  Templates processed: ${CYAN}$template_count${NC} scripts"
echo -e "  Configs processed: ${CYAN}$config_count${NC} files"
echo
print_warning "Generated files are gitignored for security"
print_status "To regenerate, run: ./create-scripts.sh"
echo