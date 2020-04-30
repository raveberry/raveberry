import setuptools

with open("raveberry/VERSION") as f:
    version = f.read().strip()

with open("raveberry/README.md") as f:
    long_description = f.read()

with open("raveberry/requirements/common.txt") as f:
    required_packages = f.read().splitlines()

with open("raveberry/requirements/screenvis.txt") as f:
    screenvis_packages = [
        line for line in f.read().splitlines() if not line.startswith("-r")
    ]

setuptools.setup(
    name="raveberry",
    version=version,
    author="Jonathan Hacker",
    author_email="raveberry@jhacker.de",
    description="A multi-user music server with a focus on participation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/raveberry/raveberry",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Django :: 2.2",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: Python :: 3",
    ],
    packages=["raveberry"],
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=required_packages,
    extras_require={"screenvis": screenvis_packages},
    scripts=["raveberry/bin/raveberry"],
)
