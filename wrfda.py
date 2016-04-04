#!/usr/bin/env python

'''
description:    WRFDA part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import os
import f90nml
import subprocess
import shutil
from utils import *


class wrfda(config):
  '''
  description
  '''
  def __init__(self):
    config.__init__(self)  # load config
    env.WRFDADIR = '/data/test'
    env.WRFDA_WORKDIR = '/data/test'
    env.OBS_DIR = '/data/test'
    env.OBS_FILENAME = 'results.txt'
    env.RUNDIR = '/data/test'

  def preprocess():
    from shutil import copyfile
    # copy default 3dvar obsproc namelist to namelist.obsproc
    obsproc_dir = os.path.join(env.WRFDADIR, 'var/obsproc')
    # read obsproc namelist
    obsproc_nml = f90nml.read(os.path.join(obsproc_dir,
                                           'namelist.obsproc.3dvar.wrfvar-tut'))
    # read WRF namelist in WRF work_dir
    wrf_nml = f90nml.read(os.path.join(self.config['filesystem']['wrf_run_dir'],
                                       'namelist.input'))
    # copy observation in LITTLE_R format to obsproc_dir
    shutil.copyfile(os.path.join(env.OBS_DIR, env.OBS_FILENAME),
            os.path.join(obsproc_dir, env.OBS_FILENAME))
    # sync obsproc namelist variables with wrf namelist.input
    obsproc_nml['record1']['obs_gts_filename'] = env.OBS_FILENAME
    obsproc_nml['record8']['nesti'] = wrf_nml['domains']['i_parent_start']
    obsproc_nml['record8']['nestj'] = wrf_nml['domains']['j_parent_start']
    obsproc_nml['record8']['nestix'] = wrf_nml['domains']['e_we']
    obsproc_nml['record8']['nestjx'] = wrf_nml['domains']['e_sn']
    obsproc_nml['record8']['numc'] = wrf_nml['domains']['parent_id']
    obsproc_nml['record8']['dis'] = wrf_nml['domains']['dx']
    obsproc_nml['record8']['maxnes'] = wrf_nml['domains']['max_dom']
    # set time_analysis, time_window_min, time_window_max
    # TODO: use datetime to create variables
    obsproc_nml['record2']['time_analysis'] = time_analysis
    obsproc_nml['record2']['time_window_min'] = time_window_min
    obsproc_nml['record2']['time_window_max'] = time_winodw_max
    # save obsproc_nml
    obsproc_nml.write(os.path.join(obsproc_dir, 'namelist.obsproc'))
    # run obsproc.exe
    subprocess.check_call(os.path.join(obsproc_dir, 'obsproc.exe'))
    # TODO: check if output is file is created and no errors have occurred

  def prepare():
    if os.path.exists(env.WRFDA_WORKDIR):
      shutil.rmtree(env.WRFDA_WORKDIR)  # remove env.WRFDA_WORKDIR
    utils._create_directory(env.WRFDA_WORKDIR)  # create empty env.WRFDA_WORKDIR
    # read wrfda and obsproc namelists
    wrfda_namelist = os.path.join(
                    env.WRFDADIR, 'var/test/tutorial/namelist.input')
    wrdfa_nml = f90nml.read(os.path.join(env.WRDA_WORKDIR, namelist.input))
    obsproc_nml = f90nml.read(os.path.join(obsproc_dir, 'namelist.obsproc'))
    # sync wrfda namelist with obsproc namelist
    wrfda_nml['wrfvar18']['analysis_date'] = obsproc_nml['record2']['time_analysis']
    wrfda_nml['wrfvar21']['time_window_min'] = obsproc_nml['record2']['time_window_min']
    wrfda_nml['wrfvar22']['time_window_max'] = obsproc_nml['record2']['time_window_max']
    wrfda_nml['wrfvar7']['cv_options'] =  3
    # save wrfda namelist
    wrfda_nml.write(os.path.join(env.WRDA_WORKDIR, namelist.input))

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
    # read WRFDA namelist
    wrdfa_nml = f90nml.read(os.path.join(env.WRDA_WORKDIR, namelist.input))
    # read WRF namelist in WRF work_dir
    wrf_nml = f90nml.read(os.path.join(self.config['filesystem']['wrf_run_dir'],
                                       'namelist.input'))
    # maximum domain number
    max_dom = wrf_nml['domains']['max_dom']
    # run WRFDA for all domains
    for domain in range(1, max_dom+1):
      # silent remove file if exists
      silentremove(os.path.join(env.WRFDA_WORKDIR, 'fg'))
      # create symlink of wrfinput_d0${domain}
      os.symlink(os.path.join(env.RUNDIR, 'wrfinput_d0'domain),
                os.path.join(env.WRFDA_WORKDIR, 'fg'))
      # set domain specific information in namelist
      for var in ['e_we', 'e_sn', 'e_vert', 'dx', 'dy']:
        # get variable from ${RUNDIR}/namelist.input
        var_value = wrf_nml['domains'][var]
        # set domain specific variable in WRDFA_WORKDIR/namelist.input
        wrfda_nml['domains'][var] = var_value[domain - 1]
      # save changes to wrfda_nml
      wrfda_nml.write(os.path.join(env.WRDA_WORKDIR, namelist.input))
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
      # maximum domain number
      max_dom = wrf_nml['domains']['max_dom']
      # TODO: get timestamp
      for domain in range(1, max_dom + 1):
        # copy first guess (wrfout in wrfinput format) for WRFDA
        first_guess = os.path.join(env.RUNDIR, 'wrfvar_input_d0' + domain +
                                  '_' + timestamp)
        try:
          shutil.copyfile(first_guess, os.path.join(env.WRFDA_WORKDIR, 'fg'))
        except Exception:
          shutil.copyfile(os.path.join(env.RUNDIR, 'wrfinput_d0' + domain),
                          os.path.join(env.WRFDA_WORKDIR, 'fg'))
        # set domain in parame.in
        parame = f90nml.read(os.path.join(env.WRFDA_WORKDIR, 'parame.in'))
        parame['control_param']['domain_id'] = domain
        # set wrf_input (IC from WPS and WRF real)
        parame['control_param']['wrf_input'] = os.path.join(
          env.RUNDIR, 'wrfinput_d0' + domain))
        # save changes to parame.in file
        parame.write(os.path.join(env.WRFDA_WORKDIR, 'parame.in'))
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


