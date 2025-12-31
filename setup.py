"""
Setup configuration for Simple Uptime Monitor.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="simple-uptime-monitor",
    version="1.0.0",
    author="Simple Uptime Monitor",
    description="A simple, YAML-configured uptime monitoring system with web dashboard",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/simple-uptime-monitor",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "Flask>=3.0.0",
        "Jinja2>=3.1.2",
        "Werkzeug>=3.0.1",
        "SQLAlchemy>=2.0.23",
        "alembic>=1.13.1",
        "requests>=2.31.0",
        "urllib3>=2.1.0",
        "dnspython>=2.4.2",
        "icmplib>=3.0.4",
        "websocket-client>=1.6.4",
        "docker>=7.0.0",
        "discord-webhook>=1.3.0",
        "slack-sdk>=3.26.1",
        "PyYAML>=6.0.1",
        "python-dotenv>=1.0.0",
        "jsonpath-ng>=1.6.0",
        "schedule>=1.2.0",
        "python-dateutil>=2.8.2",
        "pytz>=2023.3",
        "cryptography>=41.0.7",
        "certifi>=2023.11.17",
    ],
    entry_points={
        "console_scripts": [
            "uptime-monitor=uptime_monitor.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Networking :: Monitoring",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="uptime monitoring alerting notifications dashboard",
    project_urls={
        "Documentation": "https://github.com/yourusername/simple-uptime-monitor",
        "Source": "https://github.com/yourusername/simple-uptime-monitor",
        "Bug Reports": "https://github.com/yourusername/simple-uptime-monitor/issues",
    },
)
