"""Setup configuration for oig_cloud_mcp package."""

from setuptools import setup, find_packages

setup(
    name="oig_cloud_mcp",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.12",
    install_requires=[
        "mcp>=1.3.2",
        "httpx>=0.27.0",
        "oig-cloud-client @ git+https://github.com/psimsa/oig_cloud_client.git",
    ],
)
