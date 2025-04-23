"""
Setup script for Google provider modules.
"""

from setuptools import setup, find_namespace_packages

setup(
    name="ultimate-assistant-google-provider",
    version="0.1.0",
    description="Google provider modules for Ultimate Assistant",
    author="Ultimate Assistant Team",
    packages=find_namespace_packages(include=["ultimate_assistant.providers.google*"]),
    install_requires=[
        "google-auth>=2.0.0",
        "google-auth-oauthlib>=0.4.6",
        "google-auth-httplib2>=0.1.0",
        "google-api-python-client>=2.0.0",
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.0",
    ],
    python_requires=">=3.8",
)
