# GitHub Bot Tester Module

Reusable framework for automated testing of GitHub bot responses across any repository.

## Overview

The GitHub Bot Tester provides a complete framework for:
- Posting test comments to PRs
- Waiting for bot responses with timeout
- Validating responses against multiple criteria
- Automatic retry with exponential backoff
- Comment cleanup on failure
- Detailed logging and reporting

## Installation

The module is part of Fifth Symphony and can be imported directly:

```python
from modules.github_bot_tester import (
    GitHubBotTester,
    BotTestConfig,
    ResponseValidator,
    create_solution_bot_tester
)
```

## Quick Start

### Basic Usage

```python
from modules.github_bot_tester import create_solution_bot_tester

# Create tester for Solution bot
tester = create_solution_bot_tester(
    repo_name="freddieweir/ai-bedo",
    pr_number=2,
    github_token="ghp_..."
)

# Run simple test
success = tester.run_simple_test(
    test_comment="@pleiades-epsilon-bot review this code",
    expect_success=True
)

if success:
    print("✅ Test passed!")
else:
    print("❌ Test failed!")
```

### Advanced Usage with Custom Validation

```python
from modules.github_bot_tester import (
    GitHubBotTester,
    BotTestConfig,
    ResponseValidator
)

# Create custom configuration
config = BotTestConfig(
    bot_username="your-bot-name",
    repo_name="owner/repo",
    pr_number=123,
    github_token="ghp_...",
    max_wait_seconds=180,
    poll_interval=10,
    max_retries=5,
    retry_delay=30
)

tester = GitHubBotTester(config)

# Define custom validators
def check_contains_code(response):
    """Check if response contains code blocks."""
    return "```" in response.body

validators = [
    ResponseValidator.no_error_keywords,
    ResponseValidator.has_success_indicators,
    check_contains_code
]

# Run test with retry
response = tester.run_test_with_retry(
    test_comment="@your-bot generate code example",
    validators=validators,
    auto_delete_on_failure=True
)

if response.test_passed:
    print(f"Bot responded in {response.elapsed_seconds:.1f}s")
    print(f"Response: {response.body[:200]}...")
else:
    print(f"Test failed: {response.error}")
```

## API Reference

### BotTestConfig

Configuration dataclass for bot testing.

**Parameters:**
- `bot_username` (str): GitHub username of the bot to test
- `repo_name` (str): Repository in format "owner/repo"
- `pr_number` (int): PR number to test on
- `github_token` (str): GitHub Personal Access Token
- `max_wait_seconds` (int): Maximum seconds to wait for response (default: 120)
- `poll_interval` (int): Seconds between polling attempts (default: 5)
- `max_retries` (int): Maximum retry attempts (default: 3)
- `retry_delay` (int): Seconds to wait between retries (default: 60)

### GitHubBotTester

Main testing framework class.

**Methods:**

#### `post_test_comment(comment_body: str) -> int`
Post a test comment to the PR.

**Returns:** Comment ID

#### `wait_for_bot_response(since_comment_id: int, timeout_seconds: Optional[int]) -> Optional[BotResponse]`
Wait for bot to respond after a specific comment.

**Parameters:**
- `since_comment_id`: Comment ID to wait after
- `timeout_seconds`: Max seconds to wait (uses config default if None)

**Returns:** BotResponse if found, None if timeout

#### `validate_response(response: BotResponse, validators: List[Callable]) -> BotResponse`
Validate bot response against multiple criteria.

**Parameters:**
- `response`: Bot response to validate
- `validators`: List of validation functions

**Returns:** Updated BotResponse with `test_passed` set

#### `delete_comment(comment_id: int) -> bool`
Delete a comment by ID.

**Returns:** True if successful

#### `run_test_with_retry(test_comment: str, validators: List[Callable], auto_delete_on_failure: bool) -> BotResponse`
Run test with automatic retry on failure.

**Parameters:**
- `test_comment`: Comment to trigger bot
- `validators`: Validation functions
- `auto_delete_on_failure`: Delete failed test comments (default: True)

**Returns:** Final BotResponse (may be from retry)

#### `run_simple_test(test_comment: str, expect_success: bool) -> bool`
Run a simple test expecting success or failure.

**Parameters:**
- `test_comment`: Comment to trigger bot
- `expect_success`: Whether to expect success indicators (default: True)

**Returns:** True if test passed

### ResponseValidator

Built-in validation functions.

**Static Methods:**

#### `contains_text(response: BotResponse, expected: str) -> bool`
Check if response contains expected text (case-insensitive).

#### `no_error_keywords(response: BotResponse) -> bool`
Check response doesn't contain error indicators.

Error keywords: `error:`, `failed:`, `exception:`, `traceback`, `could not`, `unable to`

#### `has_success_indicators(response: BotResponse) -> bool`
Check response contains success indicators.

Success keywords: `complete`, `success`, `committed`, `pushed`, `changes`, `modified`, `updated`

#### `custom_validator(response: BotResponse, validator_func: Callable) -> bool`
Run custom validation function.

### BotResponse

Response dataclass.

**Attributes:**
- `comment_id` (int): GitHub comment ID
- `body` (str): Comment body text
- `created_at` (datetime): When comment was created
- `author` (str): Comment author username
- `test_passed` (bool): Whether validation passed
- `error` (Optional[str]): Error message if failed
- `elapsed_seconds` (float): Time from test post to bot response

## Factory Functions

### `create_solution_bot_tester(repo_name: str, pr_number: int, github_token: str) -> GitHubBotTester`

Pre-configured tester for Solution bot (pleiades-epsilon-bot).

**Parameters:**
- `repo_name`: Repository in format "owner/repo"
- `pr_number`: PR number to test on
- `github_token`: GitHub PAT

**Returns:** Configured GitHubBotTester instance with:
- bot_username: "pleiades-epsilon-bot"
- max_wait_seconds: 120
- poll_interval: 5
- max_retries: 3
- retry_delay: 60

## Example Test Suite

```python
#!/usr/bin/env python3
import logging
from modules.github_bot_tester import create_solution_bot_tester, ResponseValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_code_review():
    """Test bot can perform code review."""
    tester = create_solution_bot_tester(
        repo_name="freddieweir/ai-bedo",
        pr_number=2,
        github_token="ghp_..."
    )

    # Custom validator for review
    def check_review_content(response):
        return any(word in response.body.lower() for word in [
            'review', 'analysis', 'recommendation', 'suggestion'
        ])

    validators = [
        ResponseValidator.no_error_keywords,
        ResponseValidator.has_success_indicators,
        check_review_content
    ]

    response = tester.run_test_with_retry(
        test_comment="@pleiades-epsilon-bot review the security of this PR",
        validators=validators
    )

    assert response.test_passed, f"Review test failed: {response.error}"
    logger.info(f"✅ Review completed in {response.elapsed_seconds:.1f}s")

if __name__ == "__main__":
    test_code_review()
```

## Best Practices

### 1. Use Specific Validators

Don't rely only on generic success/error detection. Create validators specific to your use case:

```python
def check_files_modified(response):
    """Ensure bot reported modified files."""
    return "files modified" in response.body.lower()
```

### 2. Set Appropriate Timeouts

Different commands may take different amounts of time:

```python
# Quick commands
config.max_wait_seconds = 60

# Complex analysis
config.max_wait_seconds = 300
```

### 3. Clean Up Failed Tests

Always enable `auto_delete_on_failure` to keep PRs clean:

```python
response = tester.run_test_with_retry(
    test_comment=comment,
    validators=validators,
    auto_delete_on_failure=True  # Cleanup on failure
)
```

### 4. Log Everything

Use Python logging to track test progress:

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot-tests.log')
    ]
)
```

### 5. Handle Token Security

Never hardcode tokens. Use environment variables or secure vaults:

```python
import os
github_token = os.environ.get('GITHUB_TOKEN')

# Or use 1Password CLI
import subprocess
result = subprocess.run(
    ["op", "item", "get", "GitHub Token", "--fields", "label=token", "--reveal"],
    capture_output=True,
    text=True
)
github_token = result.stdout.strip()
```

## Integration with CI/CD

### GitHub Actions

```yaml
name: Test Bot

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  test-bot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install PyGithub

      - name: Run bot tests
        env:
          GITHUB_TOKEN: ${{ secrets.BOT_TEST_TOKEN }}
        run: python scripts/test-solution-bot.py
```

## Troubleshooting

### Bot Not Responding

1. Check bot is running
2. Verify bot has access to repository
3. Check bot's authentication token is valid
4. Increase `max_wait_seconds`

### Validation Failing

1. Print response body to see actual content
2. Check if error keywords are too broad
3. Add custom validators for specific cases
4. Review bot's actual response format

### Timeout Issues

1. Increase `max_wait_seconds` for complex tasks
2. Check bot's processing logs
3. Verify bot can access necessary resources
4. Consider splitting into smaller tests

## License

Part of Fifth Symphony modular component library.
