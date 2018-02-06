#!/usr/bin/env python

'''
description:    Unified Post Precession (UPP) part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

from wrfpy import utils
import glob
import subprocess
import os
import errno
from wrfpy.config import config

class upp(config):
  '''
  Runs the Universal Post Processor (UPP) for requested time steps in
  a wrfout file
  '''
  def __init__(self):
    config.__init__(self)
    self._set_variables()
    self._initialize()
    self._prepare_post_dir()
    self._set_environment_variables()


  def _set_variables(self):
    '''
    Define additional control variables for the unipost.exe tool, inherit from
    global config.
    '''
    self.crtm_dir = os.path.join(self.config['filesystem']['upp_dir'], 'src/lib/crtm2/src/fix')
    self.post_dir = os.path.join(self.config['filesystem']['upp_dir'], 'postprd')

  def _initialize(self):
    '''
    Check if archive dir exists, create if not.
    The archive dir is used to ...
    '''
    # create archive dir
    utils._create_directory(self.config['filesystem']['upp_archive_dir'])
    # create post_dir (remove old one if needed)
    utils.silentremove(self.post_dir)
    utils._create_directory(self.post_dir)



  def _prepare_post_dir(self):
    '''
    Create and prepare post_dir
    '''
    #logger.debug('Preparing postprd directory: %s' %config['post_dir'])

    # create self.post_dir if it does not exist yet
    utils._create_directory(self.post_dir)

    # Link all the relevant files need to compute various diagnostics
    relpath_to_link = ['EmisCoeff/Big_Endian/EmisCoeff.bin',
                       'AerosolCoeff/Big_Endian/AerosolCoeff.bin',
                       'CloudCoeff/Big_Endian/CloudCoeff.bin',
                       'SpcCoeff/Big_Endian/imgr_g11.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/imgr_g11.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/imgr_g12.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/imgr_g12.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/imgr_g13.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/imgr_g13.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/imgr_g15.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/imgr_g15.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/imgr_mt1r.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/imgr_mt1r.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/imgr_mt2.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/imgr_mt2.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/imgr_insat3d.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/imgr_insat3d.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/amsre_aqua.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/amsre_aqua.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/tmi_trmm.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/tmi_trmm.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/ssmi_f13.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/ssmi_f13.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/ssmi_f14.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/ssmi_f14.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/ssmi_f15.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/ssmi_f15.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/ssmis_f16.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/ssmis_f16.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/ssmis_f17.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/ssmis_f17.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/ssmis_f18.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/ssmis_f18.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/ssmis_f19.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/ssmis_f19.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/ssmis_f20.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/ssmis_f20.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/seviri_m10.SpcCoeff.bin',
                       'TauCoeff/ODPS/Big_Endian/seviri_m10.TauCoeff.bin',
                       'SpcCoeff/Big_Endian/v.seviri_m10.SpcCoeff.bin']

    # abspath coefficients for crtm2 (simulated synthetic satellites)
    abspath_coeff= [os.path.join(self.crtm_dir, relpath) for relpath in
                    relpath_to_link ]
    # abspath wrf_cntrl param file
    abspath_pf = os.path.join(self.config['filesystem']['upp_dir'], 'parm',
                              'wrf_cntrl.parm')
    # concatenate lists of paths
    abspath_to_link = abspath_coeff + [abspath_pf]
    # create a symlink for every file in abspath_to_link
    for fl in abspath_to_link:
      utils.check_file_exists(fl)  # check if file exist and is readable
      os.symlink(fl, os.path.join(self.post_dir, os.path.basename(fl)))
    # symlink wrf_cntrl.parm to config['post_dir']/fort.14
    os.symlink(abspath_pf, os.path.join(self.post_dir, 'fort.14'))
    # symlink microphysic's tables - code used is based on mp_physics option
    # used in the wrfout file
    os.symlink(os.path.join(self.config['filesystem']['wrf_run_dir'], 'ETAMPNEW_DATA'),
               os.path.join(self.post_dir, 'nam_micro_lookup.dat'))
    os.symlink(os.path.join(self.config['filesystem']['wrf_run_dir'],
                            'ETAMPNEW_DATA.expanded_rain'
                            ), os.path.join(self.post_dir,
                                            'hires_micro_lookup.dat'))


  def _set_environment_variables(self):
    '''
    Set environment variables
    '''
    #logger.debug('Enter set_environment_variables')
    os.environ['MP_SHARED_MEMORY'] = 'yes'
    os.environ['MP_LABELIO'] = 'yes'
    os.environ['tmmark'] = 'tm00'
    #logger.debug('Leave set_environment_variables')


  def _cleanup_output_files(self):
    '''
    Clean up old output files in post_dir
    '''
    #logger.debug('Enter cleanup_output_files')
    file_ext = [ '*.out', '*.tm00', 'fort.110', 'itag']
    files_found = [ f for files in [
      glob.glob(os.path.join(self.post_dir, ext))
      for ext in file_ext ] for f in files]
    # try to remove files, raise exception if needed
    [ utils.silentremove(fl) for fl in files_found ]
    #logger.debug('Leave cleanup_output_files')


  def _write_itag(self, wrfout, current_time):
    '''
    Create input file for unipost
      --------content itag file ---------------------------------------
      First line is location of wrfout data
      Second line is required format
      Third line is the modeltime to process
      Fourth line is the model identifier (WRF, NMM)
      -----------------------------------------------------------------
    '''
    #logger.debug('Enter write_itag')
    #logger.debug('Time in itag file is: %s' %current_time)
    # set itag filename and cleanup
    filename = os.path.join(self.post_dir, 'itag')
    utils.silentremove(filename)
    # template of itag file
    template = """{wrfout}
netcdf
{current_time}:00:00
NCAR
"""
    # context variables in template
    context = {
      "wrfout":wrfout,
      "current_time":current_time
      }
    # create the itag file and write content to it based on the template
    try:
      with open(filename, 'w') as itag:
        itag.write(template.format(**context))
    except IOError as e:
      #logger.error('Unable to write itag file: %s' %filename)
      print('Unable to write itag file: %s' %filename)
      raise  # re-raise exception
    #logger.debug('Leave write_itag')


  def _run_unipost_step(self, wrfout, current_time, thours):
    '''
    Input variables for the function are:
      - full path to a wrfout file (regular wrfout naming)
      - time to run unipost for in format YYYY-MM-DD_HH
      - thours: TODO add description
    The following functionality is provided by the function:
      - validate input parameters
      - write itag file
      - run unipost.exe command
      - rename output
      - archive output
      - cleanup output
    '''
    # see if current_time is in wrfout AND validate time format
    utils.validate_time_wrfout(wrfout, current_time)
    # extract domain information from wrfout filename
    domain = int(wrfout[-22:-20])
    # write itag file
    self._write_itag(wrfout, current_time)
    # run unipost.exe
    subprocess.check_call(os.path.join(self.config['filesystem']['upp_dir'], 'bin', 'unipost.exe'),
                          cwd=self.post_dir, stdout=utils.devnull(),
                          stderr=utils.devnull())
    # rename and archive output
    self._archive_output(current_time, thours, domain)
    # cleanup output files
    self._cleanup_output_files()


  def run_unipost_file(self, wrfout, frequency=2, use_t0=False):
    '''
    Input variables for the function are:
      - wrfout: full path to a wrfout file (regular wrfout naming)
      - (optional) frequency: time interval in hours at which processing should
        take place
      - (optional) use_t0: boolean, process time step 0
    The function provides the following functionality:
      description
    '''
    time_steps = utils.timesteps_wrfout(wrfout)
    # convert to hours since timestep 0
    td = [int((t - time_steps[0]).total_seconds()/3600) for t in time_steps]
    # modulo  should be zero
    if not td[-1]%frequency==0:
      message = ''  # TODO: add error message
      #logger.error(message)
      raise IOError(message)
    else:
      # create list of booleans where module is 0
      modulo = [tdi%frequency==0 for tdi in td]
    for idx, tstep in enumerate(time_steps):
      if (not use_t0 and idx==0) or (modulo[idx] is False):
        continue
      # convert time step to time string
      current_time = utils.datetime_to_string(tstep)
      # run unipost step
      self._run_unipost_step(wrfout, current_time, td[idx])


  def _archive_output(self, current_time, thours, domain):
    '''
    rename unipost.exe output to wrfpost_d0${domain}_time.grb and archive
    '''
    import shutil
    # verify that domain is an int
    if not isinstance(domain, int):
      message = 'domain id should be an integer'
      #logger.error(message)
      raise IOError(message)
    # define original and destination filename
    origname = 'WRFPRS%02d.tm00' %thours
    outname = 'wrfpost_d%02d_%s.grb' %(domain, current_time)
    # rename file and move to archive dir
    shutil.move(os.path.join(self.post_dir, origname),
                os.path.join(self.config['filesystem']['upp_archive_dir'], outname))
    # check if file is indeed archived
    utils.check_file_exists(os.path.join(self.config['filesystem']['upp_archive_dir'], outname))

