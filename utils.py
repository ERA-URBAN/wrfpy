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


def return_validate(date_text):
  '''
  validate date_text and return datetime.datetime object
  '''
  from datetime import datetime
  try:
    date_time = datetime.strptime(date_text, '%Y-%m-%d.%H')
  except ValueError:
    self.logger.error('Incorrect data format, should be YYYY-MM-DD.HH')
    raise ValueError('Incorrect data format, should be YYYY-MM-DD.HH')
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
