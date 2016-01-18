#!/usr/bin/env python3

'''
description:    Utilities used in wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

def silentremove(filename):
  '''
  Remove a file without raising an error if the file does not exist
  '''
  import os, errno
  try:
    os.remove(filename)
  except OSError as e:
    if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
      raise # re-raise exception if a different error occured


def get_domains():
  '''
  Get domain information from WRF namelist in WRF rundir
  '''
  from namelist import namelist_get
  wrf_namelist = os.path.join(env.RUNDIR, 'namelist.input')
  # get domain information from namelist
  domains = namelist_get(wrf_namelist, 'domains:grid_id')  # use max_dom?
  return domains


def return_validate(date_text, format='%Y-%m-%d_%H'):
  '''
  validate date_text and return datetime.datetime object
  '''
  from datetime import datetime
  try:
    date_time = datetime.strptime(date_text, format)
  except ValueError:
    self.logger.error('Incorrect date format, should be %s', %format)
    raise ValueError('Incorrect date format, should be %s', %format)
  return date_time


def check_file_exists(filename):
  '''
  check if file exists and is readable, else raise IOError
  '''
  try:
      with open(filename) as file:
          pass  # file exists and is readable, nothing else to do
  except IOError as e:
    # file does not exist OR no read permissions
    self.logger.error('Unable to open file: %s', %filename)
    raise  # re-raise exception


def validate_time_wrfout(wrfout, current_time):
  '''
  Validate if current_time is in wrfout file
  '''
  # get list of timesteps in wrfout file (list of datetime objects)
  time_steps = timesteps_wrfout(wrfout)
  # get start date from wrfout filename
  time_string = wrfout[-19:-6]
  start_time = return_validate(time_string)
  # convert current_time to datetime object
  ctime = return_validate(current_time)
  if ctime not in time_steps:
    message = 'Time ' + current_time + 'not found in wrfout file: ' + wrfout
    self.logger.error(message)
    raise ValueError(message)


def timesteps_wrfout(wrfout):
  '''
  return a list of timesteps (as datetime objects) in a wrfout file
  Input variables:
    - wrfout: path to a wrfout file
  '''
  from netCDF4 import Dataset as ncdf
  check_file_exists(wrfout)  # check if wrfout file exists
  # read time information from wrfout file
  ncfile = ncdf(wrfout, format='NETCDF4')
  # minutes since start of simulation, rounded to 1 decimal float
  tvar = [round(nc,0) for nc in ncfile.variables['XTIME'][:]]
  ncfile.close()
  # times in netcdf file
  time_steps = [start_time + timedelta(minutes=step) for step in tvar]
  return time_steps


def datetime_to_string(dtime, format='%Y-%m-%d_%H'):
  '''
  convert datetime object to string. Standard format is 'YYYY-MM-DD_HH'
  Input variables:
    - dtime: datetime object
    - (optional) format: string format to return
  '''
  # check if dtime is of instance datetime
  if not isinstance(dtime, datetime)
    message = 'input variable dtime is not of type datetime'
    self.logger.error(message)
    raise IOError(message)
  # return datetime as a string
  return dtime.strftime(format)


def get_logger():
  pass
