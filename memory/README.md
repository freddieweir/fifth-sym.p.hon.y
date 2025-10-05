# Memory Directory

This directory stores orchestrator runtime state, permission history, and session data.

## Structure

```
memory/
├── permissions/          # Permission approval history
│   └── auto-approve-rules.json
├── sessions/            # Active orchestrator sessions
│   └── session-<timestamp>.json
└── logs/                # Activity logs
    ├── orchestrator.log
    └── permissions.log
```

## Security

**CRITICAL**: All files in this directory are gitignored except this README.
- Contains user approval decisions
- May include sensitive operation logs
- Stores auto-approve rules (could reveal security patterns)

## Usage

The orchestrator daemon automatically manages files in this directory:
- Creates session files on startup
- Updates permission rules based on user responses
- Rotates logs automatically (configurable retention)
