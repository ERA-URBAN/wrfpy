#!/usr/bin/env python3

'''
description:    WRFDA part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import os
from namelist import namelist_get
from namelist import namelist_set
import subprocess
import shutil
from utils import *

env.WRFDADIR = '/data/test'
env.WRFDA_WORKDIR = '/data/test'
env.OBS_DIR = '/data/test'
env.OBS_FILENAME = 'results.txt'
env.RUNDIR = '/data/test'

def preprocess():
  from shutil import copyfile
  # copy default 3dvar obsproc namelist to namelist.obsproc
  obsproc_dir = os.path.join(env.WRFDADIR, 'var/obsproc')
  obsproc_namelist = os.path.join(obsproc_dir, 'namelist.obsproc')
  shutil.copyfile(os.path.join(obsproc_dir, 'namelist.obsproc.3dvar.wrfvar-tut'),
           obsproc_namelist)
  # copy observation in LITTLE_R format to obsproc_dir
  shutil.copyfile(os.path.join(env.OBS_DIR, env.OBS_FILENAME),
           os.path.join(obsproc_dir, env.OBS_FILENAME))
  # read information from env.RUNDIR/namelist.input
  namelist_input = os.path.join(env.RUNDIR, 'namelist.input')
  nesti= namelist_get(namelist_input, 'domains:i_parent_start')
  nestj = namelist_get(namelist_input, 'domains:j_parent_start')
  esn = namelist_get(namelist_input, 'domains_e_sn')
  ewe = namelist_get(namelist_input, 'domains_e_we')
  dis = namelist_get(namelist_input, 'domains:dx')
  numc = namelist_get(namelist_input, 'domains:parent_id')
  maxnes = namelist_get(namelist_input, 'domains:max_dom')
  # write information to namelist.obsproc
  namelist_set(obsproc_namelist, 'record1:obs_gts_filename', env.OBS_FILENAME)
  namelist_set(obsproc_namelist, 'record8:nesti', nesti)
  namelist_set(obsproc_namelist, 'record8:nestj', nestj)
  namelist_set(obsproc_namelist, 'record8:nestix', ewe)
  namelist_set(obsproc_namelist, 'record8:nestjx', esn)
  namelist_set(obsproc_namelist, 'record8:numc', numc)
  namelist_set(obsproc_namelist, 'record8:dis', dis)
  namelist_set(obsproc_namelist, 'record8:maxnes', maxnes)
  # set time_analysis, time_window_min, time_window_max
  # TODO: use datetime to create variables
  namelist_set(obsproc_namelist, 'record2:time_analysis', time_analysis)
  namelist_set(obsproc_namelist, 'record2:time_window_min', time_window_min)
  namelist_set(obsproc_namelist, 'record2:time_window_max', time_winodw_max)
  # run obsproc.exe
  subprocess.check_call(os.path.join(obsproc_dir, 'obsproc.exe'))
  # TODO: check if output is file is created and no errors have occurred

def prepare():
  if os.path.exists(env.WRFDA_WORKDIR):
    shutil.rmtree(env.WRFDA_WORKDIR)  # remove env.WRFDA_WORKDIR
  utils._create_directory(env.WRFDA_WORKDIR)  # create empty env.WRFDA_WORKDIR
  # copy namelis.input to env.WRFDA_WORKDIR
  wrfda_namelist = os.path.join(
                  env.WRFDADIR, 'var/test/tutorial/namelist.input')
  shutil.copyfile(wrfda_namelist,
                  os.path.join(env.WRDA_WORKDIR, namelist.input))
  # get variables from obsproc.namelist
  obsproc_namelist = os.path.join(obsproc_dir, 'namelist.obsproc')
  tmax = namelist_get(obsproc_namelist, 'record2:time_window_max')
  tana = namelist_get(obsproc_namelist, 'record2:time_analysis')
  tmin = namelist_get(obsproc_namelist, 'record2:time_window_min')
  # set variables in namelist.input
  namelist_set(wrfda_namelist, 'wrfvar18:analysis_date', tana)
  namelist_set(wrfda_namelist, 'wrfvar21:time_window_min', tmin)
  namelist_set(wrfda_namelist, 'wrfvar22:time_window_max', tmax)
  namelist_set(wrfda_namelist, 'wrfvar7:cv_options', 3)

def create_parame(parame_type):
  filename = os.path.join(env.WRFDA_WORKDIR, parame.in)
  # add configuration to parame.in file
  parame = open(filename, 'w')  # open file
  if parame_type == 'lower':
    ## start config file lower boundary conditions
    parame.write("""&control_param
      da_file = './fg'
      wrf_input = './wrfinput_d01'
      wrf_input = '/home/WUR/haren009/sources/WRFV3/run/wrfinput_d01'
      domain_id = 1
      cycling = .true.
      debug = .true.
      low_bdy_only = .true.
      update_lsm = .false.
      var4d_lbc = .false.
      iswater = 16
  /
  """)
    ## end config file lower boundary conditions
  else:
    ## start config file lateral boundary conditions
    parame.write("""&control_param
      da_file = './wrfvar_output'
      wrf_bdy_file = './wrfbdy_d01'
      wrf_input = '/home/WUR/haren009/sources/WRFV3/run/wrfinput_d01'
      domain_id = 1
      cycling = .true.
      debug = .true.
      update_low_bdy = .false.
      update_lateral_bdy = .true.
      update_lsm = .false.
      var4d_lbc = .false.
  /
  """)
    ## end config file lateral boundary conditions
  parame.close()  # close file

def run():
  # get domain information from WRF namelist.input
  wrf_namelist = os.path.join(
                  env.RUNDIR, 'namelist.input')
  wrfda_namelist = os.path.join(env.WRFDA_WORKDIR, 'namelist.input')
  domains = get_domains()
  # run WRFDA for all domains
  for domain in domains:
    # silent remove file if exists
    silentremove(os.path.join(env.WRFDA_WORKDIR, 'fg'))
    # create symlink of wrfinput_d0${domain}
    os.symlink(os.path.join(env.RUNDIR, 'wrfinput_d0'domain),
               os.path.join(env.WRFDA_WORKDIR, 'fg'))
    # set domain specific information in namelist
    for var in ['domains:e_we', 'domains:e_sn', 'domains:e_vert', 'domains:dx',
                'domains:dy']:
      # get variable from ${RUNDIR}/namelist.input
      var_value = namelist_get(wrf_namelist, var)
      # set domain specific variable in WRDFA_WORKDIR/namelist.input
      namelist_set(wrfda_namelist, var, var_value[domain - 1])
    # run da_wrfvar.exe for each domain
    logfile = os.path.join(env.WRFDA_WORKDIR, 'log.wrfda_d'domain)
    subprocess.check_call([os.path.join(env.WRFDA_WORKDIR, 'da_wrfvar.exe'),
                          '>&!', logfile])
    # copy wrfvar_output_d0${domain} to ${RUNDIR}/wrfinput_d0${domain}
    silentremove(os.path.join(env.RUNDIR ,'wrfinput_d0'domain)
    shutil.copyfile(os.path.join(env.WRFDA_WORKDIR, 'wrfvar_output'),
                    os.path.join(env.RUNDIR, 'wrfinput_d0'domain))
    # cleanup wrfvar_output
    silentremove(os.path.join(env.WRFDA_WORKDIR, 'wrfvar_output'))

def updatebc(boundary_type):
  # general functionality independent of boundary type in parame.in
  if os.path.exists(env.WRFDA_WORKDIR):
    shutil.rmtree(env.WRFDA_WORKDIR)  # remove env.WRFDA_WORKDIR
  utils._create_directory(env.WRFDA_WORKDIR)
  # define parame.in file
  create_parame(boundary_type)
  # symlink da_update_bc.exe
  os.symlink(os.path.join(env.WRFDADIR, 'var/da/da_update_bc.exe'),
             os.path.join(env.WRFDA_WORKDIR, 'var/da/da_update_bc.exe'))
  # copy wrfbdy_d01 file (lateral boundaries) to WRFDA_WORKDIR
  shutil.copyfile(os.path.join(env.RUNDIR, 'wrfbdy_d01'),
                  os.path.join(env.WRFDA_WORKDIR, 'wrfbdy_d01'))
  # specific for boundary type
  if boundary_type == 'lower' :
    # get domain information from RUNDIR/namelist.input
    domains = get_domains()
    # TODO: get timestamp
    for domain in domains:
      # copy first guess (wrfout in wrfinput format) for WRFDA
      first_guess = os.path.join(env.RUNDIR, 'wrfvar_input_d0' + domain +
                                 '_' + timestamp)
      try:
        shutil.copyfile(first_guess, os.path.join(env.WRFDA_WORKDIR, 'fg'))
      except Exception:
        shutil.copyfile(os.path.join(env.RUNDIR, 'wrfinput_d0' + domain),
                        os.path.join(env.WRFDA_WORKDIR, 'fg'))
      # set domain in parame.in
      parame = os.path.join(env.WRFDA_WORKDIR, 'parame.in')
      namelist_set(parame, 'control_param:domain_id', domain)
      # set wrf_input (IC from WPS and WRF real)
      namelist_set(parame ,'control_param:wrf_input',
                   os.path.join(env.RUNDIR, 'wrfinput_d0' + domain))
      # run da_update_bc.exe
      subprocess.check_call(os.path.join(env.WRFDA_WORKDIR, 'da_update_bc.exe'))
      # copy updated first guess to RUNDIR/wrfinput
      silentremove(os.path.join(env.RUNDIR, 'wrfinput_d0' + domain))
      shutil.copyfile(os.path.join(env.WRFDA_WORKDIR, 'fg'),
                      os.path.join(env.RUNDIR, 'wrfinput_d0' + domain))
  elif boundary_type == 'lateral' :
    # run da_update_bc.exe
    subprocess.check_call(os.path.join(env.WRFDA_WORKDIR, 'da_update_bc.exe'))
    # copy over updated lateral boundary conditions to RUNDIR
    silentremove(os.path.join(env.RUNDIR, 'wrfbdy_d01'))
    shutil.copyfile(os.path.join(env.WRFDA_WORKDIR, 'wrfbdy_d01'),
                    os.path.join(env.RUNDIR, 'wrfbdy_d01'))
  else:
    raise Exception('unknown boundary type')


