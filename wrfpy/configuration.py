#!/usr/bin/env python

'''
description:    Configuration part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

from wrfpy.config import config
from wrfpy import utils
import os
from distutils.dir_util import copy_tree
import pkg_resources


class configuration(config):
    def __init__(self, results):
        global logger
        logger = utils.start_logging(os.path.join(os.path.expanduser("~"),
                                                  'wrfpy.log'))
        if results['init']:
            self._create_directory_structure(results['suitename'],
                                             results['basedir'])
        elif results['create']:
            self._create_cylc_config(results['suitename'],
                                     results['basedir'])

    def _create_directory_structure(self, suitename, basedir=None):
        '''
        Create directory structure for the Cylc configuration
        '''
        # set basedir to users home directory if not supplied
        if not basedir:
            basedir = os.path.join(os.path.expanduser("~"), 'cylc-suites')
        # subdirectories to create
        subdirs = ['bin', 'control', 'doc', 'inc']
        # create subdirectories
        [utils._create_directory(
         os.path.join(basedir, suitename, subdir))
         for subdir in subdirs]
        # copy over helper scripts for cylc
        cylcDir = pkg_resources.resource_filename('wrfpy', 'cylc/')
        targetDir = os.path.join(basedir, suitename, 'bin')
        copy_tree(cylcDir, targetDir)
        # create empty json config file in suite directory
        # this does not overwrite an existing config file
        config.__init__(self, os.path.join(
                                        basedir, suitename, 'config.json'))

    def _create_cylc_config(self, suitename, basedir):
        '''
        Create cylc suite.rc configuration file based on config.json
        '''
        config.__init__(self, os.path.join(
                                        basedir, suitename, 'config.json'))
        self.incr_hour = self.config['options_general']['run_hours']
        self.wps_interval_hours = self.config['options_wps']['run_hours']
        suiterc = self._header()
        suiterc += self._scheduling()
        suiterc += self._runtime()
        suiterc += self._visualization()
        self._write(suiterc, os.path.join(basedir, suitename, 'suite.rc'))

    def _header(self):
        '''
        define suite.rc header information
        '''
        start_time = utils.datetime_to_string(
            utils.return_validate(self.config[
                                  'options_general']['date_start']),
            format='%Y%m%dT%H')
        end_time = utils.datetime_to_string(
            utils.return_validate(self.config['options_general']['date_end']),
            format='%Y%m%dT%H')
        # define template
        template = """#!Jinja2

{{% set START = "{start_time}" %}}
{{% set STOP  = "{end_time}" %}}

"""
        # context variables in template
        context = {
            "start_time": start_time,
            "end_time": end_time
            }
        return template.format(**context)

    def _scheduling(self):
        '''
        define suite.rc scheduling information
        '''
        # get start_hour and increment time from config.json
        start_hour = str(
            utils.return_validate
            (self.config['options_general']['date_start']).hour).zfill(2)
        # check if we need to add upp
        try:
            if self.config['options_upp']['upp']:
                uppBlock = "=> upp"
            else:
                uppBlock = ""
        except KeyError:
            uppBlock = ""
        # define template
        template = """[scheduling]
    initial cycle point = {{{{ START }}}}
    final cycle point   = {{{{ STOP }}}}
    [[dependencies]]
        # Initial cycle point
        [[[R1]]]
            graph = \"\"\"
                wrf_init => wps => wrf_real => wrfda => wrf_run {upp}
                obsproc_init => obsproc_run => wrfda
            \"\"\"
        # Repeat every {incr_hour} hours, starting {incr_hour} hours
        # after initial cylce point
        [[[+PT{incr_hour}H/PT{incr_hour}H]]]
            graph = \"\"\"
                wrf_run[-PT{incr_hour}H] => wrf_init => wrf_real => wrfda => wrf_run {upp}
                wrfda[-PT{incr_hour}H] => obsproc_init => obsproc_run => wrfda
            \"\"\"
        # Repeat every {wps_incr_hour} hours, starting {wps_incr_hour} hours
        # after initial cylce point
        [[[+PT{wps_incr_hour}H/PT{wps_incr_hour}H]]]
            graph = \"\"\"
                wps[-PT{wps_incr_hour}H] => wps => wrf_init
            \"\"\"
"""
        # context variables in template
        context = {
            "start_hour": start_hour,
            "incr_hour": self.incr_hour,
            "wps_incr_hour": self.wps_interval_hours,
            "upp": uppBlock
            }
        return template.format(**context)

    def _runtime(self):
        '''
        define suite.rc runtime information
        '''
        return (self._runtime_base() + self._runtime_init_wrf() +
                self._runtime_init_obsproc() + self._runtime_real() +
                self._runtime_wrf() + self._runtime_obsproc() +
                self._runtime_wrfda() + self._runtime_upp() +
                self._runtime_wps())

    def _runtime_base(self):
        '''
        define suite.rc runtime information: base
        '''
        # define template
        template = """[runtime]
    [[root]] # suite defaults
        [[[job submission]]]
            method = background
"""
        # context variables in template
        context = {}
        return template.format(**context)

    def _runtime_init_wrf(self):
        '''
        define suite.rc runtime information: init
        '''
        init_command = "wrf_init.py $CYLC_TASK_CYCLE_POINT {incr_hour}"
        init_context = {
            "incr_hour": self.incr_hour
            }
        init = init_command.format(**init_context)
        # define template
        template = """
    [[wrf_init]]
        script = \"\"\"
{wrf_init}
\"\"\"
        [[[job submission]]]
            method = {method}
        [[[directives]]]
            {directives}"""
        # context variables in template
        context = {
            "wrf_init": init,
            "method": "background",
            "directives": ""
            }
        return template.format(**context)

    def _runtime_init_obsproc(self):
        '''
        define suite.rc runtime information: init
        '''
        init = "wrfda_obsproc_init.py $CYLC_TASK_CYCLE_POINT"
        # define template
        template = """
    [[obsproc_init]]
        script = \"\"\"
{obsproc_init}
\"\"\"
        [[[job submission]]]
            method = {method}
        [[[directives]]]
            {directives}"""
        # context variables in template
        context = {
            "obsproc_init":  init,
            "method": "background",
            "directives": ""
            }
        return template.format(**context)

    def _runtime_real(self):
        '''
        define suite.rc runtime information: real.exe
        '''
        wrf_real = "run_real.py"
        # define template
        template = """
    [[wrf_real]]
        script = \"\"\"
{wrf_real}
\"\"\"
        [[[job submission]]]
            method = {method}
        [[[directives]]]
            {directives}"""
        # context variables in template
        context = {
            "wrf_real": wrf_real,
            "method": "background",
            "directives": ""
            }
        return template.format(**context)


    def _runtime_wrf(self):
        '''
        define suite.rc runtime information: wrf.exe
        '''
        wrf_run = "run_wrf.py"
        # define template
        template = """
    [[wrf_run]]
        script = \"\"\"
{wrf_run}
\"\"\"
        [[[job submission]]]
            method = {method}
        [[[directives]]]
            {directives}"""
        # context variables in template
        context = {
            "wrf_run": wrf_run,
            "method": "background",
            "directives": ""
            }
        return template.format(**context)

    def _runtime_obsproc(self):
        '''
        define suite.rc runtime information: obsproc.exe
        '''
        obsproc_run = "wrfda_obsproc_run.py $CYLC_TASK_CYCLE_POINT"
        # define template
        template = """
    [[obsproc_run]]
        script = \"\"\"
{obsproc_run}
\"\"\"
        [[[job submission]]]
            method = {method}
        [[[directives]]]
            {directives}"""
        # context variables in template
        context = {
            "obsproc_run":  obsproc_run,
            "method": "background",
            "directives": ""
            }
        return template.format(**context)

    def _runtime_wrfda(self):
        '''
        define suite.rc runtime information: wrfda
        '''
        wrfda_run = "wrfda_run.py $CYLC_TASK_CYCLE_POINT"
        # define template
        template = """
    [[wrfda]]
        script = \"\"\"
{wrfda_run}
\"\"\"
        [[[job submission]]]
            method = {method}
        [[[directives]]]
            {directives}"""
        # context variables in template
        context = {
            "wrfda_run":  wrfda_run,
            "method": "background",
            "directives": ""
            }
        return template.format(**context)

    def _runtime_upp(self):
        '''
        define suite.rc runtime information: wrfda
        '''
        # define template
        template = """
    [[upp]]
        script = \"\"\"
{command}
\"\"\"
        [[[job submission]]]
            method = {method}
        [[[directives]]]
            {directives}
"""
        command = "upp.py $CYLC_TASK_CYCLE_POINT"
        context = {
            "command": command,
            "method": "background",
            "directives": ""
            }
        return template.format(**context)

    def _runtime_wps(self):
        '''
        define suite.rc runtime information: wrfda
        '''
        # define template
        template = """
    [[wps]]
        pre-script = \"\"\"
{pre_command}
\"\"\"
        script = \"\"\"
{command}
\"\"\"
        post-script = \"\"\"
{post_command}
\"\"\"
        [[[environment]]]
            WORKDIR = {wps_workdir}
            CYLC_TASK_WORK_DIR = $WORKDIR
        [[[job submission]]]
            method = {method}
        [[[directives]]]
            {directives}
"""
        pre_command = "wps_init.py $CYLC_TASK_CYCLE_POINT {wps_run_hours}"
        pre_command_context = {
            "wps_run_hours": self.wps_interval_hours,
        }
        command = "wps_run.py"
        command_context = {
            "wps_dir": self.config['filesystem']['wps_dir']
        }
        post_command = "wps_post.py"
        context = {
            "wps_workdir": os.path.join(self.config['filesystem']['work_dir'],
                                        'wps'),
            "pre_command": pre_command.format(**pre_command_context),
            "command": command.format(**command_context),
            "post_command": post_command,
            "method": "background",
            "directives": ""
            }
        return template.format(**context)

    def _visualization(self):
        '''
        define suite.rc visualization information
        '''
        # define template
        template = """
[visualization]
    initial cycle point = {{ START }}
    final cycle point   = {{ STOP }}
    default node attributes = "style=filled", "fillcolor=grey"
"""
        return template

    def _write(self, suiterc, filename):
        '''
        write cylc suite.rc config to file
        '''
        # create the itag file and write content to it based on the template
        try:
            with open(filename, 'w') as itag:
                itag.write(suiterc)
        except IOError:
            raise  # re-raise exception
