from setuptools import setup, find_packages

LONG_DESCRIPTION = open("README.md", "r").read()

REQUIREMENTS = [
    "eth-account>=0.4.0",
    "pytest>=7.2.2",
    "pytest-mock>=3.0.0",
    "requests-mock>=1.6.0",
    "requests>=2.22.0",
    "setuptools>=50.3.2",
    "tox==3.25.0",
    "web3>=6.0.0",
    "dateparser>=1.0.0",
    "nest-asyncio>=1.5.6",
    "pytest-asyncio>=0.21.0",
]

setup(
    name="lighter-v1-python",
    version="1.0.6",
    packages=find_packages(),
    package_data={
        "lighter": [
            "abi/*.json",
        ],
    },
    description="lighter Python rest api and blockchain interactions for Limit Orders",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/elliottech/lighter-v1-python",
    author="Elliot",
    license="Apache 2.0",
    author_email="ahmet@elliot.ai",
    install_requires=REQUIREMENTS,
    keywords="lighter exchange rest api defi ethereum optimism l2 eth",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
