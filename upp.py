#!/usr/bin/env python3

'''
description:    Unified Post Precession (UPP) part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import utils
import glob

class upp:
  '''
  Runs the Universal Post Processor (UPP) for requested time steps in
  a wrfout file
  '''
  def __init__(self):
  self.logger = get_logger()
  self.logger.info('*** RUNNING UNIVERSAL POST PROCESSOR ***')

  def set_variables(self):
    '''
    Define control variables for the unipost.exe tool, inherit from
    global config. Variables are stored in a dictionary called config
    '''
    domain_dir    = config['domain_dir']
    max_dom       = config['max_dom']
    dom           = config['dom'] # current domain number
    model_run     = config['model_run']
    wrfout_dir    = '%s/%s/wrfout' %(domain_dir, model_run)    
    post_dir      = '%s/%s/postprd' % (domain_dir, model_run)
    wrf_cntrl     = post_dir+'/wrf_cntrl.parm'
    upp_dir       = config['upp_dir']
    wrf_run_dir   = config['wrf_dir']+'/run'
    namelist      = read_namelist(wrf_run_dir+'/namelist.input')
    fcst_times    = get_fcst_times(config)    
    init_time     = fcst_times[0]
    history_interval = config['history_interval']
    remove_wrfout = config['remove_wrfout']
    grb_fmt       = config['grb_fmt']

    config['archive_dir'] = ...
    config['upp_dir'] = 
    config['crtm_dir'] = os.path.join(config['upp_dir'],
                                     'src/lib/crtm2/coefficients')


  def initialize(self):
    '''
    Check if archive dir exists, create if not.
    The archive dir is used to ...
    '''
    archive_dir    = '%s/%s/archive' %(domain_dir,model_run)
    if not os.path.exists(self.config['archive_dir']:
      os.makedirs(self.config['archive_dir'])  # create archive dir
    # TODO: try/except for config['post_dir'] directory


  def prepare_post_dir(self):
    '''
    Create and prepare post_dir
    '''
    self.logger.debug('Preparing postprd directory: %s' %self.config['post_dir'])

    # create config['post_dir'] if it does not exist yet
    try:
      os.makedirs(self.config['post_dir'])
    except OSError as e:
      if e.errno != errno.EEXIST:  # directory already exists
        raise # re-raise exception if a different error occured

    # Link all the relevant files need to compute various diagnostics
    relpath_to_link = ['EmisCoeff/Big_Endian/EmisCoeff.bin',
                       'AerosolCoeff/Big_Endian/AerosolCoeff.bin',
                       'CloudCoeff/Big_Endian/CloudCoeff.bin'
                       'SpcCoeff/Big_Endian/imgr_g12.SpcCoeff.bin'
                       'TauCoeff/Big_Endian/imgr_g12.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/imgr_g11.SpcCoeff.bin'
                       'TauCoeff/Big_Endian/imgr_g11.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/amsre_aqua.SpcCoeff.bin'
                       'TauCoeff/Big_Endian/amsre_aqua.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/tmi_trmm.SpcCoeff.bin'
                       'TauCoeff/Big_Endian/tmi_trmm.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/ssmi_f15.SpcCoeff.bin'
                       'TauCoeff/Big_Endian/ssmi_f15.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/ssmis_f20.SpcCoeff.bin'
                       'TauCoeff/Big_Endian/ssmis_f20.TauCoeff.bin' ]
    abspath_to_link = [ os.path.join(config['crtm_dir'], relpath) for relpath in
                       relpath_to_link ]
    # TODO: extend abspath_to_link with the following:
    # TODO: add symlink for eta_micro_lookup.dat: Ferrier's microphysic's table
    # TODO: add symlink for wrf_cntrl.parm 
    for fl in abspath_to_link:
      utils.check_file_exists(fl)  # check if file exist and is readable
      os.symlink(fl, os.path.join(config['post_dir'], os.path.basename(fl)))


  def set_environment_variables(self):
    '''
    Set environment variables
    '''
    self.logger.debug('Enter set_environment_variables')
    os.environ['MP_SHARED_MEMORY'] = 'yes'
    os.environ['MP_LABELIO'] = 'yes'
    os.environ['tmmark'] = 'tm00'
    self.logger.debug('Leave set_environment_variables')


  def cleanup_output_files(self)
    '''
    Clean up old output files in post_dir
    '''
    self.logger.debug('Enter cleanup_output_files')
    file_ext = [ '*.out', '*.tm00']
    files_found = [ glob.glob(os.path.join(config['post_dir'],
                                           ext for ext in file_ext ]
    # try to remove files, raise exception if needed
    [ utils.silentremove(fl) for fl in files_found ]
    self.logger.debus('Leave cleanup_output_files')


  def write_itag(self, wrfout, current_time):
    '''
    Create input file for unipost
      --------content itag file ---------------------------------------
      First line is location of wrfout data
      Second line is required format
      Third line is the modeltime to process
      Fourth line is the model identifier (WRF, NMM)
      -----------------------------------------------------------------
    '''
    self.logger.debug('Enter write_itag')
    self.logger.debug('Time in itag file is: %s' %current_time)
    filename = os.path.join(config['post_dir'], 'itag')
    silentremove(filename)  # remove old file if it was there
    # template of itag file
    template = """{wrfout}
    netcdf
    {current_time}
    NCAR
    """
    # context variables in template
    context = {
      "wrfout":wrfout,
      "current_time":current_timie
      }
    # create the itag file and write content to it based on the template
    try:
      with open(filename, 'w') as itag:
        itag.write(template.format(**context))
    except IOError as e:
      self.logger.error('Unable to write itag file: %s', %filename)
      raise  # re-raise exception
    self.logger.debug('Leave write_itag')

