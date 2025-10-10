# Recycled Directory

Temporary storage for old, outdated, or deprecated scripts and files.

## Purpose

This directory serves as a **safe holding area** before permanent deletion:
- Old scripts that have been replaced
- Deprecated code that might be needed for reference
- Experimental code that didn't work out
- Legacy files during refactoring

## Security

**All files in this directory are gitignored** to prevent accidental commits of:
- Old code with security vulnerabilities
- Scripts with hardcoded credentials
- Deprecated patterns that shouldn't be referenced

## Retention Policy

Files in this directory should be:
1. **Reviewed periodically** (monthly recommended)
2. **Moved to documentation** if they have historical value
3. **Permanently deleted** if no longer needed

## Usage

```bash
# Move old script to recycled
mv old_script.sh recycled/

# Review recycled files
ls -la recycled/

# Permanently delete after review period
rm -rf recycled/old_script.sh
```

## Best Practices

- **Add date prefix** to files: `20251004_old_script.sh`
- **Document reason** in commit message: "recycled old_script.sh - replaced by new_script.sh"
- **Set reminder** to review recycled files monthly
- **Never commit** recycled files to git
