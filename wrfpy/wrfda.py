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
from wrfpy import utils
from wrfpy.config import config
from datetime import datetime
import time


class wrfda(config):
    '''
    description
    '''
    def __init__(self, datestart, low_only=False):
        config.__init__(self)  # load config
        self.low_only = low_only
        self.datestart = datestart
        self.rundir = self.config['filesystem']['wrf_run_dir']
        self.wrfda_workdir = os.path.join(self.config['filesystem']['work_dir'],
                                          'wrfda')
        self.max_dom = utils.get_max_dom(self.config['options_wrf']['namelist.input'])
        # copy default 3dvar obsproc namelist to namelist.obsproc
        self.obsproc_dir = os.path.join(self.config['filesystem']['wrfda_dir'],
                                        'var/obsproc')
        # get dictionary with workdir/obs filename per domain
        self.obs = self.get_obsproc_dirs()

    def run(self, datestart):
        '''
        Run all WRFDA steps
        '''
        self.datestart = datestart
        self.obsproc_init(datestart)  # initialize obsrproc work directory
        self.obsproc_run()  # run obsproc.exe
        self.prepare_updatebc(datestart)  # prepares for updating low bc
        for domain in range(1, self.max_dom+1):
            self.updatebc_run(domain)  # run da_updatebc.exe
        self.prepare_wrfda()  # prepare for running da_wrfvar.exe
        for domain in range(1, self.max_dom+1):
            self.wrfvar_run(domain)  # run da_wrfvar.exe
        # prepare for updating lateral bc
        self.prepare_updatebc_type('lateral', datestart, 1)
        self.updatebc_run(1)  # run da_updatebc.exe
        self.wrfda_post(datestart)  # copy files over to WRF run_dir

    def obsproc_init(self, datestart):
        '''
        Sync obsproc namelist with WRF namelist.input
        '''
        from datetime import timedelta
        from datetime import datetime
        # convert to unique list
        obslist = list(set(self.obs.values()))
        # read WRF namelist in WRF work_dir
        wrf_nml = f90nml.read(self.config['options_wrf']['namelist.input'])
        for obs in obslist:
            # read obsproc namelist
            obsproc_nml = f90nml.read(os.path.join
                                      (self.obsproc_dir,
                                       'namelist.obsproc.3dvar.wrfvar-tut'))
            # create obsproc workdir
            self.create_obsproc_dir(obs[0])
            # copy observation in LITTLE_R format to obsproc_dir
            shutil.copyfile(os.path.join(
              self.config['filesystem']['obs_dir'], obs[1]),
              os.path.join(obs[0], obs[1]))
            # sync obsproc namelist variables with wrf namelist.input
            obsproc_nml['record1']['obs_gts_filename'] = obs[1]
            obsproc_nml['record8']['nesti'] = (wrf_nml['domains'][
                                               'i_parent_start'])
            obsproc_nml['record8']['nestj'] = (wrf_nml['domains'][
                                               'j_parent_start'])
            obsproc_nml['record8']['nestix'] = wrf_nml['domains']['e_we']
            obsproc_nml['record8']['nestjx'] = wrf_nml['domains']['e_sn']
            obsproc_nml['record8']['numc'] = wrf_nml['domains']['parent_id']
            obsproc_nml['record8']['dis'] = wrf_nml['domains']['dx']
            obsproc_nml['record8']['maxnes'] = wrf_nml['domains']['max_dom']
            # set time_analysis, time_window_min, time_window_max
            # check if both datestart and dateend are a datetime instance
            if not isinstance(datestart, datetime):
                raise TypeError("datestart must be an instance of datetime")
            obsproc_nml['record2'][
              'time_analysis'] = datetime.strftime(datestart,
                                                   '%Y-%m-%d_%H:%M:%S')
            obsproc_nml['record2']['time_window_min'] = datetime.strftime(
              datestart - timedelta(minutes=15), '%Y-%m-%d_%H:%M:%S')
            obsproc_nml['record2']['time_window_max'] = datetime.strftime(
              datestart + timedelta(minutes=15), '%Y-%m-%d_%H:%M:%S')
            # save obsproc_nml
            utils.silentremove(os.path.join(obs[0], 'namelist.obsproc'))
            obsproc_nml.write(os.path.join(obs[0], 'namelist.obsproc'))

    def get_obsproc_dirs(self):
        '''
        get list of observation names and workdirs for obsproc
        '''
        # initialize variables
        obsnames, obsproc_workdirs = [], []
        for dom in range(1, self.max_dom + 1):
            try:
                obsname = self.config['filesystem']['obs_filename_d'
                                                    + str(dom)]
                obsnames.append(obsname)
                obsproc_workdirs.append(os.path.join(
                                        self.config['filesystem']['work_dir'],
                                        'obsproc', obsname))
            except KeyError:
                obsname = self.config['filesystem']['obs_filename']
                obsnames.append(obsname)
                obsproc_workdirs.append(os.path.join(
                                        self.config['filesystem']['work_dir'],
                                        'obsproc', obsname))
        # merge everything into a dict
        # domain: (workdir, obsname)
        obs = dict(zip(range(1, self.max_dom + 1),
                       zip(obsproc_workdirs, obsnames)))
        return obs

    def create_obsproc_dir(self, workdir):
        '''
        symlink all files required to run obsproc.exe into obsproc workdir
        '''
        # cleanup
        utils.silentremove(workdir)
        # create work directory
        utils._create_directory(workdir)
        # symlink error files
        files = ['DIR.txt', 'HEIGHT.txt', 'PRES.txt', 'RH.txt', 'TEMP.txt',
                 'UV.txt', 'obserr.txt']
        for fl in files:
            os.symlink(os.path.join(self.obsproc_dir, fl),
                       os.path.join(workdir, fl))
        # symlink obsproc.exe
        os.symlink(os.path.join(self.obsproc_dir, 'src', 'obsproc.exe'),
                   os.path.join(workdir, 'obsproc.exe'))

    def obsproc_run(self):
        '''
        run obsproc.exe
        '''
        obslist = list(set(self.obs.values()))
        obsproc_dir = obslist[0][0]
        # TODO: check if output is file is created and no errors have occurred
        j_id = None
        if len(self.config['options_slurm']['slurm_obsproc.exe']):
            # run using slurm
            if j_id:
                mid = "--dependency=afterok:%d" % j_id
                obsproc_command = ['sbatch', mid,
                                   self.config['options_slurm']['slurm_obsproc.exe']]
            else:
                obsproc_command = ['sbatch',
                                   self.config['options_slurm']['slurm_obsproc.exe']]
            utils.check_file_exists(obsproc_command[-1])
            try:
                res = subprocess.check_output(obsproc_command, cwd=obsproc_dir,
                                              stderr=utils.devnull())
                j_id = int(res.split()[-1])  # slurm job-id
            except subprocess.CalledProcessError:
                #logger.error('Obsproc failed %s:' % obsproc_command)
                raise  # re-raise exception
            utils.waitJobToFinish(j_id)
        else:
            # run locally
            subprocess.check_call(os.path.join(obsproc_dir, 'obsproc.exe'),
                                  cwd=obsproc_dir,
                                  stdout=utils.devnull(),
                                  stderr=utils.devnull())

            return None

    def prepare_symlink_files(self, domain):
        '''
        prepare WRFDA directory
        '''
        # set domain specific workdir
        wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(domain))
        # read obsproc namelist
        obsproc_nml = f90nml.read(os.path.join(self.obs[domain][0],
                                               'namelist.obsproc'))
        # symlink da_wrfvar.exe, LANDUSE.TBL, be.dat.cv3
        os.symlink(os.path.join(
          self.config['filesystem']['wrfda_dir'], 'var/da/da_wrfvar.exe'
          ), os.path.join(wrfda_workdir, 'da_wrfvar.exe'))
        if self.check_cv5_cv7():
            # symlink the correct be.dat from the list
            os.symlink(self.wrfda_be_dat,
                       os.path.join(wrfda_workdir, 'be.dat'))
        else:
            # cv3
            os.symlink(os.path.join(
              self.config['filesystem']['wrfda_dir'], 'var/run/be.dat.cv3'
              ), os.path.join(wrfda_workdir, 'be.dat'))
        os.symlink(os.path.join(
          self.config['filesystem']['wrfda_dir'], 'run/LANDUSE.TBL'
          ), os.path.join(wrfda_workdir, 'LANDUSE.TBL'))
        # symlink output of obsproc
        os.symlink(os.path.join
                   (self.obs[domain][0],
                    'obs_gts_' + obsproc_nml['record2']['time_analysis'] +
                    '.3DVAR'
                    ), os.path.join(wrfda_workdir, 'ob.ascii'))

    def create_parame(self, parame_type, domain):
        # set domain specific workdir
        wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(domain))
        filename = os.path.join(wrfda_workdir, 'parame.in')
        utils.silentremove(filename)
        # add configuration to parame.in file
        parame = open(filename, 'w')  # open file
        if parame_type == 'lower':
            # start config file lower boundary conditions
            parame.write("""&control_param
              da_file = './fg'
              wrf_input = './wrfinput_d01'
              domain_id = 1
              cycling = .true.
              debug = .true.
              update_low_bdy = .true.
              update_lsm = .true.
              var4d_lbc = .false.
              iswater = 16
            /
            """)
            # end config file lower boundary conditions
        else:
            # start config file lateral boundary conditions
            parame.write("""&control_param
              da_file = '/home/haren/model/WRFV3/run2/wrfinput_d01'
              wrf_bdy_file = './wrfbdy_d01'
              domain_id = 1
              cycling = .true.
              debug = .true.
              update_low_bdy = .false.
              update_lateral_bdy = .true.
              update_lsm = .false.
              var4d_lbc = .false.
            /
            """)
            # end config file lateral boundary conditions
        parame.close()  # close file

    def prepare_wrfda_namelist(self, domain):
        # set domain specific workdir
        wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(domain))
        # read WRFDA namelist, use namelist.wrfda as supplied in config.json
        # if not supplied, fall back to default from WRFDA
        if utils.check_file_exists(self.config['options_wrfda'][
                                   'namelist.wrfda'],
                                   boolean=True):
            wrfda_namelist = self.config['options_wrfda']['namelist.wrfda']
        else:
            wrfda_namelist = os.path.join(self.config['filesystem'][
                                          'wrfda_dir'],
                                          'var/test/tutorial/namelist.input')
        wrfda_nml = f90nml.read(wrfda_namelist)
        # read WRF namelist in WRF work_dir
        wrf_nml = f90nml.read(os.path.join
                              (self.config['filesystem']['wrf_run_dir'],
                               'namelist.input'))
        # set domain specific information in namelist
        for var in ['e_we', 'e_sn', 'e_vert', 'dx', 'dy']:
            # get variable from ${RUNDIR}/namelist.input
            var_value = wrf_nml['domains'][var]
            # set domain specific variable in WRDFA_WORKDIR/namelist.input
            wrfda_nml['domains'][var] = var_value[domain - 1]
        for var in ['mp_physics', 'ra_lw_physics', 'ra_sw_physics', 'radt',
                    'sf_sfclay_physics', 'sf_surface_physics',
                    'bl_pbl_physics',
                    'cu_physics', 'cudt', 'num_soil_layers']:
            # get variable from ${RUNDIR}/namelist.input
            var_value = wrf_nml['physics'][var]
            # set domain specific variable in WRDFA_WORKDIR/namelist.input
            try:
                wrfda_nml['physics'][var] = var_value[domain - 1]
            except TypeError:
                wrfda_nml['physics'][var] = var_value
        obsproc_nml = f90nml.read(os.path.join
                                  (self.obs[domain][0], 'namelist.obsproc'))
        # sync wrfda namelist with obsproc namelist
        wrfda_nml['wrfvar18']['analysis_date'] = (obsproc_nml['record2'][
                                                  'time_analysis'])
        wrfda_nml['wrfvar21']['time_window_min'] = (obsproc_nml['record2'][
                                                    'time_window_min'])
        wrfda_nml['wrfvar22']['time_window_max'] = (obsproc_nml['record2'][
                                                    'time_window_max'])
        if self.check_cv5_cv7():
            wrfda_nml['wrfvar7']['cv_options'] = int(self.config[
                                                     'options_wrfda'][
                                                     'cv_type'])
            wrfda_nml['wrfvar6']['max_ext_its'] = 2
            wrfda_nml['wrfvar5']['check_max_iv'] = True
        else:
            wrfda_nml['wrfvar7']['cv_options'] = 3
        tana = utils.return_validate(obsproc_nml
                                     ['record2']['time_analysis'][:-6])
        wrfda_nml['time_control']['start_year'] = tana.year
        wrfda_nml['time_control']['start_month'] = tana.month
        wrfda_nml['time_control']['start_day'] = tana.day
        wrfda_nml['time_control']['start_hour'] = tana.hour
        wrfda_nml['time_control']['end_year'] = tana.year
        wrfda_nml['time_control']['end_month'] = tana.month
        wrfda_nml['time_control']['end_day'] = tana.day
        wrfda_nml['time_control']['end_hour'] = tana.hour
        # save changes to wrfda_nml
        utils.silentremove(os.path.join(wrfda_workdir, 'namelist.input'))
        wrfda_nml.write(os.path.join(wrfda_workdir, 'namelist.input'))

    def check_cv5_cv7(self):
        '''
        return True if cv_type=5 or cv_type=7 is set and
        be.dat is defined (and exist on filesystem)
        for the outer domain in config.json
        '''
        if (int(self.config['options_wrfda']['cv_type']) in [5, 7]):
            # check if be.dat is a filepath or an array of filepaths
            if isinstance(self.config['options_wrfda']['be.dat'], str):
                # option is a filepath
                self.wrfda_be_dat = self.config['options_wrfda']['be.dat']
            elif isinstance(self.config['options_wrfda']['be.dat'], list):
                if len(self.config['options_wrfda']['be.dat']) == 1:
                    # lenght == 1, so threat the first element as a str case
                    month_idx = 0
                elif len(self.config['options_wrfda']['be.dat']) == 12:
                    # there is one be.dat matrix for each month
                    # find month number from self.datestart
                    month_idx = self.datestart.month - 1
                else:
                    # list but not of length 1 or 12
                    raise IOError("config['options_wrfda']['be.dat'] ",
                                  "should be a string or a ",
                                  "list of length 1 or 12. Found a list of ",
                                  "length ",
                                  str(len(self.config['options_wrfda'][
                                          'be.dat'])))
                self.wrfda_be_dat = self.config[
                  'options_wrfda']['be.dat'][month_idx]
            else:
                # not a list or str
                raise TypeError("unkonwn type for be.dat configuration:",
                                type(self.config['options_wrfda']['be.dat']))
            return utils.check_file_exists(
              self.wrfda_be_dat, boolean=True)

    def prepare_wrfda(self):
        '''
        prepare WRFDA
        '''
        # prepare a WRFDA workdirectory for each domain
        for domain in range(1, self.max_dom+1):
            self.prepare_symlink_files(domain)
            self.prepare_wrfda_namelist(domain)

    def wrfvar_run(self, domain):
        '''
        run da_wrfvar.exe
        '''
        # set domain specific workdir
        wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(domain))
        logfile = os.path.join(wrfda_workdir, 'log.wrfda_d' + str(domain))
        j_id = None
        if len(self.config['options_slurm']['slurm_wrfvar.exe']):
            if j_id:
                mid = "--dependency=afterok:%d" % j_id
                wrfvar_command = ['sbatch', mid,
                                  self.config['options_slurm']['slurm_wrfvar.exe']]
            else:
                wrfvar_command = ['sbatch',
                                  self.config['options_slurm']['slurm_wrfvar.exe']]
            utils.check_file_exists(wrfvar_command[-1])
            try:
                res = subprocess.check_output(wrfvar_command,
                                              cwd=wrfda_workdir,
                                              stderr=utils.devnull())
                j_id = int(res.split()[-1])  # slurm job-id
            except subprocess.CalledProcessError:
                #logger.error('Wrfvar failed %s:' %wrfvar_command)
                raise  # re-raise exception
            utils.waitJobToFinish(j_id)
        else:
            # run locally
            subprocess.check_call([os.path.join(wrfda_workdir,
                                                'da_wrfvar.exe'),
                                   '>&!', logfile],
                                  cwd=wrfda_workdir, stdout=utils.devnull(),
                                  stderr=utils.devnull())

    def prepare_updatebc(self, datestart):
        # prepare a WRFDA workdirectory for each domain
        for domain in range(1, self.max_dom+1):
            # TODO: add check for domain is int
            # define domain specific workdir
            wrfda_workdir = os.path.join(self.wrfda_workdir,
                                         "d0" + str(domain))
            # general functionality independent of boundary type in parame.in
            if os.path.exists(wrfda_workdir):
                shutil.rmtree(wrfda_workdir)  # remove wrfda_workdir
            utils._create_directory(os.path.join(wrfda_workdir, 'var', 'da'))
            # define parame.in file
            self.create_parame('lower', domain)
            # symlink da_update_bc.exe
            os.symlink(os.path.join(
              self.config['filesystem']['wrfda_dir'], 'var/da/da_update_bc.exe'
              ), os.path.join(wrfda_workdir, 'da_update_bc.exe'))
            # copy wrfbdy_d01 file (lateral boundaries) to WRFDA_WORKDIR
            shutil.copyfile(os.path.join(self.rundir, 'wrfbdy_d01'),
                            os.path.join(wrfda_workdir, 'wrfbdy_d01'))
            # set parame.in file for updating lower boundary first
            self.prepare_updatebc_type('lower', datestart, domain)

    def prepare_updatebc_type(self, boundary_type, datestart, domain):
        # set domain specific workdir
        wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(domain))
        if (boundary_type == 'lower'):
            # define parame.in file
            self.create_parame(boundary_type, domain)
            # copy first guess (wrfout in wrfinput format) for WRFDA
            first_guess = os.path.join(self.rundir,
                                       ('wrfvar_input_d0' + str(domain) + '_' +
                                        datetime.strftime
                                        (datestart, '%Y-%m-%d_%H:%M:%S')))
            try:
                shutil.copyfile(first_guess, os.path.join(wrfda_workdir, 'fg'))
            except Exception:
                shutil.copyfile(os.path.join
                                (self.rundir, 'wrfinput_d0' + str(domain)),
                                os.path.join(wrfda_workdir, 'fg'))
            # read parame.in file
            parame = f90nml.read(os.path.join(wrfda_workdir, 'parame.in'))
            # set domain in parame.in
            parame['control_param']['domain_id'] = domain
            # set wrf_input (IC from WPS and WRF real)
            parame['control_param']['wrf_input'] = str(os.path.join(
              self.rundir, 'wrfinput_d0' + str(domain)))
            # save changes to parame.in file
            utils.silentremove(os.path.join(wrfda_workdir, 'parame.in'))
            parame.write(os.path.join(wrfda_workdir, 'parame.in'))
        elif (boundary_type == 'lateral'):
            # define parame.in file
            self.create_parame(boundary_type, domain)
            # read parame.in file
            parame = f90nml.read(os.path.join(wrfda_workdir, 'parame.in'))
            # set output from WRFDA
            parame['control_param']['da_file'] = os.path.join(wrfda_workdir,
                                                              'wrfvar_output')
            # save changes to parame.in file
            utils.silentremove(os.path.join(wrfda_workdir, 'parame.in'))
            parame.write(os.path.join(wrfda_workdir, 'parame.in'))
        else:
            raise Exception('unknown boundary type')

    def updatebc_run(self, domain):
        # set domain specific workdir
        wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(domain))
        # run da_update_bc.exe
        j_id = None
        if len(self.config['options_slurm']['slurm_updatebc.exe']):
            if j_id:
                mid = "--dependency=afterok:%d" % j_id
                updatebc_command = ['sbatch', mid,
                                    self.config[
                                      'options_slurm']['slurm_updatebc.exe']]
            else:
                updatebc_command = ['sbatch',
                                    self.config[
                                      'options_slurm']['slurm_updatebc.exe']]
            try:
                res = subprocess.check_output(updatebc_command,
                                              cwd=wrfda_workdir,
                                              stderr=utils.devnull())
                j_id = int(res.split()[-1])  # slurm job-id
            except subprocess.CalledProcessError:
                #logger.error('Updatebc failed %s:' % updatebc_command)
                raise  # re-raise exception
            utils.waitJobToFinish(j_id)
        else:
            # run locally
            subprocess.check_call(os.path.join
                                  (wrfda_workdir, 'da_update_bc.exe'),
                                  cwd=wrfda_workdir,
                                  stdout=utils.devnull(),
                                  stderr=utils.devnull())

    def wrfda_post(self, datestart):
        '''
        Move files into WRF run dir
        after all data assimilation steps have completed
        '''
        # prepare a WRFDA workdirectory for each domain
        for domain in range(1, self.max_dom+1):
            # set domain specific workdir
            wrfda_workdir = os.path.join(self.wrfda_workdir,
                                         "d0" + str(domain))
            if (domain == 1):
                # copy over updated lateral boundary conditions to RUNDIR
                # only for outer domain
                utils.silentremove(os.path.join(self.rundir, 'wrfbdy_d01'))
                shutil.copyfile(os.path.join(wrfda_workdir, 'wrfbdy_d01'),
                                os.path.join(self.rundir, 'wrfbdy_d01'))
                # copy log files
                datestr = datetime.strftime(datestart, '%Y-%m-%d_%H:%M:%S')
                rsl_out_name = 'wrfda_rsl_out_' + datestr
                statistics_out_name = 'wrfda_statistics_' + datestr
                try:
                    shutil.copyfile(os.path.join
                                    (wrfda_workdir, 'rsl.out.0000'),
                                    os.path.join(self.rundir, rsl_out_name))
                except IOError:
                    pass
                try:
                    shutil.copyfile(os.path.join
                                    (wrfda_workdir, 'statistics'),
                                    os.path.join(self.rundir,
                                                 statistics_out_name))
                except IOError:
                    pass
            # copy wrfvar_output_d0${domain} to ${RUNDIR}/wrfinput_d0${domain}
            utils.silentremove(os.path.join
                               (self.rundir, 'wrfinput_d0' + str(domain)))
            if not self.low_only:
                shutil.copyfile(os.path.join(wrfda_workdir, 'wrfvar_output'),
                                os.path.join(self.rundir,
                                             'wrfinput_d0' + str(domain)))
            else:
                shutil.copyfile(os.path.join(wrfda_workdir, 'fg'),
                                os.path.join(self.rundir,
                                             'wrfinput_d0' + str(domain)))
