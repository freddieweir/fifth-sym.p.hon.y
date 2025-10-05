# 🔒 Template-Based Script Security System

This repository implements a template-based script security system to prevent accidental exposure of domains, paths, and sensitive information in git commits.

## Security Problem Solved

**Before**: Scripts contained hardcoded paths like `/Users/fweir` and project names that could expose personal information.

**After**: Scripts are generated from safe templates that use generic placeholders, with real values stored in gitignored `.env` files.

## How It Works

### Template Files (Safe for Git)
- `*.sh.template` - Shell script templates with `{{PROJECT_NAME}}` placeholders
- `*.yaml.template` - Configuration templates with `${VARIABLE}` environment variables
- All templates use generic domains like `yourdomain.com` and `yourusername`

### Generated Files (Gitignored)
- `*.sh` - Working scripts with real paths and domains
- `*.yaml` - Configuration files with actual values
- `scripts/symlinks/.symlink_metadata.json` - Real symlink paths

### Generator Script
- `create-scripts.sh` - Converts templates to working scripts using `.env` values
- Safe for git - contains no sensitive information itself

## Setup Process

### 1. Initial Setup
```bash
# Copy environment template
cp .env.example .env

# Edit with your actual values
nano .env
```

### 2. Generate Working Scripts
```bash
# Generate all scripts from templates
./create-scripts.sh
```

### 3. Use Generated Scripts
```bash
# Generated scripts work normally
./lint.sh
./setup_aliases.sh

# Symlinks are created automatically
scripts/symlinks/human_log.sh
```

## Environment Variables

Configure these in your `.env` file:

```bash
PROJECT_NAME="Fifth Symphony"
USER_PATH="/Users/yourusername"
EXTERNAL_VOLUME="/Volumes/yourvolume"
COMMUNICATION_PATH="/path/to/communication"
HUMAN_LOG_SCRIPT_PATH="/path/to/human_log.sh"
```

## Git Security

### What Gets Committed
- ✅ `*.template` files (safe - generic placeholders)
- ✅ `create-scripts.sh` (safe - no sensitive data)
- ✅ `.env.example` (safe - example values only)

### What Gets Gitignored
- ❌ `*.sh` (except whitelisted ones)
- ❌ `*.yaml` (except whitelisted config files)
- ❌ `.env` (contains real paths/domains)
- ❌ `scripts/symlinks/.symlink_metadata.json` (contains real paths)

## Template Syntax

### Shell Scripts
```bash
#!/bin/bash
# {{PROJECT_NAME}} - Script Description

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_HOME="{{USER_PATH}}"
```

### Configuration Files
```yaml
project:
  name: "${PROJECT_NAME}"
  path: "${USER_PATH}/projects"
  external: "${EXTERNAL_VOLUME}"
```

## Adding New Templates

### 1. Create Template File
```bash
# Create new script template
cat > new_script.sh.template << 'EOF'
#!/bin/bash
# {{PROJECT_NAME}} - New Script
echo "Running from {{USER_PATH}}"
EOF
```

### 2. Test Template
```bash
# Regenerate all scripts
./create-scripts.sh

# Test generated script
./new_script.sh
```

### 3. Commit Only Template
```bash
# Only commit the template
git add new_script.sh.template
git commit -m "feat: add new script template"

# Generated script is automatically gitignored
```

## Security Benefits

- **Zero Domain Exposure**: No real domains or paths in git history
- **Safe Collaboration**: Templates can be shared without exposing personal info
- **Automatic Generation**: Working scripts created locally as needed
- **Version Control**: Template changes are tracked, but real values aren't
- **Consistency**: Same template generates working scripts for any environment

## Troubleshooting

### Scripts Not Executable
```bash
# Regenerate scripts (fixes permissions)
./create-scripts.sh
```

### Missing .env File
```bash
# Copy and edit template
cp .env.example .env
nano .env
./create-scripts.sh
```

### Symlinks Not Created
```bash
# Check paths in .env file
cat .env
# Update paths and regenerate
./create-scripts.sh
```

### Template Variables Not Replaced
```bash
# Check environment variable names match
grep "{{" *.template  # Should use {{VARIABLE}} syntax
grep "\${" *.template  # Should use ${VARIABLE} syntax
```

## Integration with Development

### Pre-commit Hooks
Templates are compatible with pre-commit hooks since generated files are gitignored.

### CI/CD Systems
CI systems should run `./create-scripts.sh` with appropriate environment variables before using scripts.

### Docker Integration
```dockerfile
# Copy templates and generator
COPY *.template create-scripts.sh ./
COPY .env.docker .env

# Generate working scripts
RUN ./create-scripts.sh
```

## Maintenance

### Regular Tasks
- Keep `.env.example` updated with new variables
- Test template generation after changes: `./create-scripts.sh`
- Verify `.gitignore` patterns are working: `git status`

### When Moving Projects
1. Update `.env` with new paths
2. Run `./create-scripts.sh`
3. No template changes needed

This template system provides robust security for script management while maintaining development convenience and git collaboration safety.