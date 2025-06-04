from setuptools import setup, find_packages

setup(
    name="djroid",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy",
        "psycopg2-binary",
        "python-dotenv",
        "mutagen",
        "click",
    ],
    entry_points={
        "console_scripts": [
            "djroid=djroid.cli:cli",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A DJ's music library management tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/djroid",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
) 