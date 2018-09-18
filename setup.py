import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "WRFpy",
    version = "0.2.1",
    author = "Ronald van Haren",
    author_email = "r.vanharen@esciencecenter.nl",
    description = ("A python application that provides an easy way to set up,"
                   " run, and monitor (long) Weather Research and Forecasting "
                   " (WRF) simulations."),
    license = "Apache 2.0",
    keywords = "WRF cylc workflow WRFDA",
    url = "https://github.com/ERA-URBAN/wrfpy",
    packages=['wrfpy'],
    include_package_data = True,    # include everything in source control
    package_data={'wrfpy': ['cylc/*.py', 'examples/*']},
    scripts=['wrfpy/scripts/wrfpy'],
    long_description=read('README.rst'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=['numpy', 'Jinja2', 'MarkupSafe', 'PyYAML', 'f90nml'],
)

