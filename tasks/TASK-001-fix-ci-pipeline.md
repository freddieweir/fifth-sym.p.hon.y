# TASK-001: Fix CI Pipeline Issues

**Status:** Todo
**Priority:** High
**Created:** 2025-10-24
**Category:** DevOps, CI/CD

## Context

CI pipeline is currently failing for fifth-symphony. Need to identify issues and fix them to enable automated testing and deployment.

## Objective

Fix GitHub Actions CI pipeline and enable local testing with `act`.

## Requirements

### 1. Diagnose CI Failures
- Check GitHub Actions logs for errors
- Identify failing tests or build steps
- Review Python dependencies and uv setup
- Check environment variable requirements

### 2. Local Testing Setup
- Install and configure `act` for local CI testing
  ```bash
  brew install act
  ```
- Test workflows locally before pushing:
  ```bash
  act -l  # List available workflows
  act pull_request  # Test PR workflow
  ```

### 3. Fix CI Configuration
- Update `.github/workflows/*.yml` files
- Ensure uv is properly installed in CI
- Fix Python version compatibility
- Add proper error handling for missing dependencies

### 4. Test Coverage
- Test AudioTTS module functionality
- Test environment detection (mocked for CI)
- Test ElevenLabs integration (mocked)
- Test voice selection logic

## Technical Tasks

### Phase 1: Diagnosis
- [ ] Review GitHub Actions run logs
- [ ] Identify specific errors
- [ ] Check Python/uv version requirements
- [ ] Check if secrets are properly configured
- [ ] Document findings

### Phase 2: Local Testing
- [ ] Install `act` tool
- [ ] Configure `.actrc` if needed
- [ ] Test workflows locally with mock secrets
- [ ] Fix issues found during local testing

### Phase 3: CI Fixes
- [ ] Update GitHub Actions workflow files
- [ ] Add uv installation step if missing
- [ ] Mock ElevenLabs API calls in tests
- [ ] Add proper environment detection for CI
- [ ] Enable caching for faster builds

### Phase 4: Documentation
- [ ] Document CI setup in README
- [ ] Add testing guide
- [ ] Document local testing with `act`
- [ ] Document mock strategies for API calls

## Testing with act

```bash
# List workflows
act -l

# Run specific workflow
act -j test

# Run with environment variables
act -e <(echo '{"ELEVENLABS_API_KEY":"mock"}')

# Dry run to see what would happen
act -n
```

## CI Workflow Example

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Run tests
        run: uv run pytest tests/
        env:
          ELEVENLABS_API_KEY: mock-key-for-testing
```

## Success Criteria

- [ ] CI pipeline passes on all PRs
- [ ] Local testing works with `act`
- [ ] All tests pass consistently
- [ ] Mock strategy documented
- [ ] Documentation updated

## Related Work

- igris TASK-002: Fix CI Pipeline Issues (similar work)
- OPSEC cleanup (completed 2025-10-24)

## Notes

- ElevenLabs API calls need mocking in CI
- Audio playback tests need to be skipped in headless environment
- Consider using pytest fixtures for mocking
- May need separate test suite for integration vs unit tests
