#!/usr/bin/env uv run python3
"""
Error Demonstration Script
Shows how the orchestrator handles various types of errors
"""

import random
import sys
import time


def demonstrate_errors():
    """Demonstrate different types of errors"""
    print("Error Demonstration Script")
    print("This script will intentionally generate various errors")

    error_types = [
        "file_not_found",
        "permission_error",
        "value_error",
        "connection_timeout",
        "memory_warning",
    ]

    selected_error = random.choice(error_types)
    print(f"Simulating: {selected_error}")

    time.sleep(1)

    if selected_error == "file_not_found":
        try:
            with open("nonexistent_file.txt", encoding="utf-8") as f:
                _ = f.read()  # Attempt to read file that doesn't exist
        except FileNotFoundError as e:
            print(f"FileNotFoundError: {e}")
            return 1

    elif selected_error == "permission_error":
        print("PermissionError: Access denied to /restricted/file.txt")
        return 1

    elif selected_error == "value_error":
        try:
            _ = int("not_a_number")  # Attempt to convert invalid string to int
        except ValueError as e:
            print(f"ValueError: {e}")
            return 1

    elif selected_error == "connection_timeout":
        print("ConnectionError: Timeout connecting to remote server")
        return 1

    elif selected_error == "memory_warning":
        print("Warning: High memory usage detected (89% of available RAM)")
        print("Continuing with reduced performance...")
        time.sleep(2)
        print("Operation completed despite memory pressure")
        return 0

    return 0


def main():
    """Main function"""
    return demonstrate_errors()


if __name__ == "__main__":
    sys.exit(main())
