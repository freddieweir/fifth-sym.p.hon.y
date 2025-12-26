#!/usr/bin/env python3
"""
GitHub Bot Tester - Automated testing framework for GitHub bot responses.

Reusable module for testing any GitHub bot's behavior across repositories.
Part of Fifth Symphony modular component library.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from github import Github, GithubException


@dataclass
class BotTestConfig:
    """Configuration for bot testing."""
    bot_username: str
    repo_name: str
    pr_number: int
    github_token: str
    max_wait_seconds: int = 120
    poll_interval: int = 5
    max_retries: int = 3
    retry_delay: int = 60


@dataclass
class BotResponse:
    """Represents a bot's response to a test."""
    comment_id: int
    body: str
    created_at: datetime
    author: str
    test_passed: bool
    error: str | None = None
    elapsed_seconds: float = 0.0


class ResponseValidator:
    """Validates bot responses against expected criteria."""

    @staticmethod
    def contains_text(response: BotResponse, expected: str) -> bool:
        """Check if response contains expected text."""
        return expected.lower() in response.body.lower()

    @staticmethod
    def no_error_keywords(response: BotResponse) -> bool:
        """Check response doesn't contain error indicators."""
        error_keywords = [
            "error:", "failed:", "exception:",
            "traceback", "could not", "unable to"
        ]
        return not any(kw in response.body.lower() for kw in error_keywords)

    @staticmethod
    def has_success_indicators(response: BotResponse) -> bool:
        """Check response contains success indicators."""
        success_keywords = [
            "complete", "success", "committed", "pushed",
            "changes", "modified", "updated"
        ]
        return any(kw in response.body.lower() for kw in success_keywords)

    @staticmethod
    def custom_validator(response: BotResponse, validator_func: Callable[[str], bool]) -> bool:
        """Run custom validation function."""
        return validator_func(response.body)


class GitHubBotTester:
    """Framework for testing GitHub bot responses."""

    def __init__(self, config: BotTestConfig, logger: logging.Logger | None = None):
        """
        Initialize bot tester.

        Args:
            config: Test configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.github = Github(config.github_token)
        self.repo = self.github.get_repo(config.repo_name)
        self.pr = self.repo.get_pull(config.pr_number)

    def post_test_comment(self, comment_body: str) -> int:
        """
        Post a test comment to the PR.

        Args:
            comment_body: Comment text to post

        Returns:
            Comment ID of posted comment
        """
        try:
            comment = self.pr.create_issue_comment(comment_body)
            self.logger.info(f"Posted test comment: ID {comment.id}")
            return comment.id

        except GithubException as e:
            self.logger.error(f"Failed to post comment: {e}")
            raise

    def wait_for_bot_response(
        self,
        since_comment_id: int,
        timeout_seconds: int | None = None
    ) -> BotResponse | None:
        """
        Wait for bot to respond after a specific comment.

        Args:
            since_comment_id: Comment ID to wait after
            timeout_seconds: Max seconds to wait (uses config default if None)

        Returns:
            BotResponse if found, None if timeout
        """
        timeout = timeout_seconds or self.config.max_wait_seconds
        start_time = time.time()

        self.logger.info(f"Waiting up to {timeout}s for @{self.config.bot_username} response...")

        while (time.time() - start_time) < timeout:
            try:
                comments = self.pr.get_issue_comments()

                # Find bot comments after our test comment
                for comment in comments:
                    if (comment.id > since_comment_id and
                        comment.user.login == self.config.bot_username):

                        elapsed = time.time() - start_time
                        self.logger.info(f"Bot responded after {elapsed:.1f}s")

                        return BotResponse(
                            comment_id=comment.id,
                            body=comment.body,
                            created_at=comment.created_at,
                            author=comment.user.login,
                            test_passed=False,  # Will be set by validation
                            elapsed_seconds=elapsed
                        )

                # Wait before next poll
                time.sleep(self.config.poll_interval)

            except GithubException as e:
                self.logger.warning(f"Error polling comments: {e}")
                time.sleep(self.config.poll_interval)

        self.logger.warning(f"Timeout after {timeout}s waiting for bot response")
        return None

    def validate_response(
        self,
        response: BotResponse,
        validators: list[Callable[[BotResponse], bool]]
    ) -> BotResponse:
        """
        Validate bot response against multiple criteria.

        Args:
            response: Bot response to validate
            validators: List of validation functions

        Returns:
            Updated BotResponse with test_passed set
        """
        all_passed = True
        errors = []

        for validator in validators:
            try:
                if not validator(response):
                    all_passed = False
                    errors.append(f"Validator {validator.__name__} failed")
            except Exception as e:
                all_passed = False
                errors.append(f"Validator {validator.__name__} error: {e}")

        response.test_passed = all_passed
        response.error = "; ".join(errors) if errors else None

        return response

    def delete_comment(self, comment_id: int) -> bool:
        """
        Delete a comment by ID.

        Args:
            comment_id: Comment ID to delete

        Returns:
            True if successful
        """
        try:
            comment = self.pr.get_issue_comment(comment_id)
            comment.delete()
            self.logger.info(f"Deleted comment ID {comment_id}")
            return True

        except GithubException as e:
            self.logger.error(f"Failed to delete comment {comment_id}: {e}")
            return False

    def run_test_with_retry(
        self,
        test_comment: str,
        validators: list[Callable[[BotResponse], bool]],
        auto_delete_on_failure: bool = True
    ) -> BotResponse:
        """
        Run test with automatic retry on failure.

        Args:
            test_comment: Comment to trigger bot
            validators: Validation functions
            auto_delete_on_failure: Delete failed test comments

        Returns:
            Final BotResponse (may be from retry)
        """
        attempt = 0

        while attempt < self.config.max_retries:
            attempt += 1
            self.logger.info(f"Test attempt {attempt}/{self.config.max_retries}")

            # Post test comment
            try:
                comment_id = self.post_test_comment(test_comment)
            except Exception as e:
                self.logger.error(f"Failed to post comment: {e}")
                if attempt < self.config.max_retries:
                    self.logger.info(f"Retrying in {self.config.retry_delay}s...")
                    time.sleep(self.config.retry_delay)
                continue

            # Wait for bot response
            response = self.wait_for_bot_response(comment_id)

            if not response:
                self.logger.warning("No bot response received")
                if auto_delete_on_failure:
                    self.delete_comment(comment_id)

                if attempt < self.config.max_retries:
                    self.logger.info(f"Retrying in {self.config.retry_delay}s...")
                    time.sleep(self.config.retry_delay)
                continue

            # Validate response
            response = self.validate_response(response, validators)

            if response.test_passed:
                self.logger.info("✅ Test passed!")
                return response
            else:
                self.logger.warning(f"❌ Test failed: {response.error}")

                if auto_delete_on_failure:
                    self.delete_comment(comment_id)
                    self.delete_comment(response.comment_id)

                if attempt < self.config.max_retries:
                    self.logger.info(f"Retrying in {self.config.retry_delay}s...")
                    time.sleep(self.config.retry_delay)

        # All retries exhausted
        self.logger.error(f"Test failed after {self.config.max_retries} attempts")
        return response or BotResponse(
            comment_id=0,
            body="",
            created_at=datetime.now(),
            author="",
            test_passed=False,
            error="All retry attempts exhausted"
        )

    def run_simple_test(self, test_comment: str, expect_success: bool = True) -> bool:
        """
        Run a simple test expecting success or failure.

        Args:
            test_comment: Comment to trigger bot
            expect_success: Whether to expect success indicators

        Returns:
            True if test passed
        """
        validators = [
            ResponseValidator.no_error_keywords
        ]

        if expect_success:
            validators.append(ResponseValidator.has_success_indicators)

        response = self.run_test_with_retry(test_comment, validators)
        return response.test_passed


def create_solution_bot_tester(
    repo_name: str,
    pr_number: int,
    github_token: str
) -> GitHubBotTester:
    """
    Factory function for Solution bot tester.

    Args:
        repo_name: Repository in format "owner/repo"
        pr_number: PR number to test on
        github_token: GitHub PAT

    Returns:
        Configured GitHubBotTester instance
    """
    config = BotTestConfig(
        bot_username="pleiades-epsilon-bot",
        repo_name=repo_name,
        pr_number=pr_number,
        github_token=github_token,
        max_wait_seconds=120,
        poll_interval=5,
        max_retries=3,
        retry_delay=60
    )

    return GitHubBotTester(config)
