#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نشر پکیج nima_persianguard در PyPI / TestPyPI با Twine (تک‌دستوری)."""

import getpass
import glob
import os
import shutil
import subprocess
import sys

PYPI_REPOSITORY = "pypi"
TESTPYPI_REPOSITORY = "testpypi"


def info(msg: str) -> None:
    print(f"ℹ️  {msg}")


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def fail(msg: str) -> None:
    print(f"❌ {msg}")
    sys.exit(1)


def check_python() -> None:
    info("بررسی نسخه پایتون...")
    if sys.version_info < (3, 8):
        fail("پایتون ۳.۸ یا بالاتر لازم است.")
    ok(f"نسخه پایتون: {sys.version.split()[0]}")


def ensure_tool(module: str, package=None) -> None:
    package = package or module
    try:
        __import__(module)
        ok(f"«{package}» موجود است.")
        return
    except ImportError:
        pass
    info(f"«{package}» نصب نیست.")
    ans = input("آیا با pip نصب شود؟ [y/N] ").strip().lower()
    if ans not in ("y", "yes", "بله"):
        fail(f"برای ادامه، «{package}» لازم است. نصب: pip install {package}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    ok(f"«{package}» نصب شد.")


def resolve_credentials() -> tuple[str, str]:
    """خواندن نام کاربری و توکن از محیط، فایل pypirc یا ورودی کاربر."""
    username = os.environ.get("TWINE_USERNAME", "__token__")
    password = os.environ.get("TWINE_PASSWORD")

    if password:
        ok("توکن از متغیر محیطی TWINE_PASSWORD خوانده شد.")
        return username, password

    pypirc = os.path.expanduser("~/.pypirc")
    if os.path.exists(pypirc):
        info(f"فایل {pypirc} پیدا شد؛ Twine اعتبارنامه‌ها را از آن می‌خواند.")
        return username, ""  # خالی ⇒ twine از pypirc می‌خواند

    info("توکن API پیدا نشد (متغیر محیطی یا ~/.pypirc).")
    info("قالب توکن:  نام کاربری: __token__   |   رمز: pypi-...")
    password = getpass.getpass("توکن API را بچسبانید (نمایش داده نمی‌شود): ").strip()
    if not password:
        fail("توکن وارد نشد.")
    return username, password


def build() -> None:
    info("ساخت توزیع‌ها با python -m build ...")
    if os.path.isdir("dist"):
        shutil.rmtree("dist")
    subprocess.check_call([sys.executable, "-m", "build"])
    ok("فایل‌های dist/ ساخته شدند.")


def upload(repository: str, username: str, password: str) -> None:
    info(f"آپلود به {repository} با twine ...")
    env = os.environ.copy()
    env["TWINE_USERNAME"] = username
    if password:
        env["TWINE_PASSWORD"] = password
    repository_url = (
        "https://test.pypi.org/legacy/" if repository == TESTPYPI_REPOSITORY else None
    )
    cmd = [sys.executable, "-m", "twine", "upload", *glob.glob("dist/*"), "--non-interactive"]
    if repository_url:
        cmd += ["--repository-url", repository_url]
    subprocess.check_call(cmd, env=env)
    ok(f"آپلود به {repository} با موفقیت انجام شد.")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="نشر پکیج در PyPI یا TestPyPI")
    parser.add_argument("--test", action="store_true", help="انتشار روی TestPyPI")
    parser.add_argument("--pypi", action="store_true", help="انتشار روی PyPI اصلی")
    args = parser.parse_args()

    if args.test and args.pypi:
        fail("فقط یکی از --test یا --pypi را انتخاب کنید.")
    if args.pypi:
        repository = PYPI_REPOSITORY
    elif args.test:
        repository = TESTPYPI_REPOSITORY
    else:
        ans = input("مقصد؟ [1] TestPyPI  [2] PyPI  (پیش‌فرض: 1): ").strip()
        repository = PYPI_REPOSITORY if ans == "2" else TESTPYPI_REPOSITORY

    print(f"\n🚀 انتشار روی: {repository}\n")
    check_python()
    ensure_tool("build")
    ensure_tool("twine")
    username, password = resolve_credentials()
    build()
    upload(repository, username, password)
    return 0


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nلغو شد.")
        sys.exit(1)
