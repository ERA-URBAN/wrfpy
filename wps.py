#!/usr/bin/env python3

'''
description:    WRF Preprocessing System (WPS) part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import utils
import glob
import subprocess
import os
import errno
import f90nml

class wps(config):
  '''
  description
  '''
  def __init__(self, boundary_dir):
    config.__init__(self)  # load config
    # define and create wps working directory
    self.wps_workdir = os.path.join(self.config['filesystem']['work_dir'], wps)
    utils._create_directory(self.wps_workdir)
    '''boundary_dir as an argument so we switch between boundary_dir and
       upp_archive_dir defined in config module'''
    self.boundary_dir = boundary_dir

  def clean_boundaries_wps():
  '''
  clean old leftover boundary files in WPS directory
  '''
  # create list of files to remove
  files = [ os.path.join(self.config['filesystem']['wps_dir'], ext)
           for ext in ['GRIBFILE.*', 'FILE:', 'PFILE:', 'PRES:'] ]
  # remove files silently
  [ silentremove(filename) for filename in files ]


  def prepare_namelist(datestart, dateend):
  '''
  prepare wps namelist
  '''
  # copy namelist over to WPS work_dir
  shutil.copyfile(os.path.join(self.config['options_wps']['namelist.wps'],
    self.config['filesystem']['work_dir'], 'wps', 'namelist.wps'))
  # read WPS namelist in WPS work_dir
  wps_nml = f90nml.read(self.config['filesystem']['work_dir'], 'wps',
                        'namelist.wps')
  # get numer of domains
  ndoms = wps_nml['share']['max_dom']
  # check if ndoms is an integer and >0
  if not (isinstance(ndoms, int) and ndoms>0):
    raise ValueError("'domains_max_dom' namelist variable should be an " \
                     "integer>0")
  # check if both datestart and dateend are a datetime instance
  if not all([ isinstance(dt, datetime) for dt in [datestart, dateend] ]):
    raise TypeError("datestart and dateend must be an instance of datetime")
  # set new datestart and dateend
  wps_nml['share']['start_date'] = [datetime.strftime(datestart,
                                                        '%Y-%m-%d_%H:%M:%S')] * ndoms
  wps_nml['share']['end_date'] = [datetime.strftime(datestart,
                                                        '%Y-%m-%d_%H:%M:%S')] * ndoms


  def link_boundary_files():
    '''
    link boundary grib files to wps work directory with the required naming
    '''
    # get list of files to link
    filelist = glob.glob(self.boundary_dir)
    if len(filelist) == 0:
      message = 'linking boundary files failed, no files found to link'
      logger.error(message)
      raise IOError(message)
    # get list of filename extensions to use for destination link
    linkext = self._get_ext_list(len(filelist))
    # link grib files
    [os.symlink(filelist[idx], os.path.join(
      self.wps_workdir, 'GRIBFILE' + linkext[idx])) for idx in range(len(filelist))]


  def _get_ext_list(num):
    '''
    create list of filename extensions for num number of files
    Extensions have the form: AAA, AAB, AAC... ABA, ABB...,BAA, BAB...
    '''
    from string import ascii_uppercase
    # create list of uppercase letters used linkname extension
    ext = [ascii_uppercase[idx] for idx in range(0,len(ascii_uppercase))]
    i1, i2, i3 = 0, 0, 0
    for range(num):  # loop over number of files
      # append extension to list (or create list for first iteration)
      try:
        list_ext = list_ext.append([ext[i1] + ext[i2] + ext[i3]])
      except NameError:
        list_ext = [ext[i1] + ext[i2] + ext[i3]]
      i1 += 1  # increment i1
      if i1 >= len(ascii_uppercase):
        i1 = 1
        i2 += 1  # increment i2
        if i2 >= len(ascii_uppercase):
          i2 = 1
          i3 += 1  # increment i3
          if i3 >= len(ascii_uppercase):
            message = 'Too many files to link'
            logger.error(message)
            raise IOError(message)


  def _run_geogrid():
    '''
    run geogrid.exe (run it on the login node for now)
    '''
    geogrid_command = os.path.join(self.config['filesystem']['wps_dir'],
                                   'geogrid', 'gegrid.exe')
    utils.check_file_exists(geogrid_command)
    try:
      subprocess.check_call(geogrid_command, cwd=self.wps_workdir,
                            stdout=utils.devnull(), stderr=utils.devnull())
    except CalledProcessError:
      logger.error('Geogrid failed %s:' %geogrid_command)
      raise  # re-raise exception


  def _run_ungrib():
    '''
    run ungrib.exe (run it on the login node for now)
    '''
    ungrib_command = os.path.join(self.config['filesystem']['wps_dir'],
                            'ungrib', 'ungrib.exe')
    utils.check_file_exists(ungrib_command)
    try:
      subprocess.check_call(ungrib_command, cwd=self.wps_workdir,
                            stdout=utils.devnull(), stderr=utils.devnull())
    except CalledProcessError:
      logger.error('Ungrib failed %s:' %ungrib_command)
      raise  # re-raise exception


  def _run_metgrid():
    '''
    run metgrid.exe (run it on the login node for now)
    '''
    metgrid_command = os.path.join(self.config['filesystem']['wps_dir'],
                            'metgrid', 'metgrid.exe')
    utils.check_file_exists(metgrid_command)
    try:
      subprocess.check_call(metgrid_command, cwd=self.wps_workdir,
                            stdout=utils.devnull(), stderr=utils.devnull())
    except CalledProcessError:
      logger.error('Metgrid failed %s:' %metgrid_command)
      raise  # re-raise exception
