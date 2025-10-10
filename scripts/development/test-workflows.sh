#!/bin/bash
# Test GitHub Actions workflows locally with act
# Usage: ./test-workflows.sh [workflow-name]

set -e

echo "🎭 Fifth Symphony - GitHub Actions Testing"
echo "=========================================="
echo ""

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo "❌ act not found. Install with: brew install act"
    exit 1
fi

# Default to pull_request event
EVENT="${2:-pull_request}"

case "${1:-list}" in
    list)
        echo "📋 Available workflows:"
        act "$EVENT" --list
        ;;

    lint)
        echo "🔍 Testing Code Quality (lint)..."
        act "$EVENT" --job lint
        ;;

    security)
        echo "🔒 Testing Security Workflows..."
        echo "  - Domain sanitization check"
        act "$EVENT" --job domain-check
        echo "  - Secret scanning (gitleaks)"
        act "$EVENT" --job gitleaks
        echo "  - Template compliance"
        act "$EVENT" --job template-check
        ;;

    quick)
        echo "⚡ Quick Test (template-check only)..."
        act "$EVENT" --job template-check
        ;;

    all)
        echo "🚀 Running ALL PR workflows..."
        echo "⚠️  Warning: This will take several minutes and pull Docker images"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            act "$EVENT"
        else
            echo "Cancelled."
        fi
        ;;

    *)
        echo "Usage: $0 {list|lint|security|quick|all} [event]"
        echo ""
        echo "Commands:"
        echo "  list      - List all workflows"
        echo "  lint      - Test code quality workflow"
        echo "  security  - Test security workflows (domain, secrets, templates)"
        echo "  quick     - Quick test (template compliance only)"
        echo "  all       - Run all PR workflows (slow!)"
        echo ""
        echo "Event (optional): pull_request (default), push, workflow_dispatch"
        exit 1
        ;;
esac

echo ""
echo "✅ Workflow test complete!"
