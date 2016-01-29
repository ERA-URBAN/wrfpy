#!/usr/bin/env python

'''
description:    split WRF namelist into first domain / rest
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import f90nml
import copy


class split_namelist:
  def __init__(self):


  def _read_namelist(self)
    '''
    read user supplied namelist
    '''
    self.wrf_nml = f90nml.read(os.path.join(
      self.config['filesystem']['wrf_run_dir'], 'namelist.forecast'))
    # get list of namelist keys
    self.keys = self.wrf_nml.keys()

  def _create_namelist_copyies(self)
    '''
    create two (shallow) copies of the variable containing the namelist
    which will be used to create the output namelists
    '''
    self.wrf_nml_coarse = copy.copy(self.wrf_nml)
    self.wrf_nml_fine = copy.copy(self.wrf_nml)


  def _modify_coarse_namelist(self):
    '''
    modify coarse namelist (resulting namelist contains outer domain only)
    '''
    for section in self.wrf_nml.keys():
      for key in self.wrf_nml[section].keys():
        if isinstance(self.wrf_nml[section][key], list):
          if key not in ['eta_levels']:  # don't modify these keys
            # use only first item from list
            self.wrf_nml_coarse[section][key] = self.wrf_nml[section][key][0]
        elif key == 'max_dom':
          self.wrf_nml[section][key] = 1  # only outer domain
        # else don't modify the key


  def _modify_fine_namelist(self):
    '''
    modify fine namelist (resulting namelist contains all but outer domain)
    '''
    special_cases1 = ['parent_grid_ratio', 'i_parent_start', 'j_parent_start',
                     'parent_time_step_ratio']
    special_cases2 = ['grid_id', 'parent_id']
    for section in self.wrf_nml.keys():
      for key in self.wrf_nml[section].keys():
        if isinstance(self.wrf_nml[section][key], list):
          if key in special_cases1:
            if len(self.wrf_nml][section][key] > 2:
              self.wrf_nml_fine[section][key] = 1 + self.wrf_nml[section][key][2:]
            else:
              self.wrf_nml_fine[section][key] = 1
          elif key in special_cases2:
            self.wrf_nml_fine[section][key] = self.wrf_nml[section][key][:-1]
          elif key not in ['eta_levels']:  # don't modify these keys
            # use only first item from list
            self.wrf_nml_coarse[section][key] = self.wrf_nml[section][key][0]
        elif key=='time_step':
          self.wrf_nml_fine[section][key] = int(
            float(self.wrf_nml[section][key]) / self.wrf_nml['domains']['parent_grid_ratio'][1])
        elif key=='max_dom':
          self.wrf_nml_fine[section][key] = self.wrf_nml[section][key] - 1
