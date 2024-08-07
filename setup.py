from os import path

from setuptools import find_packages, setup

# Get the version from auto_ocr/version.py without importing the package
exec(compile(open("auto_ocr/version.py").read(), "auto_ocr/version.py", "exec"))


def readme():
    this_directory = path.abspath(path.dirname(__file__))
    with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
        return f.read()


setup(
    name="auto-ocr",
    version=__version__,
    description="Tool to automatically OCR PDFs and copy them to a folder",
    long_description=readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/c0d3d3v/auto-ocr",
    author="c0d3d3v",
    author_email="c0d3d3v@mag-keinen-spam.de",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "auto-ocr = auto_ocr.main:main",
        ],
    },
    python_requires=">=3.7",
    install_requires=[
        "colorama>=0.4.6",
        "colorlog>=6.7.0",
        "ocrmypdf>=16.4.2",
        "orjson>=3.10.6",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License (MIT)",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Education",
        "Topic :: Utilities",
    ],
    zip_safe=False,
)
