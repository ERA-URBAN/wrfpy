import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "WRFpy",
    version = "0.0.1",
    author = "Ronald van Haren",
    author_email = "r.vanharen@esciencecenter.nl",
    description = ("A python application that provides an easy way to set up,"
                   " run, and monitor (long) Weather Research and Forecasting "
                   " (WRF) simulations."),
    license = "Apache 2.0",
    keywords = "WRF cylc workflow WRFDA",
    url = "https://github.com/rvanharen/wrfpy",
    packages=['wrfpy'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved ::Apache Software License",
    ],
)

