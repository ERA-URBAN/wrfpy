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
import utils
from config import config
from datetime import datetime

class wrfda(config):
  '''
  description
  '''
  def __init__(self, datestart):
    config.__init__(self)  # load config
    self.rundir = self.config['filesystem']['wrf_run_dir']
    self.wrfda_workdir = os.path.join(self.config['filesystem']['work_dir'],
                                      'wrfda')
    print "preprocess"
    self.preprocess(datestart)
    print "updatebc lower"
    self.updatebc('lower', datestart)
    print "prepare"
    self.prepare()
    print "run wrfda"
    self.run()
    print "udpatebc lateral"
    self.updatebc('lateral', datestart)

  def preprocess(self, datestart):
    from shutil import copyfile
    from datetime import timedelta
    from datetime import datetime
    # copy default 3dvar obsproc namelist to namelist.obsproc
    obsproc_dir = os.path.join(self.config['filesystem']['wrfda_dir'],
                               'var/obsproc')
    # read obsproc namelist
    obsproc_nml = f90nml.read(os.path.join(obsproc_dir,
                                           'namelist.obsproc.3dvar.wrfvar-tut'))
    # read WRF namelist in WRF work_dir
    wrf_nml = f90nml.read(os.path.join(self.config['filesystem']['wrf_run_dir'],
                                       'namelist.input'))
    # copy observation in LITTLE_R format to obsproc_dir
    shutil.copyfile(os.path.join(
      self.config['filesystem']['obs_dir'],
      self.config['filesystem']['obs_filename']), os.path.join(
        obsproc_dir, self.config['filesystem']['obs_filename']))
    # sync obsproc namelist variables with wrf namelist.input
    obsproc_nml['record1']['obs_gts_filename'] = str(self.config[
      'filesystem']['obs_filename'])  # convert unicode str to regular str
    obsproc_nml['record8']['nesti'] = wrf_nml['domains']['i_parent_start']
    obsproc_nml['record8']['nestj'] = wrf_nml['domains']['j_parent_start']
    obsproc_nml['record8']['nestix'] = wrf_nml['domains']['e_we']
    obsproc_nml['record8']['nestjx'] = wrf_nml['domains']['e_sn']
    obsproc_nml['record8']['numc'] = wrf_nml['domains']['parent_id']
    obsproc_nml['record8']['dis'] = wrf_nml['domains']['dx']
    obsproc_nml['record8']['maxnes'] = wrf_nml['domains']['max_dom']
    # set time_analysis, time_window_min, time_window_max
    # check if both datestart and dateend are a datetime instance
    if not isinstance(datestart, datetime):
      raise TypeError("datestart must be an instance of datetime")
    obsproc_nml['record2']['time_analysis'] = datetime.strftime(datestart,
                                                        '%Y-%m-%d_%H:%M:%S')
    obsproc_nml['record2']['time_window_min'] = datetime.strftime(
      datestart - timedelta(minutes=15), '%Y-%m-%d_%H:%M:%S')
    obsproc_nml['record2']['time_window_max'] = datetime.strftime(
      datestart + timedelta(minutes=15), '%Y-%m-%d_%H:%M:%S')
    # save obsproc_nml
    utils.silentremove(os.path.join(obsproc_dir, 'namelist.obsproc'))
    obsproc_nml.write(os.path.join(obsproc_dir, 'namelist.obsproc'))
    # run obsproc.exe
    subprocess.check_call(os.path.join(obsproc_dir, 'obsproc.exe'))
    # TODO: check if output is file is created and no errors have occurred

  def prepare(self):
    obsproc_dir = os.path.join(self.config['filesystem']['wrfda_dir'],
                               'var/obsproc')
    if os.path.exists(self.wrfda_workdir):
      shutil.rmtree(self.wrfda_workdir)  # remove self.wrfda_workdir
    utils._create_directory(self.wrfda_workdir)  # create empty self.wrfda_workdir
    # read wrfda and obsproc namelists
    wrfda_namelist = os.path.join(self.config['filesystem']['wrfda_dir'],
                                  'var/test/tutorial/namelist.input')
    wrfda_nml = f90nml.read(wrfda_namelist)
    obsproc_nml = f90nml.read(os.path.join(obsproc_dir, 'namelist.obsproc'))
    # sync wrfda namelist with obsproc namelist
    wrfda_nml['wrfvar18']['analysis_date'] = obsproc_nml['record2']['time_analysis']
    wrfda_nml['wrfvar21']['time_window_min'] = obsproc_nml['record2']['time_window_min']
    wrfda_nml['wrfvar22']['time_window_max'] = obsproc_nml['record2']['time_window_max']
    wrfda_nml['wrfvar7']['cv_options'] =  3
    # save wrfda namelist
    utils.silentremove(os.path.join(self.wrfda_workdir, 'namelist.input'))
    wrfda_nml.write(os.path.join(self.wrfda_workdir, 'namelist.input'))
    # symlink da_wrfvar.exe
    os.symlink(os.path.join(
      self.config['filesystem']['wrfda_dir'],'var/da/da_wrfvar.exe'
      ), os.path.join(self.wrfda_workdir, 'da_wrfvar.exe'))

  def create_parame(self, parame_type):
    filename = os.path.join(self.wrfda_workdir, 'parame.in')
    utils.silentremove(filename)
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

  def run(self):
    # read WRFDA namelist
    wrfda_nml = f90nml.read(os.path.join(self.wrfda_workdir, 'namelist.input'))
    # read WRF namelist in WRF work_dir
    wrf_nml = f90nml.read(os.path.join(self.config['filesystem']['wrf_run_dir'],
                                       'namelist.input'))
    # maximum domain number
    max_dom = wrf_nml['domains']['max_dom']
    # run WRFDA for all domains
    for domain in range(1, max_dom+1):
      # silent remove file if exists
      utils.silentremove(os.path.join(self.wrfda_workdir, 'fg'))
      # create symlink of wrfinput_d0${domain}
      os.symlink(os.path.join(self.rundir, 'wrfinput_d0' + str(domain)),
                os.path.join(self.wrfda_workdir, 'fg'))
      # set domain specific information in namelist
      for var in ['e_we', 'e_sn', 'e_vert', 'dx', 'dy']:
        # get variable from ${RUNDIR}/namelist.input
        var_value = wrf_nml['domains'][var]
        # set domain specific variable in WRDFA_WORKDIR/namelist.input
        wrfda_nml['domains'][var] = var_value[domain - 1]
      # save changes to wrfda_nml
      utils.silentremove(os.path.join(self.wrfda_workdir, 'namelist.input'))
      wrfda_nml.write(os.path.join(self.wrfda_workdir, 'namelist.input'))
      # run da_wrfvar.exe for each domain
      logfile = os.path.join(self.wrfda_workdir, 'log.wrfda_d' + str(domain))
      subprocess.check_call([os.path.join(self.wrfda_workdir, 'da_wrfvar.exe'), '>&!', logfile],
                            cwd=self.wrfda_workdir, stdout=utils.devnull(), stderr=utils.devnull())
      # copy wrfvar_output_d0${domain} to ${RUNDIR}/wrfinput_d0${domain}
      utils.silentremove(os.path.join(self.rundir ,'wrfinput_d0' + str(domain)))
      shutil.copyfile(os.path.join(self.wrfda_workdir, 'wrfvar_output'),
                      os.path.join(self.rundir, 'wrfinput_d0' + str(domain)))
      # cleanup wrfvar_output
      utils.silentremove(os.path.join(self.wrfda_workdir, 'wrfvar_output'))

  def updatebc(self, boundary_type, datestart):
    # general functionality independent of boundary type in parame.in
    if os.path.exists(self.wrfda_workdir):
      shutil.rmtree(self.wrfda_workdir)  # remove self.wrfda_workdir
    utils._create_directory(os.path.join(self.wrfda_workdir, 'var', 'da'))
    wrf_nml = f90nml.read(os.path.join(self.config['filesystem']['wrf_run_dir'],
                                       'namelist.input'))
    # define parame.in file
    self.create_parame(boundary_type)
    # symlink da_update_bc.exe
    os.symlink(os.path.join(
      self.config['filesystem']['wrfda_dir'],'var/da/da_update_bc.exe'
      ), os.path.join(self.wrfda_workdir, 'da_update_bc.exe'))
    # copy wrfbdy_d01 file (lateral boundaries) to WRFDA_WORKDIR
    shutil.copyfile(os.path.join(self.rundir, 'wrfbdy_d01'),
                    os.path.join(self.wrfda_workdir, 'wrfbdy_d01'))
    # specific for boundary type
    if boundary_type == 'lower' :
      # maximum domain number
      max_dom = wrf_nml['domains']['max_dom']
      for domain in range(1, max_dom + 1):
        # copy first guess (wrfout in wrfinput format) for WRFDA
        first_guess = os.path.join(self.rundir, 'wrfvar_input_d0' + str(domain) +
                                  '_' + datetime.strftime(datestart,
                                                          '%Y-%m-%d_%H:%M:%S'))
        try:
          shutil.copyfile(first_guess, os.path.join(self.wrfda_workdir, 'fg'))
        except Exception:
          shutil.copyfile(os.path.join(self.rundir, 'wrfinput_d0' + str(domain)),
                          os.path.join(self.wrfda_workdir, 'fg'))
        # set domain in parame.in
        parame = f90nml.read(os.path.join(self.wrfda_workdir, 'parame.in'))
        parame['control_param']['domain_id'] = domain
        # set wrf_input (IC from WPS and WRF real)
        parame['control_param']['wrf_input'] = str(os.path.join(
          self.rundir, 'wrfinput_d0' + str(domain)))
        # save changes to parame.in file
        utils.silentremove(os.path.join(self.wrfda_workdir, 'parame.in'))
        parame.write(os.path.join(self.wrfda_workdir, 'parame.in'))
        # run da_update_bc.exe
        subprocess.check_call(os.path.join(self.wrfda_workdir, 'da_update_bc.exe'),
                              cwd=self.wrfda_workdir,
                              stdout=utils.devnull(), stderr=utils.devnull())
        # copy updated first guess to RUNDIR/wrfinput
        utils.silentremove(os.path.join(self.rundir, 'wrfinput_d0' + str(domain)))
        shutil.copyfile(os.path.join(self.wrfda_workdir, 'fg'),
                        os.path.join(self.rundir, 'wrfinput_d0' + str(domain)))
    elif boundary_type == 'lateral' :
      # run da_update_bc.exe
      subprocess.check_call(os.path.join(self.wrfda_workdir, 'da_update_bc.exe'),
                            cwd=self.wrfda_workdir,
                            stdout=utils.devnull(), stderr=utils.devnull())
      # copy over updated lateral boundary conditions to RUNDIR
      utils.silentremove(os.path.join(self.rundir, 'wrfbdy_d01'))
      shutil.copyfile(os.path.join(self.wrfda_workdir, 'wrfbdy_d01'),
                      os.path.join(self.rundir, 'wrfbdy_d01'))
    else:
      raise Exception('unknown boundary type')

if __name__ == "__main__":
  datestart= datetime(2014,07,16,00)
  wrf_da = wrfda(datestart)
