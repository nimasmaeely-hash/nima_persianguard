# راهنمای انتشار

در PyPI یا TestPyPI از بخش Account Settings → API tokens توکن بسازید. آن را محرمانه نگه دارید؛ هرجا لازم شد مقدار `<YOUR_PYPI_TOKEN>` را با توکن خود جایگزین کنید.

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
TWINE_USERNAME=__token__ TWINE_PASSWORD=<YOUR_PYPI_TOKEN> python -m twine upload --repository testpypi dist/*
```

پس از آزمایش نصب از TestPyPI، انتشار رسمی: `python -m twine upload dist/*`. در Windows، متغیرهای محیطی را با PowerShell تنظیم کنید و توکن را در خط فرمان مشترک یا گیت قرار ندهید.

برای بررسی Zenodo، نسخهٔ منتشرشده، DOI، فایل LICENSE و فرادادهٔ لایسنس MIT را با همین نسخه تطبیق دهید.

© copyright 2026 nima esmaeili
