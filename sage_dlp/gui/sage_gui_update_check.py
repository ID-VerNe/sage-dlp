# -*- coding: utf-8 -*-
"""
Background update-check thread for SageDLP GUI.

`UpdateCheckThread` queries PyPI and GitHub (in parallel, or GitHub beta-first
when beta checks are enabled) and emits `update_available` when a newer
version than the running one is found.
"""

from concurrent.futures import ThreadPoolExecutor

import requests
from packaging import version
from PySide6.QtCore import QThread, Signal

from ..utils.sage_config_manager import ConfigManager


class UpdateCheckThread(QThread):
    """Background thread for checking application updates with parallel network requests."""

    update_available = Signal(str, str, str)  # version, url, changelog

    # Reduced timeouts for faster failure detection
    PYPI_TIMEOUT = 8
    GITHUB_TIMEOUT = 5

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version

    def _fetch_pypi_version(self) -> tuple[str | None, str | None]:
        """Fetch latest version from PyPI. Returns (version, error)."""
        try:
            response = requests.get(
                "https://pypi.org/pypi/sage-dlp/json",
                timeout=self.PYPI_TIMEOUT,
            )
            response.raise_for_status()
            pypi_data = response.json()
            return pypi_data["info"]["version"], None
        except requests.Timeout:
            return None, "PyPI request timed out"
        except requests.RequestException as e:
            return None, f"PyPI request failed: {e}"
        except Exception as e:
            return None, f"Error parsing PyPI response: {e}"

    def _fetch_github_changelog(self) -> str:
        """Fetch changelog from GitHub. Returns changelog text or fallback message."""
        fallback = "View the full changelog on the [GitHub Releases](https://github.com/oop7/SageDLP/releases) page."
        try:
            response = requests.get(
                "https://api.github.com/repos/oop7/SageDLP/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=self.GITHUB_TIMEOUT,
            )
            if response.status_code == 200:
                gh_data = response.json()
                return gh_data.get("body", fallback) or fallback
            return fallback
        except Exception:
            # Silently fallback if GitHub API fails (rate limiting, network issues, etc.)
            return fallback

    def _fetch_github_beta_version(self) -> tuple[str | None, str | None, str | None]:
        """Fetch latest version code from GitHub releases (including betas). Returns (version, tag, changelog)."""
        try:
            response = requests.get(
                "https://api.github.com/repos/oop7/SageDLP/releases",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=self.GITHUB_TIMEOUT,
            )
            if response.status_code != 200:
                return None, None, None

            releases = response.json()
            if not releases:
                return None, None, None

            latest_release = None
            highest_ver = version.parse("0.0.0")

            for rel in releases:
                tag = rel.get("tag_name", "")
                ver_str = tag.lstrip("v")
                try:
                    v = version.parse(ver_str)
                    if v > highest_ver:
                        highest_ver = v
                        latest_release = rel
                except Exception:
                    continue

            if latest_release:
                return str(highest_ver), latest_release.get("tag_name"), latest_release.get("body")
            return None, None, None

        except Exception:
            return None, None, None

    def run(self):
        """Check for updates using parallel network requests for better performance."""
        try:
            # Check for beta updates if enabled
            check_beta = ConfigManager.get("check_beta_updates")

            if check_beta:
                latest_ver_str, tag, changelog = self._fetch_github_beta_version()

                if latest_ver_str and version.parse(latest_ver_str) > version.parse(self.current_version):
                    release_url = f"https://github.com/oop7/SageDLP/releases/tag/{tag}"
                    if not changelog:
                        changelog = "View the full changelog on GitHub."
                    self.update_available.emit(latest_ver_str, release_url, changelog)
                # Return if beta check completes (whether update found or not),
                # effectively skipping PyPI check if beta is enabled.
                # This ensures we don't downgrade or conflict.
                return

            # Use ThreadPoolExecutor to make both requests in parallel
            # This reduces total wait time from potentially 15s to ~8s max
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both tasks
                pypi_future = executor.submit(self._fetch_pypi_version)
                github_future = executor.submit(self._fetch_github_changelog)

                # Get PyPI result (this is required)
                latest_version, error = pypi_future.result()

                if error:
                    return

                if not latest_version:
                    return

                # Compare versions
                if version.parse(latest_version) > version.parse(self.current_version):
                    release_url = "https://github.com/oop7/SageDLP/releases/latest"

                    # Get GitHub changelog (may already be complete due to parallel execution)
                    changelog = github_future.result()

                    self.update_available.emit(latest_version, release_url, changelog)

        except Exception:
            pass
