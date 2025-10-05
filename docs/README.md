# Fifth Symphony Documentation

Comprehensive documentation for the AI-powered distributed automation conductor.

## Quick Links

- [Architecture](ARCHITECTURE.md) - System design and component overview
- [Mobile Access](MOBILE-ACCESS.md) - iOS/iPad SSH access guide
- [Orchestrator Protocol](ORCHESTRATOR-PROTOCOL.md) - Permission system specification

## Documentation Structure

```
docs/
├── README.md                     # This file
├── ARCHITECTURE.md              # System architecture
├── MOBILE-ACCESS.md             # iOS/SSH access guide
├── ORCHESTRATOR-PROTOCOL.md     # Permission protocol spec
└── internal/                    # Private documentation (gitignored)
    ├── DEPLOYMENT.md
    ├── TROUBLESHOOTING.md
    └── *.opml                   # Personal data files
```

## Public vs Private Documentation

### Public Documentation (Committed to Git)
- Architecture and design docs
- User guides and tutorials
- API specifications
- Generic examples with placeholder domains

### Private Documentation (Gitignored)
- Deployment-specific configurations
- Troubleshooting with real domains/paths
- Personal notes and planning
- Operational runbooks with sensitive info

## Contributing to Documentation

When adding documentation:
1. Use generic domains (`yourdomain.com`) in committed docs
2. Place sensitive/personal docs in `internal/`
3. Follow markdown best practices
4. Include practical examples
5. Keep tone conversational and helpful
