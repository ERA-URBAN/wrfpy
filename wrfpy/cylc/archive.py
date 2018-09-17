#!/usr/bin/env python

from netCDF4 import Dataset as ncdf
from netCDF4 import date2num
import datetime
import pandas
from numpy import diff as npdiff
import numpy
import time
import os
from dateutil import relativedelta
import argparse
import f90nml
import shutil
from wrfpy.config import config
from wrfpy import utils

class postprocess(config):
  def __init__(self, datestart, dateend):
    config.__init__(self)
    self.startdate = datestart
    self.enddate = dateend
    # read WRF namelist in WRF work_dir
    wrf_nml = f90nml.read(self.config['options_wrf']['namelist.input'])
    # get number of domains
    self.ndoms = wrf_nml['domains']['max_dom']
    self.rundir = self.config['filesystem']['wrf_run_dir']
    # archive in subdir per year
    self.archivedir = os.path.join(self.config['filesystem']['archive_dir'],
                                   str(self.startdate.year))
    utils._create_directory(self.archivedir)
    # define static variables
    self.define_vars_static()
    # define variables that need to be stored hourly
    self.define_vars_hourly()
    # define variables that need to be stored every minute for the most inner
    # domain, hourly for the other domains
    self.define_vars_minute()
    self.define_vars_deac()  # define variables to be deaccumulated
    self.archive()  # archive "normal" variables
    self.archive_wrfvar_input()  # archive wrfvar_input files
    # get start_date from config.json
    start_date = utils.return_validate(
      self.config['options_general']['date_start'])
    if (start_date == datestart):  # very first timestep
      self.archive_static()  # archive static variables
    self.cleanup()

  def define_vars_hourly(self):
    '''
    create dict of outputstream:variable for output that has to be saved every
    hour
    '''
    self.hour_var = [
          #'P_TOP',
          #'ZNU',
          #'ZNW',
          'VEGFRA', #change in time
          'MU',
          'MUB',
          'Q2',
          'T2',
          'TH2',
          'PSFC',
          'U10',
          'V10',
          'GRDFLX',
          'ACSNOM',
          'SNOW',
          'SNOWH',
          'CANWAT',
          'TC2M_URB',
          'TP2M_URB',
          'LAI',
          'VAR',
          'F',
          'E',
          'TSK',
          'SWDOWN',
          'GLW',
          'SWNORM',
          'ALBEDO',
          'ALBBCK',
          'EMISS',
          'NOAHRES',
          'UST',
          'PBLH',
          'HFX',
          'LH',
          'SNOWC',
          'OLR',
          'SFCEXC',   # SURFACE EXCHANGE COEFFICIENT, does change
          'Z0',
          'SST',
          'U',
          'V',
          'W',
          'PH',
          'PHB',
          'T',
          'P',
          'PB',
          'P_HYD', # Hydrostatic pressure. keep in archive altough differences are small. I cannot derive it from the geopotential.
          'QVAPOR',
          'QCLOUD',
          'QRAIN',
          'QICE',
          'QSNOW',
          'QGRAUP',
          'CLDFRA',
          'TSLB',
          'SMOIS',
          #'SH20',
          'SMCREL']

  def define_vars_static(self):
    '''
    Static variables.
    Run only once on the very first timestep
    '''
    self.static_var = [
          'ZS',
          'DZS',
          'XLAND', #LAND MASK (1 FOR LAND, 2 FOR WATER)
          'TMN']

  def define_vars_minute(self):
    '''
    create dict of outputstream:variable for output that has to be saved every
    minute for the inner domain
    '''
    self.minute_var = [
      'SFROFF',
      'UDROFF',
      'QFX',
      'SR',
      'RAINNC',
      'SNOWNC',
      'GRAUPELNC',
      'HAILNC']

  def define_vars_deac(self):
    self.deac_var = [
      'SNOWNC',
      'RAINNC',
      'SFROFF',
      'UDROFF',
      'SNOWC',
      'GRAUPELNC',
      'HAILNC']

  def write_netcdf(self, var, inpdata, lat, lon, dt, dim, outfile):
    '''
    Write netcdf output file
    '''
    # open output file
    ncfile = ncdf(outfile, 'w')
    # create dimensions and variables
    if dim == 3:
      ncfile.createDimension('time', len(dt))
      ncfile.createDimension('south_north', numpy.shape(inpdata)[1])
      ncfile.createDimension('west_east', numpy.shape(inpdata)[2])
      data = ncfile.createVariable(var,'f4',
                                   ('time', 'south_north', 'west_east',),
                                   zlib=True, fill_value=-999)
    elif dim == 4:
      ncfile.createDimension('time', len(dt))
      ncfile.createDimension('bottom_top', numpy.shape(inpdata)[1])
      ncfile.createDimension('south_north', numpy.shape(inpdata)[2])
      ncfile.createDimension('west_east', numpy.shape(inpdata)[3])
      data = ncfile.createVariable(var,'f4',
                                   ('time', 'bottom_top',
                                    'south_north', 'west_east',),
                                   zlib=True, fill_value=-999)
    data1 = ncfile.createVariable('latitude', 'f4',
                                  ('south_north', 'west_east',), zlib=True)
    data2 = ncfile.createVariable('longitude', 'f4',
                                  ('south_north', 'west_east',), zlib=True)
    timevar = ncfile.createVariable('time', 'f4', ('time',), zlib=True)
    # time axis UTC
    dt = [date2num(d.to_datetime(), units='minutes since 2010-01-01 00:00:00',
                   calendar='gregorian') for d in dt]
    # define attributes
    timevar.units = 'minutes since 2010-01-01 00:00:00'
    timevar.calendar = 'gregorian'
    timevar.standard_name = 'time'
    timevar.long_name = 'time in UTC'
    data1.units = 'degree_east'
    data1.standard_name = 'longitude'
    data1.FieldType = 104
    data1.description = "longitude, west is negative"  #check
    data1.MemoryOrder = "XY"
    data1.coordinates = "lon lat"
    data2.units = 'degree_north'
    data2.standard_name = 'latitude'
    data2.description = 'latitude, south is negative'
    data2.FieldType = 104
    data2.MemoryOrder = "XY"
    data2.coordinates = "lon lat"
    try:
      data[:] = inpdata[:]
    except IndexError:
      raise
    # lat/lon should be a static field
    try:
      data1[:] = lat[0,:]
      data2[:] = lon[0,:]
    except IndexError:
      raise
    timevar[:] = dt
    # Add global attributes
    ncfile.history = 'Created ' + time.ctime(time.time())
    ncfile.close()

  def archive(self):
    '''
    archive standard output files
    '''
    # loop over all domains
    for domain in range(1, self.ndoms + 1):
      # get lat/lon information from wrfout
      datestr_fn = self.startdate.strftime('%Y-%m-%d_%H:%M:%S')
      wrfout_n = 'wrfout_d0' + str(domain) + '_' + datestr_fn
      wrfout = ncdf(os.path.join(self.rundir, wrfout_n), 'r')
      lat = wrfout.variables['XLAT'][:]
      lon = wrfout.variables['XLONG'][:]
      lat_u = wrfout.variables['XLAT_U'][:]
      lon_u = wrfout.variables['XLONG_U'][:]
      lat_v = wrfout.variables['XLAT_V'][:]
      lon_v = wrfout.variables['XLONG_V'][:]
      wrfout.close()
      # iterate over all variables that need to be archived
      for var in (self.hour_var + self.minute_var):
        print(var)
        output_fn = var + '_d0' + str(domain) + '_' + datestr_fn + '.nc'
        output_file = os.path.join(self.archivedir, output_fn)
        for cdate in pandas.date_range(self.startdate, self.enddate, freq='2H')[:-1]:
          datestr_in = cdate.strftime('%Y-%m-%d_%H:%M:%S')
          # define and load input file
          input_fn = var + '_d0' + str(domain) + '_' + datestr_in
          input_file = os.path.join(self.rundir, input_fn)
          ncfile = ncdf(input_file, 'r')
          # read variable and close netCDF file
          tmp = ncfile.variables[var][:]
          ncfile.close()
          # combine steps from input files
          if var in self.deac_var:
            # need to deaccumulate this variable
            try:
              output = numpy.vstack((output, npdiff(tmp, axis=0)))
            except NameError:
              output = numpy.vstack((tmp[0,:][numpy.newaxis,:], npdiff(tmp, axis=0)))
          else:
            # variable only needs appending
            try:
              output = numpy.vstack((output, tmp[1:]))
            except NameError:
              output = tmp
        # find number of dimensions (3d/4d variable)
        dim = numpy.ndim(tmp)
        del tmp  # cleanup
        # define time variable in output file
        if (var in self.minute_var) and (domain == self.ndoms):
          # minute variable in inner domain => minute output
          dt = pandas.date_range(self.startdate, self.enddate, freq='1min')[:]
        else:
          # else hourly output
          dt = pandas.date_range(self.startdate, self.enddate, freq='1H')[:]
        # write netcdf outfile
        if var=='U':
          self.write_netcdf(var, output, lat_u, lon_u, dt, dim, output_file)
        elif var=='V':
          self.write_netcdf(var, output, lat_v, lon_v, dt, dim, output_file)
        else:
          self.write_netcdf(var, output, lat, lon, dt, dim, output_file)
        del output

  def archive_wrfvar_input(self):
    '''
    archive wrfvar_input files
    '''
    # loop over all domains
    wrfvar_archivedir = os.path.join(self.archivedir, 'wrfvar')
    utils._create_directory(wrfvar_archivedir)
    start_date = utils.return_validate(
        self.config['options_general']['date_start'])
    for domain in range(1, self.ndoms + 1):
      # iterate over all variables that need to be archived
        for cdate in pandas.date_range(self.startdate, self.enddate, freq='2H')[:-1]:
          if (cdate != start_date):
            datestr_in = cdate.strftime('%Y-%m-%d_%H:%M:%S')
            # define and load input file
            input_fn = 'wrfvar_input' + '_d0' + str(domain) + '_' + datestr_in
            input_file = os.path.join(self.rundir, input_fn)
            output_file = os.path.join(wrfvar_archivedir, input_fn)
            # copy wrfvar_input to archive dir
            shutil.copyfile(input_file, output_file)

  def archive_static(self):
    '''
    archive non-changing files
    '''
    # loop over all domains
    static_archivedir = os.path.join(self.archivedir, 'static')
    utils._create_directory(static_archivedir)
    for domain in range(1, self.ndoms + 1):
      # iterate over all variables that need to be archived
      for var in self.static_var:
        datestr_in = self.startdate.strftime('%Y-%m-%d_%H:%M:%S')
        # define and load input file
        input_fn = var + '_d0' + str(domain) + '_' + datestr_in
        input_file = os.path.join(self.rundir, input_fn)
        output_file = os.path.join(static_archivedir, input_fn)
        # copy wrfvar_input to archive dir
        shutil.copyfile(input_file, output_file)

  def cleanup(self):
    '''
    cleanup files in WRF run directory
    '''
    # loop over all domains
    for domain in range(1, self.ndoms + 1):
      # iterate over all variables that need to be archived
      #for var in (self.hour_var + self.minute_var + ['wrfout', 'wrfvar_input']):
      for var in (self.hour_var + self.minute_var + ['wrfvar_input']):
        for cdate in pandas.date_range(self.startdate, self.enddate, freq='2H')[:-1]:
          datestr_in = cdate.strftime('%Y-%m-%d_%H:%M:%S')
          # define and load input file
          input_fn = var + '_d0' + str(domain) + '_' + datestr_in
          input_file = os.path.join(self.rundir, input_fn)
          utils.silentremove(input_file)

def main(datestring):
    '''
    Main function to call archive class
    '''
    dt = utils.convert_cylc_time(datestring)
    postprocess(dt-relativedelta.relativedelta(days=1), dt)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize obsproc.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    # parse arguments
    args = parser.parse_args()
    # call main
    main(args.datestring)
