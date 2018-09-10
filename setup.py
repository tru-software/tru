#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


setup(
    name="tru",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython"
    ],
    description="Set of libs",
    license="MIT",
    long_description='Set of python libs for django projects',
    url="https://github.com/tru-software/tru",
    project_urls={
        "Documentation": "https://github.com/tru-software/tru",
        "Source Code": "https://github.com/tru-software/tru",
    },

    author="TRU SOFTWARE",
    author_email="at@tru.pl",

    setup_requires=["setuptools_scm"],
    use_scm_version=True,

    install_requires=["django >= 2.1"],
    packages=find_packages()
)
