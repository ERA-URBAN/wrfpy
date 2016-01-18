#!/usr/bin/env python3

'''
description:    Unified Post Precession (UPP) part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import utils
import glob
import subprocess

class upp:
  '''
  Runs the Universal Post Processor (UPP) for requested time steps in
  a wrfout file
  '''
  def __init__(self):
    self.logger = utils.get_logger()
    self.logger.info('*** RUNNING UNIVERSAL POST PROCESSOR ***')
    self._set_variables()
    self._initialize()
    self._prepare_post_dir()
    self._set_environment_variables()


  def _set_variables(self):
    '''
    Define control variables for the unipost.exe tool, inherit from
    global config. Variables are stored in a dictionary called config
    '''
    # TODO: clean up this mess, inherit global configs
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

    config['upp_archive_dir'] = ...
    config['upp_dir'] = 
    config['crtm_dir'] = os.path.join(config['upp_dir'],
                                     'src/lib/crtm2/coefficients')


  def _initialize(self):
    '''
    Check if archive dir exists, create if not.
    The archive dir is used to ...
    '''
    archive_dir    = '%s/%s/archive' %(domain_dir,model_run)
    if not os.path.exists(self.config['archive_dir']:
      os.makedirs(self.config['archive_dir'])  # create archive dir
    # TODO: try/except for config['post_dir'] directory


  def _prepare_post_dir(self):
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
    relpath_to_link = ['EmisCoeff/Big_Endian/EmisCoeff.bin'
                       'AerosolCoeff/Big_Endian/AerosolCoeff.bin'
                       'CloudCoeff/Big_Endian/CloudCoeff.bin'
                       'SpcCoeff/Big_Endian/imgr_g11.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/imgr_g11.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/imgr_g12.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/imgr_g12.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/imgr_g13.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/imgr_g13.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/imgr_g15.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/imgr_g15.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/imgr_mt1r.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/imgr_mt1r.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/imgr_mt2.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/imgr_mt2.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/imgr_insat3d.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/imgr_insat3d.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/amsre_aqua.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/amsre_aqua.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/tmi_trmm.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/tmi_trmm.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/ssmi_f13.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/ssmi_f13.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/ssmi_f14.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/ssmi_f14.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/ssmi_f15.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/ssmi_f15.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/ssmis_f16.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/ssmis_f16.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/ssmis_f17.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/ssmis_f17.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/ssmis_f18.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/ssmis_f18.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/ssmis_f19.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/ssmis_f19.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/ssmis_f20.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/ssmis_f20.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/seviri_m10.SpcCoeff.bin'
                       'TauCoeff/ODPS/Big_Endian/seviri_m10.TauCoeff.bin'
                       'SpcCoeff/Big_Endian/v.seviri_m10.SpcCoeff.bin']

    # abspath coefficients for crtm2 (simulated synthetic satellites)
    abspath_coeff= [os.path.join(config['crtm_dir'], relpath) for relpath in
                    relpath_to_link ]
    # abspath microphysic's tables - code used is based on mp_physics option
    # used in the wrfout file
    abspath_mf = [os.path.join(config['wrf_run_dir'], mffile) for file in
                  ['ETAMPNEW_DATA nam_micro_lookup.dat',
                   'run/ETAMPNEW_DATA.expanded_rain hires_micro_lookup.dat']]
    # abspath wrf_cntrl param file
    abspath_pf = os.path.join(config['upp_domain_dir'], 'parm',
                              'wrf_cntrl.parm')
    # concatenate lists of paths
    abspath_to_link = abspath_coeff + abspath_mf + abspath_pf
    # create a symlink for every file in abspath_to_link
    for fl in abspath_to_link:
      utils.check_file_exists(fl)  # check if file exist and is readable
      os.symlink(fl, os.path.join(config['post_dir'], os.path.basename(fl)))
    # symlink wrf_cntrl.parm to config['post_dir']/fort.14
    os.symlink(abspath_pf, os.path.join(config['post_dir'], 'fort.14'))


  def _set_environment_variables(self):
    '''
    Set environment variables
    '''
    self.logger.debug('Enter set_environment_variables')
    os.environ['MP_SHARED_MEMORY'] = 'yes'
    os.environ['MP_LABELIO'] = 'yes'
    os.environ['tmmark'] = 'tm00'
    self.logger.debug('Leave set_environment_variables')


  def _cleanup_output_files(self)
    '''
    Clean up old output files in post_dir
    '''
    self.logger.debug('Enter cleanup_output_files')
    file_ext = [ '*.out', '*.tm00', 'fort.*', 'itag']
    files_found = [ glob.glob(os.path.join(config['post_dir'],
                                           ext for ext in file_ext ]
    # try to remove files, raise exception if needed
    [ utils.silentremove(fl) for fl in files_found ]
    self.logger.debus('Leave cleanup_output_files')


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
    self.logger.debug('Enter write_itag')
    self.logger.debug('Time in itag file is: %s' %current_time)
    # set itag filename and cleanup
    filename = os.path.join(config['post_dir'], 'itag')
    silentremove(filename)
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
      self.logger.error('Unable to write itag file: %s', %filename)
      raise  # re-raise exception
    self.logger.debug('Leave write_itag')


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
    domain = wrfout[14:16]
    # write itag file
    self._write_itag(wrfout, current_time)
    # run unipost.exe
    subprocess.check_call(os.path.join(config['upp_dir'], 'bin', 'unipost.exe'),
                          cwd=config['post_dir'])
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
    self._run_unipost_step(wrfout, timestep)
    time_steps = utils.timesteps_wrfout(wrfout)
    # convert to hours since timestep 0
    td = [int((t - t0).total_seconds()/3600) for t in time_steps]
    # modulo  should be zero
    if not td[-1]%frequency==0:
      message = ''  # TODO: add error message
      self.logger.error(message)
      raise IOError(message)
    else:
      # create list of booleans where module is 0
      modulo = [tdi%frequency==0 for tdi in td]
    for idx, tstep in enumerate(time_steps):
      if modulo[idx] is False:
        continue
      # convert time step to time string
      current_time = utils.datetime_to_string(tstep)
      # run unipost step
      _run_unipost_step(wrfout, current_time, td[idx])


  def _archive_output(self, current_time, thours, domain):
    '''
    rename unipost.exe output to wrfpost_d0${domain}_time.grb and archive
    '''
    # verify that domain is a string
    if not isinstance(domain, str):
      message = 'domain id should be a string'
      self.logger.error(message)
      raise IOError(message)
    # define original and destination filename
    origname = 'WRFPRS%03d.tm00' %thours
    outname = 'wrfpost_d%02d_%s.grb' %(domain, current_time)
    # rename file and move to archive dir
    shutil.move(os.path.join(config['post_dir'], origname),
                os.path.join(config['upp_archive_dir'], outname))
    # check if file is indeed archived
    check_file_exists(os.path.join(config['upp_archive_dir'], outname))
