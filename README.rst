WRFpy
=====

What is WRFpy:
~~~~~~~~~~~~~~

WRFpy is a python application that provides an easy way to set up, run,
and monitor (long) Weather Research and Forecasting (WRF) simulations.
It provides a simple user-editable JSON configuration file and
integrates with Cylc to access distributed computing and storage
resources as well as monitoring. Optionally, WRFpy allows for data
assimilation using WRF data assimilation system (WRFDA) and
postprocessing of wrfinput files using the NCEP Unified Post Processing
System (UPP).

Installation
~~~~~~~~~~~~

WRFpy is installable via pip:

::

   pip install git+https://github.com/ERA-URBAN/wrfpy

Usage
~~~~~

WRFpy provides functionality depending on the used command-line
switches:

::

   usage: wrfpy [-h] [--init] [--create] [--basedir BASEDIR] --suitename
                SUITENAME

   WRFpy

   optional arguments:
     -h, --help            show this help message and exit
     --init                Initialize suite (default: False)
     --create              Create suite config (default: False)
     --basedir BASEDIR     basedir in which suites are installed (default:
                           /home/ronald/cylc-suites)
     --suitename SUITENAME
                           name (default: None)

In order to set up a new cylc suite, we first need to initialize one.
This is done using the following command:

::

   wrfpy --init --suitename testsuite

This creates a configuration file (config.json) that needs to be filled
in by the user before continueing. WRFpy points the user to the location
of this file.

After the configuration file has been filled, it is time to create the
actual configuration that will be used by the CYLC workflow engine. To
create the CYLC suite, use the following command:

::

   wrfpy --create --suitename testsuite

The final configuration lives in a file called suite.rc. If you want to
make further (specialized) changes to the workflow by adding/tweaking
steps, you can directly edit the suite.rc file with your favorite
editor.

Now it is time to register the suite with CYLC. CYLC is available at

::

   https://cylc.github.io/cylc/

and has great documentation. From now on you are using CYLC to control
your WRF runs. Please consult the CYLC documentation for the relevant
commands.
