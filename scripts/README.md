# Scripts Directory

Organized script management for Fifth Symphony automation conductor.

## Structure

```
scripts/
├── user-scripts/        # User automation scripts (discoverable by GUI/CLI)
│   ├── quick_test.py
│   ├── error_demo.py
│   └── *.py              # Your custom automation scripts
│
├── system/              # System management and orchestrator control
│   ├── install-orchestrator.sh
│   ├── start-daemon.sh
│   ├── stop-daemon.sh
│   └── health-check.sh
│
├── templates/           # Script templates (git-safe, use .template suffix)
│   ├── setup_aliases.sh.template
│   └── lint.sh.template
│
└── utils/               # Utility scripts and helpers
    └── applescripts/    # macOS AppleScript automation
```

## Usage

### User Scripts
Place your automation scripts in `user-scripts/` for automatic discovery:
- CLI: `./run.sh` will list and run scripts
- GUI: `./run_gui.sh` shows visual script cards

### System Scripts
Management scripts for the orchestrator daemon:
```bash
scripts/system/install-orchestrator.sh  # Set up daemon
scripts/system/start-daemon.sh         # Start orchestrator
scripts/system/stop-daemon.sh          # Stop orchestrator
scripts/system/health-check.sh         # Verify system health
```

### Templates
Script templates use `.template` suffix and contain placeholder domains:
- Safe for git commits (no real domains/paths)
- Generate real scripts with `create-scripts.sh`
- Real generated scripts are gitignored

## Security

- **Templates**: Committed to git with generic placeholders
- **Generated scripts**: Gitignored (contain real domains/paths)
- **User scripts**: Review before committing (may contain sensitive data)
