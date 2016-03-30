#!/usr/bin/env python

'''
description:    Configuration part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import json
import os
import utils
import f90nml

class config:
  '''
  description
  '''
  def __init__(self):
    logger = utils.start_logging('test.log')
    home = os.path.expanduser("~")  # get users homedir
    self.configfile = os.path.join(home, 'config.json')
    logger.debug('Checking if configuration file exists: %s' %self.configfile)
    try:
      utils.check_file_exists(self.configfile)
    except IOError:
      # create config file
      self._create_empty_config()
      # TODO: exit and notify user to manually edit config file
    # read json config file
    self._read_json()
    import pdb; pdb.set_trace()
    # check config file for consistenc and errors
    self._check_config()


  def _create_empty_config(self):
    '''
    create empty json config file
    '''
    # define keys
    keys_dir = ['wrf_dir', 'wrf_run_dir', 'wrfda_dir', 'upp_dir', 'wps_dir',
                'archive_dir', 'boundary_dir', 'upp_archive_dir', 'work_dir']
    keys_wrf = ['namelist.input']
    keys_upp = ['upp', 'upp_interval']
    keys_wrfda = ['wrfda', 'wrfda_type']
    keys_general = ['date_start', 'date_end', 'boundary_interval', 'ref_lon',
                    'ref_lat', 'run_hours']
    keys_wps = ['namelist.wps']
    keys_slurm = ['slurm_real.exe', 'slurm_wrf.exe']

    # create dictionaries
    config_dir = {key: '' for key in keys_dir}
    options_general = {key: '' for key in keys_general}
    options_wrfda = {key: '' for key in keys_wrfda}
    options_wrf = {key: '' for key in keys_wrf}
    options_upp = {key: '' for key in keys_upp}
    options_wps = {key: '' for key in keys_wps}
    options_slurm = {key: '' for key in keys_slurm}
    # combine dictionaries
    config_out = {}
    config_out['filesystem'] = config_dir
    config_out['options_wrf'] = options_wrf
    config_out['options_wps'] = options_wps
    config_out['options_upp'] = options_upp
    config_out['options_slurm'] = options_slurm
    config_out['options_wrfda'] = options_wrfda
    config_out['options_general'] = options_general
    # write json config file
    with open(self.configfile, 'w') as outfile:
      json.dump(config_out, outfile,sort_keys=True, indent=4)
    # print message pointing user to edit config file
    self._print_config_message()
    exit()  # exit


  def _print_config_message(self):
    '''
    print message pointing the user to edit the configuration file
    '''
    message = '''>>> A configuration file has been created at %s.
>>> Please edit the configuration file before continuing.''' %self.configfile
    print(message)
    logger.info(message)


  def _read_json(self):
    '''
    read json config file
    '''
    with open(self.configfile, 'r') as infile:
      self.config = json.load(infile)


  def _check_config(self):
    '''
    check configuration file
    '''
    self._check_general()  # check general options
    self._check_wrf()  # check wrf options
    self._check_wps()  # check wps options
    self._check_wrfda()  # check wrfda
    self._check_upp()  # check upp


  def _check_wrfda(self):
    '''
    check if wrfda option is set
    check if wrfda_type is supported
    check wrfda_dir for consistency
    '''
    if self.config['options_wrfda']['wrfda']:
      self._check_wrfda_type()
      self._check_wrfda_dir()


  def _check_wrfda_type(self):
    '''
    check if wrfda_type in json config file is either 3dvar of 4dvar
    '''
    if (not self.config['options_wrfda']['wrfda_type'].lower() in
        ['3dvar', '4dvar']):
      message = ("Only '3dvar' or '4dvar' supported in ",
                 "config['options']['wrfda_type']")
      logger.error(message)
      raise IOError(message)


  def _check_wrda_dir(self):
    '''
    check if the wrfda directory exist
    check if obsproc.exe and da_wrfvar.exe executables exist in the wrfda
    directory
    '''
    # TODO: find out if we can verify that WRFDA dir is 3dvar or 4dvar compiled
    assert os.path.isdir(self.config['filesystem']['wrfda_dir']), (
      'wrfda directory %s not found' %self.config['filesystem']['wrfda_dir'])
    # create list of files to check
    files_to_check = [
      os.path.join(self.config['filesystem']['wrfda_dir'], filename) for
      filename in ['var/obsproc/obsproc.exe', 'var/da/da_wrfvar.exe']]
    # check if all files in the list exist and are readable
    [utils.check_file_exists(filename) for filename in files_to_check]


  def _check_upp(self):
    if self.config['options_upp']['upp']:
      # TODO: check UPP interval
      self._check_upp_dir()


  def _check_upp_dir(self):
    assert os.path.isdir(self.config['filesystem']['upp_dir']), (
      'upp directory %s not found' %self.config['filesystem']['upp_dir'])
    # create list of files to check
    files_to_check = [
      os.path.join(self.config['filesystem']['upp_dir'], filename) for
      filename in ['bin/unipost.exe', 'parm/wrf_cntrl.parm']]
    # check if all files in the list exist and are readable
    [utils.check_file_exists(filename) for filename in files_to_check]


  def _check_general(self):
    '''
    check general options in json config file
      - date_start and date_end have a valid format
      - end_date is after start_date
      - boundary_interval is an integer
    '''
    # check if start_date and end_date are in valid format
    start_date = utils.return_validate(
      self.config['options_general']['date_start'])
    end_date = utils.return_validate(
      self.config['options_general']['date_end'])
    # end_date should be after start_date
    if (start_date >= end_date):
      message = ''
      logger.error(message)
      raise IOError(message)
    # boundary interval should be an int number of hours
    assert isinstance(self.config['options_general']['boundary_interval'],
                        int), ('boundary_interval should be given as an '
                               'integer in %s' %self.configfile)
    # boundary interval should not be larger than time between start_date
    # and end_date
    assert ((self.config['options_general']['boundary_interval']*3600) < (
      end_date - start_date).total_seconds()), (
        'boundary interval is larger than time between start_date and ' 
        'end_date')


  def _check_wps(self):
    '''
    check wps options in json config file
    '''
    # verify that the config option is specified by the user
    assert (len(self.config['options_wps']['namelist.wps']) > 0), (
      'No WPS namelist.wps specified in config file')
    # check if specified namelist.wps exist and are readable
    utils.check_file_exists(self.config['options_wps']['namelist.wps'])
    # check if namelist.wps is in the required format and has all keys needed
    self._check_namelist_wps()


  def _check_namelist_wps(self):
    '''
    check if namelist.wps is in the required format and has all keys needed
    '''
    # verify that example namelist.wps exists and is not removed by user
    basepath = utils.get_script_path()
    self.example_file = os.path.join(basepath, 'examples', 'namelist.wps')
    utils.check_file_exists(self.example_file)
    # load specified namelist
    self.user_nml = f90nml.read(self.config['options_wps']['namelist.wps'])
    # verify that all keys in self.user_nml are also in example namelist
    self._verify_namelist_wps_keys()
    # validate the key information specified
    self._validate_namelist_wps_keys()


  def _verify_namelist_wps_keys(self):
    '''
    verify that all keys in example_nml are also in user_nml
    '''
    # load example namelist.wps
    example_nml = f90nml.read(self.example_file)
    example_keys = example_nml.keys()
    for section in example_nml.keys():
      for key in example_nml[section].keys():
        assert self.user_nml[section][key], (
          'Key not found in user specified namelist: %s'
          %self.config['options_wps']['namelist.wps'])


  def _validate_namelist_wps_keys(self):
    '''
    verify that user specified namelist.wps contains valid information
    for all domains specified by the max_dom key
    '''
    pass


  def _check_wrf(self):
    '''
    check wrf options in json config file
    '''
    # verify that the config option is specified by the user
    assert (len(self.config['options_wrf']['namelist.input']) > 0), (
      'No WRF namelist.input specified in config file')
    # check if specified namelist.wps exist and are readable
    utils.check_file_exists(self.config['options_wrf']['namelist.input'])
    # check if namelist.input is in the required format and has all keys needed
    self._check_namelist_wrf()


  def _check_namelist_wrf(self):
    '''
    check if namelist.input is in the required format and has all keys needed
    '''
    pass


if __name__=="__main__":
  import sys
  #sys.excepthook = utils.excepthook
  cf = config()
  cf._read_json()
  cf._check_config()
