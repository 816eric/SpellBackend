#!/usr/bin/env python3
"""
Integration Test Runner Script
Executes all integration tests and generates a report

Usage:
    python run_integration_tests.py                    # Run all tests
    python run_integration_tests.py --verbose          # Verbose output
    python run_integration_tests.py --coverage         # Generate coverage report
    python run_integration_tests.py --specific TestUserManagement  # Run specific class
"""

import subprocess
import sys
import json
import time
from datetime import datetime
from pathlib import Path

class TestRunner:
    def __init__(self, verbose=False, coverage=False):
        self.verbose = verbose
        self.coverage = coverage
        self.start_time = None
        self.end_time = None
        self.results = {}

    def run_tests(self, specific_test=None):
        """Run integration tests"""
        self.start_time = datetime.now()

        print(self._header())
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 70)

        try:
            cmd = ["pytest", "tests/test_integration_full_game_flow.py"]

            if self.verbose:
                cmd.append("-v")
                cmd.append("-s")
            else:
                cmd.append("-v")

            if self.coverage:
                cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])

            if specific_test:
                cmd.append(f"-k {specific_test}")

            print(f"Running: {' '.join(cmd)}\n")

            result = subprocess.run(cmd, capture_output=False)

            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()

            self._print_summary(result.returncode, duration)

            return result.returncode == 0

        except Exception as e:
            print(f"ERROR: Failed to run tests: {e}")
            self.end_time = datetime.now()
            return False

    def _header(self):
        return """
╔════════════════════════════════════════════════════════════════════════╗
║           INTEGRATION TEST SUITE - SPELLING GAME APP                   ║
║                                                                        ║
║  Test Coverage:                                                        ║
║  • User Management APIs                                               ║
║  • Points & Rewards System                                            ║
║  • Level System & Progression                                         ║
║  • Leaderboard Features                                               ║
║  • Unlockables & Cosmetics                                            ║
║  • History Tracking                                                    ║
║  • Error Handling & Edge Cases                                        ║
║  • Full Game Flow Integration                                         ║
╚════════════════════════════════════════════════════════════════════════╝
        """

    def _print_summary(self, return_code, duration):
        """Print test execution summary"""
        status = "PASSED" if return_code == 0 else "FAILED"
        status_symbol = "✓" if return_code == 0 else "✗"

        print("\n" + "=" * 70)
        print(f"{status_symbol} Test Execution {status}")
        print("=" * 70)
        print(f"End Time:     {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:     {duration:.2f} seconds")
        print(f"Return Code:  {return_code}")
        print("=" * 70)

        if self.coverage:
            print("\n✓ Coverage report generated in: htmlcov/index.html")

        if return_code == 0:
            print("\n╔════════════════════════════════════════════════════════════════════════╗")
            print("║                    ALL INTEGRATION TESTS PASSED!                      ║")
            print("║                                                                        ║")
            print("║  Next Steps:                                                           ║")
            print("║  1. Review coverage report (if generated)                              ║")
            print("║  2. Run manual testing checklist                                       ║")
            print("║  3. Verify performance benchmarks                                      ║")
            print("║  4. Check data consistency across all screens                          ║")
            print("╚════════════════════════════════════════════════════════════════════════╝")
        else:
            print("\n╔════════════════════════════════════════════════════════════════════════╗")
            print("║                   SOME TESTS FAILED - SEE ABOVE                        ║")
            print("║                                                                        ║")
            print("║  Troubleshooting:                                                      ║")
            print("║  1. Check backend is running: http://localhost:8000/docs               ║")
            print("║  2. Verify database connectivity                                       ║")
            print("║  3. Review error messages above                                        ║")
            print("║  4. Check api_config.dart for correct API URL                          ║")
            print("╚════════════════════════════════════════════════════════════════════════╝")


def print_test_categories():
    """Print available test categories"""
    print("\nAvailable Test Categories:")
    print("  - TestUserManagement")
    print("  - TestPointsSystem")
    print("  - TestLevelSystem")
    print("  - TestLeaderboard")
    print("  - TestUnlockables")
    print("  - TestStreaks")
    print("  - TestHistory")
    print("  - TestIntegrationFullGameFlow")
    print("  - TestErrorHandling")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Run Integration Tests for Spelling Game App'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output with detailed logs'
    )
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Generate coverage report'
    )
    parser.add_argument(
        '--specific', '-s',
        type=str,
        help='Run specific test class or method'
    )
    parser.add_argument(
        '--categories',
        action='store_true',
        help='Show available test categories'
    )

    args = parser.parse_args()

    if args.categories:
        print_test_categories()
        return 0

    runner = TestRunner(verbose=args.verbose, coverage=args.coverage)
    success = runner.run_tests(specific_test=args.specific)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
