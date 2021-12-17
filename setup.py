import setuptools

with open("backend/VERSION") as f:
    version = f.read().strip()

with open("README.md") as f:
    long_description = f.read()

with open("backend/requirements/common.txt") as f:
    run_packages = f.read().splitlines()
with open("backend/requirements/youtube.txt") as f:
    run_packages.extend(f.read().splitlines())

with open("backend/requirements/install.txt") as f:
    install_packages = f.read().splitlines()

with open("backend/requirements/screenvis.txt") as f:
    screenvis_packages = f.read().splitlines()

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
        "Framework :: Django",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: Python :: 3",
    ],
    packages=["raveberry"],
    include_package_data=True,
    python_requires=">=3.8",
    extras_require={
        "install": install_packages,
        "run": run_packages,
        "screenvis": screenvis_packages,
    },
    scripts=["bin/raveberry"],
)
