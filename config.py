#!/usr/bin/env python

'''
description:    Configuration part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import json
import os
import utils

class config:
  '''
  description
  '''
  def __init__(self):
    home = os.path.expanduser("~")  # get users homedir
    #self.configfile = os.path.join(home, 'wrfpy.config')
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
    keys_dir = ['wrf_dir', 'wrf_run_dir', 'wrfda_dir', 'upp_dir', 'wps_dir'
                  'archive_dir', 'boundary_dir', 'upp_archive_dir', 'work_dir']
    keys_upp = ['upp', 'upp_interval']
    keys_wrfda = ['wrfda', 'wrfda_type']
    keys_general = ['start_date', 'end_date', 'boundary_interval' 'ref_lon'
                    'ref_lat', 'run_hours']
    keys_wps = ['ref_lon', 'ref_lat', 'wps_geog_data_path']
    keys_slurm = ['slurm_real.exe', 'slurm_wrf.exe']

    # create dictionaries
    config_dir = {key: '' for key in keys_dir}
    options_general = {key: '' for key in keys_general}
    options_wrfda = {key: '' for key in keys_wrfda}
    options_upp = {key: '' for key in keys_upp}
    options_wps = {key: '' for key in keys_wps}
    options_slurm = {key: '' for key in keys_slurm}
    # add defaults to wps dictionary
    options_wps['map_proj'] = 'lambert'
    options_wps['truelat1'] = 30.0
    options_wps['truelat2'] = 60.0
    options_wps['stand_lon'] = 4.55
    # combine dictionaries
    config_out = {}
    config_out['filesystem'] = config_dir
    config_out['options_wps'] = options_wps
    config_out['options_upp'] = options_upp
    config_out['options_slurm'] = options_slurm
    config_out['options_wrfda'] = options_wrfda
    config_out['options_general'] = options_general
    # write json config file
    with open(self.configfile, 'w') as outfile:
      json.dump(config_out, outfile,sort_keys=True, indent=4)


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
      - start_date and end_date have a valid format
      - end_date is after start_date
      - boundary_interval is an integer
    '''
    # check if start_date and end_date are in valid format
    start_date = utils.return_validate(
      self.config['options_general']['start_date'])
    end_date = utils.return_validate(
      self.config['options_general']['end_date'])
    # end_date should be after start_date
    if (start_date >= end_date):
      message = ''
      logger.error(message)
      raise IOError(message)
    # boundary interval should be an int number of hours
    assert isinstance(self.config['options_general']['boundary_interval'],
                        int), ('boundary_interval should be given as an ',
                               'integer in %s' %self.configfile)
    # boundary interval should not be larger than time between start_date
    # and end_date
    assert ((self.config['options_general']['boundary_interval']*3600) > (
      end_date - start_date).total_seconds()), (
        'boundary interval is larger than time between start_date and ',
        'end_date')


if __name__=="__main__":
  import sys
  #sys.excepthook = utils.excepthook
  logger = utils.start_logging('test.log')
  cf = config()
  cf._read_json()
  cf._check_config()