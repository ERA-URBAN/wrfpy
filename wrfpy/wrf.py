#!/usr/bin/env python

'''
description:    WRF part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

from wrfpy.config import config
from datetime import datetime
import glob
import os
import f90nml
from wrfpy import utils
import subprocess
import shutil


class run_wrf(config):
  '''
  run_wrf is a subclass of config  # TODO: use better names
  '''
  def __init__(self):
    config.__init__(self)
    self.wrf_rundir = self.config['filesystem']['wrf_run_dir']

  def initialize(self, datestart, dateend):
      '''
      initialize new WRF run
      '''
      self.check_wrf_rundir()
      self.cleanup_previous_wrf_run()
      self.prepare_wrf_config(datestart,
                              dateend)

  def check_wrf_rundir(self):
    '''
    check if rundir exists
    if rundir doesn't exist, copy over content
    of self.config['filesystem']['wrf_dir']/run
    '''
    utils._create_directory(self.wrf_rundir)
    # create list of files in self.config['filesystem']['wrf_dir']/run
    files = glob.glob(os.path.join(self.config['filesystem']['wrf_dir'],
                                   'run', '*'))
    for fl in files:
        fname = os.path.basename(fl)
        if (os.path.splitext(fname)[1] == '.exe'):
          # don't copy over the executables
          continue
        shutil.copyfile(fl, os.path.join(self.wrf_rundir, fname))

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
    from datetime import datetime
    # check if both datestart and dateend are a datetime instance
    if not all([ isinstance(dt, datetime) for dt in [datestart, dateend] ]):
      raise TypeError("datestart and dateend must be an instance of datetime")
    # read WRF namelist in WRF work_dir
    wrf_nml = f90nml.read(self.config['options_wrf']['namelist.input'])
    # get number of domains
    ndoms = wrf_nml['domains']['max_dom']
    # check if ndoms is an integer and >0
    if not (isinstance(ndoms, int) and ndoms>0):
      raise ValueError("'domains_max_dom' namelist variable should be an " \
                      "integer>0")
    # define dictionary with time control values
    dict = {'time_control:start_year':datestart.year,
            'time_control:start_month':datestart.month,
            'time_control:start_day':datestart.day,
            'time_control:start_hour':datestart.hour,
            'time_control:end_year':dateend.year,
            'time_control:end_month':dateend.month,
            'time_control:end_day':dateend.day,
            'time_control:end_hour':dateend.hour,
            }
    # loop over dictionary and set start/end date parameters
    for el in dict.keys():
      if type(dict[el])!=list:
        wrf_nml[el.split(':')[0]][el.split(':')[1]] = [dict[el]] * ndoms
      else:
        wrf_nml[el.split(':')[0]][el.split(':')[1]] = dict[el] * ndoms
    # set interval_seconds to total seconds between datestart and dateend
    wrf_nml['time_control']['interval_seconds'] = int(self.config[
      'options_general']['boundary_interval'])
    # calculate datetime.timedelta between datestart and dateend
    td = dateend - datestart
    # set run_days, run_hours, run_minutes, run_seconds
    td_days, td_hours, td_minutes, td_seconds = utils.days_hours_minutes_seconds(td)
    wrf_nml['time_control']['run_days'] = td_days
    wrf_nml['time_control']['run_hours'] = td_hours
    wrf_nml['time_control']['run_minutes'] = td_minutes
    wrf_nml['time_control']['run_seconds'] = td_seconds
    # check if WUR urban config is to be used
    if 'sf_urban_use_wur_config' in wrf_nml['physics']:
      # get start_date from config.json
      start_date = utils.return_validate(
        self.config['options_general']['date_start'])
      # if very first timestep, don't initialize urban parameters from file
      if (wrf_nml['physics']['sf_urban_use_wur_config'] and
          start_date == datestart):
        wrf_nml['physics']['sf_urban_init_from_file'] = False
      else:
        wrf_nml['physics']['sf_urban_init_from_file'] = True
    # write namelist.input
    wrf_nml.write(os.path.join(
      self.config['filesystem']['wrf_run_dir'], 'namelist.input'))


  def run_real(self, j_id=None):
    '''
    run wrf real.exe
    '''
    # check if slurm_real.exe is defined
    if len(self.config['options_slurm']['slurm_real.exe']):
      if j_id:
        mid = "--dependency=afterok:%d" %j_id
        real_command = ['sbatch', mid, self.config['options_slurm']['slurm_real.exe']]
      else:
        real_command = ['sbatch', self.config['options_slurm']['slurm_real.exe']]
      utils.check_file_exists(real_command[-1])
      utils.silentremove(os.path.join(self.wrf_rundir, 'real.exe'))
      os.symlink(os.path.join(self.config['filesystem']['wrf_dir'],'main','real.exe'),
                 os.path.join(self.wrf_rundir, 'real.exe'))
      try:
        res = subprocess.check_output(real_command, cwd=self.wrf_rundir,
                                      stderr=utils.devnull())
        j_id = int(res.split()[-1])  # slurm job-id
      except subprocess.CalledProcessError:
        #logger.error('Real failed %s:' %real_command)
        raise  # re-raise exception
      utils.waitJobToFinish(j_id)
    else:  # run locally
      real_command = os.path.join(self.config['filesystem']['wrf_dir'],
                              'main', 'real.exe')
      utils.check_file_exists(real_command)
      try:
        subprocess.check_call(real_command, cwd=self.wrf_rundir,
                              stdout=utils.devnull(), stderr=utils.devnull())
      except subprocess.CalledProcessError:
        #logger.error('real.exe failed %s:' %real_command)
        raise  # re-raise exception


  def run_wrf(self, j_id=None):
    '''
    run wrf.exe
    '''
    # check if slurm_wrf.exe is defined
    if len(self.config['options_slurm']['slurm_wrf.exe']):
      if j_id:
        mid = "--dependency=afterok:%d" %j_id
        wrf_command = ['sbatch', mid, self.config['options_slurm']['slurm_wrf.exe']]
      else:
        wrf_command = ['sbatch', self.config['options_slurm']['slurm_wrf.exe']]
      utils.check_file_exists(wrf_command[-1])
      utils.silentremove(os.path.join(self.wrf_rundir, 'wrf.exe'))
      os.symlink(os.path.join(self.config['filesystem']['wrf_dir'],'main','wrf.exe'),
                 os.path.join(self.wrf_rundir, 'wrf.exe'))
      try:
        res = subprocess.check_output(wrf_command, cwd=self.wrf_rundir,
                                      stderr=utils.devnull())
        j_id = int(res.split()[-1])  # slurm job-id
      except subprocess.CalledProcessError:
        logger.error('Wrf failed %s:' %wrf_command)
        raise  # re-raise exception
      utils.waitJobToFinish(j_id)
    else:  # run locally
      wrf_command = os.path.join(self.config['filesystem']['wrf_dir'],
                              'main', 'wrf.exe')
      utils.check_file_exists(wrf_command)
      try:
        subprocess.check_call(wrf_command, cwd=self.wrf_rundir,
                              stdout=utils.devnull(), stderr=utils.devnull())
      except subprocess.CalledProcessError:
        logger.error('wrf.exe failed %s:' %wrf_command)
        raise  # re-raise exception

