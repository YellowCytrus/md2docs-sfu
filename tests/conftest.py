from __future__ import annotations


def pytest_addoption(parser):
    parser.addoption(
        "--update-fixtures",
        action="store_true",
        default=False,
        help="Rewrite profile e2e expected diagnostics and first-page dumps.",
    )
