from setuptools import setup, find_packages

setup(
    name="mantra-demo",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "sqlalchemy",
        "psycopg2-binary",
        "pytest",
        "httpx",
    ],
) 