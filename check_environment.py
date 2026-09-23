#!/usr/bin/env python3
"""
ComicCraft - Environment & Pre-requisites Verification Script
Author: Moulitharan (Deliverables Specialist - Milestone 1 & 2)
Project: ComicCraft - AI Comic Story Creator

Validates:
1. Python Runtime Version (>= 3.10) and Architecture
2. Project Directory Structure and Permissions
3. Required Python Packages & Library Imports
4. Environment Configuration (.env, .env.example, .gitignore)
5. API Key & Model Configuration Readiness
"""

import importlib
import importlib.metadata
import os
import platform
import sys
from pathlib import Path


class Colors:
    """ANSI color escape codes for terminal formatting."""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.RED = ""
        cls.CYAN = ""
        cls.BOLD = ""
        cls.RESET = ""


# Disable colors on Windows cmd if ANSI isn't enabled
if sys.platform == "win32" and "WT_SESSION" not in os.environ and "TERM" not in os.environ:
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        Colors.disable()


class EnvironmentChecker:
    """Performs deep verification of the ComicCraft development environment."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.passed_checks = 0
        self.warn_checks = 0
        self.failed_checks = 0

    def log_pass(self, message: str):
        self.passed_checks += 1
        print(f"  [{Colors.GREEN}PASS{Colors.RESET}] {message}")

    def log_warn(self, message: str):
        self.warn_checks += 1
        print(f"  [{Colors.YELLOW}WARN{Colors.RESET}] {message}")

    def log_fail(self, message: str):
        self.failed_checks += 1
        print(f"  [{Colors.RED}FAIL{Colors.RESET}] {message}")

    def print_header(self, title: str):
        print(f"\n{Colors.BOLD}{Colors.CYAN}--- {title} ---{Colors.RESET}")

    def check_python_runtime(self):
        self.print_header("1. Python Runtime Verification")
        major, minor, micro = sys.version_info[:3]
        py_version_str = f"{major}.{minor}.{micro}"
        is_64bit = sys.maxsize > 2**32
        arch = "64-bit" if is_64bit else "32-bit"

        print(f"  Python executable: {sys.executable}")
        print(f"  Detected version:  {py_version_str} ({arch}) on {platform.system()} {platform.release()}")

        if (major, minor) >= (3, 10):
            self.log_pass(f"Python version {py_version_str} satisfies requirement (>= 3.10)")
        else:
            self.log_fail(f"Python version {py_version_str} is below minimum requirement (>= 3.10)")

        if is_64bit:
            self.log_pass("Python architecture is 64-bit")
        else:
            self.log_warn("32-bit Python detected. 64-bit is strongly recommended for image processing")

    def check_directory_structure(self):
        self.print_header("2. Project Directory Structure Verification")

        required_dirs = [
            ("app", "Application source root"),
            ("app/ai", "AI orchestration package"),
            ("app/services", "Business logic & PDF export service"),
            ("templates", "Jinja2 HTML templates"),
            ("static", "Static assets directory"),
            ("static/css", "Application CSS styling"),
            ("static/panels", "Generated comic panel images storage"),
            ("static/exports", "Generated PDF comic exports storage"),
            ("tests", "Automated pytest test suite"),
        ]

        for rel_path, desc in required_dirs:
            dir_path = self.base_dir / rel_path
            if dir_path.is_dir():
                self.log_pass(f"Directory exists: {rel_path:<16} ({desc})")
            else:
                if rel_path in ("static/panels", "static/exports"):
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        self.log_pass(f"Created missing directory: {rel_path:<16} ({desc})")
                    except Exception as e:
                        self.log_fail(f"Failed to create directory: {rel_path} ({e})")
                else:
                    self.log_fail(f"Missing required directory: {rel_path} ({desc})")

        # Check write permissions in runtime output directories
        output_dirs = ["static/panels", "static/exports"]
        for rel_path in output_dirs:
            dir_path = self.base_dir / rel_path
            test_file = dir_path / ".perm_check.tmp"
            try:
                test_file.write_text("ok", encoding="utf-8")
                test_file.unlink()
                self.log_pass(f"Write permission verified for: {rel_path}")
            except Exception as e:
                self.log_fail(f"Directory not writable: {rel_path} ({e})")

    def check_required_packages(self):
        self.print_header("3. Required Python Packages Verification")

        packages = [
            ("fastapi", "FastAPI Framework", "fastapi"),
            ("uvicorn", "ASGI Server", "uvicorn"),
            ("jinja2", "HTML Templating Engine", "jinja2"),
            ("python-multipart", "Form Data Parser", "multipart"),
            ("google-generativeai", "Google Gemini SDK", "google.generativeai"),
            ("fpdf2", "PDF Generation Engine", "fpdf"),
            ("pillow", "Image Processing (PIL)", "PIL"),
            ("requests", "Synchronous HTTP Client", "requests"),
            ("httpx", "Asynchronous HTTP Client", "httpx"),
            ("python-dotenv", "Environment Variable Loader", "dotenv"),
            ("pydantic", "Data Validation & Schemas", "pydantic"),
            ("pytest", "Testing Framework", "pytest"),
        ]

        for pkg_dist_name, label, import_module_name in packages:
            try:
                mod = importlib.import_module(import_module_name)
                # Try getting installed version from importlib.metadata
                try:
                    version = importlib.metadata.version(pkg_dist_name)
                except Exception:
                    version = getattr(mod, "__version__", "Installed")
                self.log_pass(f"{label:<25} ({pkg_dist_name} v{version})")
            except ImportError as e:
                self.log_fail(f"Missing package: {pkg_dist_name} (Cannot import '{import_module_name}': {e})")

        # Optional / dev test packages
        try:
            import pytest_asyncio
            self.log_pass(f"{'Pytest AsyncIO Extension':<25} (pytest-asyncio Installed)")
        except ImportError:
            self.log_warn(f"{'Pytest AsyncIO Extension':<25} (pytest-asyncio not installed; optional if using anyio)")

    def check_environment_configuration(self):
        self.print_header("4. Configuration Files Verification")

        config_files = [
            ("requirements.txt", True, "Dependency specifications"),
            (".env.example", True, "Template environment file"),
            (".gitignore", True, "Git version control ignore rules"),
            (".env", False, "Active environment secrets file"),
        ]

        for filename, mandatory, desc in config_files:
            file_path = self.base_dir / filename
            if file_path.is_file():
                size = file_path.stat().st_size
                self.log_pass(f"Found {filename:<18} ({desc}, {size} bytes)")
            else:
                if mandatory:
                    self.log_fail(f"Missing mandatory file: {filename} ({desc})")
                else:
                    self.log_warn(
                        f"Optional file missing: {filename} ({desc}). "
                        "Create it by copying .env.example"
                    )

    def check_api_readiness(self):
        self.print_header("5. AI API Keys & Execution Mode")

        # Try to load .env if available
        env_file = self.base_dir / ".env"
        if env_file.is_file():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except Exception:
                pass

        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        hf_key = os.getenv("HF_API_KEY", "").strip()
        dev_mock_raw = os.getenv("DEV_MOCK_AI", "").strip().lower()
        dev_mock_enabled = dev_mock_raw in ("true", "1", "yes")

        # Gemini status
        if gemini_key and gemini_key != "your_gemini_api_key_here":
            masked = gemini_key[:4] + "..." + gemini_key[-4:] if len(gemini_key) > 8 else "***"
            self.log_pass(f"GEMINI_API_KEY is configured ({masked})")
        else:
            self.log_warn("GEMINI_API_KEY is not configured or using placeholder")

        # Hugging Face status
        if hf_key and hf_key != "your_huggingface_api_key_here":
            masked = hf_key[:4] + "..." + hf_key[-4:] if len(hf_key) > 8 else "***"
            self.log_pass(f"HF_API_KEY is configured ({masked})")
        else:
            self.log_warn("HF_API_KEY is not configured or using placeholder")

        # Execution mode
        if dev_mock_enabled or not gemini_key or gemini_key == "your_gemini_api_key_here":
            self.log_pass("Execution Mode: DEV_MOCK_AI active (Safe offline / test / grading mode enabled)")
        else:
            self.log_pass("Execution Mode: Live AI Services active (Gemini Cloud + HF Inference)")

    def run_all(self) -> int:
        print("=" * 70)
        print(f"{Colors.BOLD}ComicCraft Environment & Pre-requisites Verification{Colors.RESET}")
        print(f"Working Directory: {self.base_dir}")
        print("=" * 70)

        self.check_python_runtime()
        self.check_directory_structure()
        self.check_required_packages()
        self.check_environment_configuration()
        self.check_api_readiness()

        print("\n" + "=" * 70)
        print(f"{Colors.BOLD}Verification Summary:{Colors.RESET}")
        print(f"  {Colors.GREEN}Passed:   {self.passed_checks}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Warnings: {self.warn_checks}{Colors.RESET}")
        print(f"  {Colors.RED}Failed:   {self.failed_checks}{Colors.RESET}")
        print("=" * 70)

        if self.failed_checks == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] Environment is fully configured for ComicCraft!{Colors.RESET}\n")
            return 0
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}[FAILURE] Please resolve the failed checks above before proceeding.{Colors.RESET}\n")
            return 1


def main():
    base_dir = Path(__file__).resolve().parent
    checker = EnvironmentChecker(base_dir)
    sys.exit(checker.run_all())


if __name__ == "__main__":
    main()
