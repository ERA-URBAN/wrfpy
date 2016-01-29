#!/usr/bin/env python

'''
description:    WRF part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

class run_wrf(config):
  '''
  run_wrf is a subclass of config  # TODO: use better names
  '''
  def __init__(self):
    config.__init__(self)
    pass

  def cleanup_previous_wrf_run(self):
    from utils import silentremove
    '''
    cleanup initial/boundary conditions and namelist from previous WRF run
    '''
    # remove initial conditions (wrfinput files)
    for filename in glob.glob(os.path.join(
      self.config['filesystem']['wrf_run_dir'], 'wrfinput_d*')):
      silentremove(filename)
    # remove lateral boundary conditions (wrfbdy_d01)
    silentremove(os.path.join(self.config['filesystem']['wrf_run_dir'],
                              'wrfbdy_d01'))
    silentremove(os.path.join(self.config['filesystem']['wrf_run_dir'],
                              'namelist.input'))


  def prepare_wrf_config(self, datestart, dateend):
    '''
    Copy over default WRF namelist and modify time_control variables
    '''
    from namelist import namelist_set
    from datetime import datetime
    # check if both datestart and dateend are a datetime instance
    if not all([ isinstance(dt, datetime) for dt in [datestart, dateend] ]):
      raise TypeError("datestart and dateend must be an instance of datetime")
    # namelist.input target
    input_namelist = os.path.join(self.config['filesystem']['wrf_run_dir'],
                                  'namelist.input')
    # copy over default namelist
    shutil.copyfile(os.path.join(self.config['filesystem']['wrf_run_dir'],
                                 'namelist.forecast'), input_namelist)
    # get number of domains
    ndoms = namelist_get(input_namelist, 'domains:max_dom')
    # check if ndoms is an integer and >0
    if not (isinstance(ndoms, int) and ndoms>0):
      raise ValueError("'domains_max_dom' namelist variable should be an " \
                      "integer>0")
    # define dictionary with time control values
    dict = { 'time_control:start_year':datestart.year,
            'time_control:start_month':datestart.month,
            'time_control:start_day':datestart.day,
            'time_control:start_hour':datestart.hour,
            'time_control:start_date':datetime.strftime(datestart,
                                                        '%Y-%m-%d_%H:%M:%S')
            'time_control:end_year':dateend.year,
            'time_control:end_month':dateend.month,
            'time_control:end_day':dateend.day,
            'time_control:end_hour':dateend.hour,
            'time_control:end_date':datetime.strftime(dateend,
                                                        '%Y-%m-%d_%H:%M:%S')
            }
    # loop over dictionary and set start/end date parameters
    for el in dict.keys():
      namelist_set(input_namelist, el, [dict[el]]*ndoms)


  def run_real(self):
    '''
    run wrf real.exe
    '''
    pass


  def run_wrf(self):
    '''
    run wrf.exe
    '''
    pass