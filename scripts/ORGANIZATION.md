# Fifth Symphony - Script Organization

All utility scripts have been organized into logical subdirectories for better maintainability.

## 📁 Directory Structure

```
scripts/
├── cli/              # CLI entry points and interfaces
│   ├── cli.py           - Command-line interface
│   ├── dashboard.py     - Dashboard UI
│   ├── gui.py           - Graphical interface
│   └── gui_orchestrator.py - GUI orchestration logic
│
├── launchers/        # Application launchers
│   ├── run_gui.sh              - Launch GUI
│   ├── run_dashboard.sh        - Launch dashboard
│   ├── monitor.sh              - Basic monitor
│   ├── monitor-clean.sh        - Clean monitor (recommended)
│   ├── monitor-dashboard.sh    - Multi-project monitor
│   └── monitor-interactive.sh  - Interactive monitor with Ollama
│
├── setup/            # Installation and configuration
│   ├── create-scripts.sh    - Generate scripts from templates
│   └── setup_aliases.sh     - Set up shell aliases
│
├── development/      # Development tools
│   ├── lint.sh              - Code quality checks
│   └── test-workflows.sh    - Test GitHub Actions locally
│
├── services/         # Service management
│   ├── start_chat_client.sh - Chat client
│   └── start_chat_server.sh - Chat server
│
├── system/           # System integration
│   └── update-external-repos.sh
│
├── user-scripts/     # User-added scripts
│   ├── quick_test.py
│   ├── error_demo.py
│   └── opml_to_txt.py
│
└── classified/       # Classified content (gitignored)
    └── ghostcore-blueprint/
```

## 🚀 Convenience Launchers (Root Directory)

For quick access, these convenience launchers remain in the root:

- `./run.sh` - Main orchestrator
- `./gui.sh` - Launch GUI → `scripts/launchers/run_gui.sh`
- `./dashboard.sh` - Launch dashboard → `scripts/launchers/run_dashboard.sh`
- `./monitor.sh` - Launch monitor → `scripts/launchers/monitor-clean.sh`

## 📝 Usage Examples

### Running Applications
```bash
# Main orchestrator (from root)
./run.sh

# GUI interface
./gui.sh
# or directly:
./scripts/launchers/run_gui.sh

# Dashboard
./dashboard.sh

# Claude Code monitor (clean version)
./monitor.sh
```

### Development Workflow
```bash
# Test GitHub Actions before PR
./scripts/development/test-workflows.sh quick

# Run linter
./scripts/development/lint.sh

# Set up shell aliases
./scripts/setup/setup_aliases.sh
```

### Service Management
```bash
# Start chat server
./scripts/services/start_chat_server.sh

# Start chat client
./scripts/services/start_chat_client.sh
```

## 🔧 Adding New Scripts

When adding new scripts:

1. **CLI Tools** → `scripts/cli/` - User-facing interfaces
2. **Launchers** → `scripts/launchers/` - Application starters
3. **Setup** → `scripts/setup/` - Installation/config scripts
4. **Development** → `scripts/development/` - Testing/quality tools
5. **Services** → `scripts/services/` - Background services
6. **User Scripts** → `scripts/user-scripts/` - Quick utilities

Keep only **main.py** and **run.sh** in the repository root.

## 📋 Main Entry Points

The repository maintains a clean root with only essential entry points:

- `main.py` - Core orchestrator Python module
- `run.sh` - Primary launcher script
- `gui.sh`, `dashboard.sh`, `monitor.sh` - Convenience launchers (redirects)

All other scripts are organized under `scripts/` for clarity and maintainability.
