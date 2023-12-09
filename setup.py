import setuptools

with open("raveberry/VERSION") as f:
    version = f.read().strip()

with open("README.md") as f:
    long_description = f.read()


def parse_requirements(lines):
    # remove comments, empty lines and arguments
    return list(
        line.split(" ")[0] for line in lines if line and not line.startswith("#")
    )


with open("raveberry/requirements/common.txt") as f:
    run_packages = parse_requirements(f.read().splitlines())
with open("raveberry/requirements/youtube.txt") as f:
    run_packages.extend(parse_requirements(f.read().splitlines()))

with open("raveberry/requirements/install.txt") as f:
    install_packages = parse_requirements(f.read().splitlines())

with open("raveberry/requirements/screenvis.txt") as f:
    screenvis_packages = parse_requirements(f.read().splitlines())

setuptools.setup(
    name="raveberry",
    version=version,
    author="Jasmin Hacker",
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
