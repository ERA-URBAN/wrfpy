#!/usr/bin/env python2

import argparse
from netCDF4 import Dataset
from netCDF4 import num2date
import numpy
from geopy.distance import vincenty
from wrfpy.config import config
import f90nml
import os
from datetime import datetime
from numpy import meshgrid as npmeshgrid
from geopy.distance import vincenty
import operator
from numpy import unravel_index
from numpy import shape as npshape
import glob
import statsmodels.api as sm

def reg_m(y, x):
    ones = numpy.ones(len(x[0]))
    X = sm.add_constant(numpy.column_stack((x[0], ones)))
    for ele in x[1:]:
        X = sm.add_constant(numpy.column_stack((ele, X)))
    results = sm.OLS(y, X).fit()
    return results

def find_gridpoint(lat_in, lon_in, lat, lon):
    '''
    lat_in, lon_in: lat/lon coordinate of point of interest
    lat, lon: grid of lat/lon to find closest index of gridpoint
    '''
    # extract window surrounding point
    lon_window = lon[(lon >= lon_in - 0.10) &
                     (lon <= lon_in + 0.10) & 
                     (lat >= lat_in - 0.10) & 
                     (lat <= lat_in + 0.10)]
    lat_window = lat[(lon >= lon_in - 0.10) & 
                     (lon <= lon_in + 0.10) & 
                     (lat >= lat_in - 0.10) & 
                     (lat <= lat_in + 0.10)]

    lonx = lon_window
    latx = lat_window
    # calculate distance to each point in the surrounding window
    distance = [vincenty((lat_in,lon_in),(latx[idx],lonx[idx])).km for idx in range(0,len(lonx))]
    # find index of closest reference station to wunderground station
    try:
      min_index, min_value = min(enumerate(distance), key=operator.itemgetter(1))
      lon_sel, lat_sel = lonx[min_index], latx[min_index]
      # indices of gridpoint
      latidx = lat.reshape(-1).tolist().index(lat_sel)
      lonidx = lon.reshape(-1).tolist().index(lon_sel)
      #print(latidx,lonidx)
      (lat_idx,lon_idx) = unravel_index(latidx, npshape(lon)) 
      return lat_idx, lon_idx
    except ValueError:
      return None, None

class bumpskin(config):
  def __init__(self, filename):
    config.__init__(self)
    self.wrfda_workdir = os.path.join(self.config['filesystem']['work_dir'], 'wrfda')
    # verify input
    self.verify_input(filename)
    # fix urban temperatures in outer domain
    domain = 1
    self.fix_temp(domain)

  def verify_input(self, filename):
    '''
    verify input and create list of files
    '''
    try:
      f = Dataset(filename, 'r')
      f.close()
      self.filelist = [filename]
    except IOError:
      # file is not a netcdf file, assuming a txt file containing a 
      # list of netcdf files
      if os.path.isdir(filename):
        # path is actually a directory, not a file
        self.filelist = glob.glob(os.path.join(filename, '*nc'))
      else:
        # re-raise error
        raise

  def get_time(self, wrfinput):
      '''
      get time from wrfinput file
      '''
      wrfinput = Dataset(wrfinput, 'r')  # open netcdf file
      # get datetime string from wrfinput file
      datestr = ''.join(wrfinput.variables['Times'][0])
      # convert to datetime object
      dtobj = datetime.strptime(datestr, '%Y-%m-%d_%H:%M:%S')
      wrfinput.close()  # close netcdf file
      return dtobj

  def get_urban_temp(self, wrfinput, ams):
    '''
    get urban temperature TC2M
    '''
    wrfinput = Dataset(wrfinput, 'r')  # open netcdf file
    # get datetime string from wrfinput file
    LU_IND = wrfinput.variables['LU_INDEX'][0,:]
    URB_IND = wrfinput.variables['FRC_URB2D'][0,:]
    GLW_IND = wrfinput.variables['GLW'][0,:]
    U10_IND = wrfinput.variables['U10'][0,:]
    V10_IND = wrfinput.variables['V10'][0,:]
    UV10_IND = numpy.sqrt(U10_IND**2 + V10_IND**2)
    lat = wrfinput.variables['XLAT'][0,:]#[LU_IND==1]
    lon = wrfinput.variables['XLONG'][0,:]#[LU_IND==1]
    T2 = []
    U10 = []
    V10 = []
    GLW = []
    LU = []
    #FRC_URB = []
    for point in ams:
      i_idx, j_idx = find_gridpoint(point[0], point[1],lat,lon)
      if (i_idx and j_idx):
        T2.append(wrfinput.variables['T2'][0, i_idx, j_idx])
        U10.append(wrfinput.variables['U10'][0, i_idx, j_idx])
        V10.append(wrfinput.variables['V10'][0, i_idx, j_idx])
        GLW.append(wrfinput.variables['GLW'][0, i_idx, j_idx])
        LU.append(wrfinput.variables['LU_INDEX'][0, i_idx, j_idx])
      else:
        T2.append(numpy.nan)
        U10.append(numpy.nan)
        V10.append(numpy.nan)
        GLW.append(numpy.nan)
        LU.append(numpy.nan)
    wrfinput.close()
    UV10 = numpy.sqrt(numpy.array(U10)**2 + numpy.array(V10)**2)
    return T2, numpy.array(GLW), UV10, numpy.array(LU), LU_IND, GLW_IND, UV10_IND


  def obs_temp(self, dtobj):
    '''
    get observed temperature in amsterdam
    '''
    for f in self.filelist:
      try:
        obs = Dataset(f, 'r')
        dt = obs.variables['time'] 
        dtobj_obs = num2date(dt[:], units=dt.units, calendar=dt.calendar)
        idx = numpy.argsort(abs(dtobj_obs-dtobj))[0]
        if abs((dtobj_obs-dtobj)[idx]).total_seconds() > 900:
          # ignore observation if
          # time difference between model and observation is > 15 minutes
          continue 
        # TODO: support multile obs in 1 file
        try:
          obs_temp = numpy.hstack((obs_temp,
                                  obs.variables['temperature'][idx]))
        except NameError:
          obs_temp = [obs.variables['temperature'][idx]]
        try:
          obs_lon = numpy.hstack((obs_lon,
                                  obs.variables['longitude'][:]))
        except NameError:
          obs_lon = obs.variables['longitude'][:]
        try:
          obs_lat = numpy.hstack((obs_lat,
                                  obs.variables['latitude'][:]))
        except NameError:
          obs_lat = obs.variables['latitude'][:]
        print(f, str(obs.variables['temperature'][idx]-273.15))
        obs.close()
      except IOError:
        pass
      except AttributeError:
        pass
    try:
      obs = zip(obs_lat, obs_lon, obs_temp)
    except UnboundLocalError:
      obs = [()]
    return obs

  def fix_temp(self, domain):
    '''
    calculate increment of urban temperatures and apply increment
    to wrfinput file in wrfda directory
    '''
    # load netcdf files
    wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(domain))
    wrfinput = os.path.join(wrfda_workdir, 'fg')
    # get datetime from wrfinput file
    dtobj = self.get_time(wrfinput)
    # get observed temperatures
    obs = self.obs_temp(dtobj)
    obs_temp = [obs[idx][2] for idx in range(0,len(obs))]
    # get modeled temperatures at location of observation stations
    t_urb, glw, uv10, lu, LU_IND, glw_IND, uv10_IND = self.get_urban_temp(
      wrfinput, obs)
    diffT_station = numpy.array(obs_temp) - numpy.array(t_urb)
    # calculate median and standard deviation, ignore outliers > 10K
    # only consider landuse class 1
    nanmask = (~numpy.isnan(diffT_station)) & (lu==1)
    diffT_station = diffT_station[nanmask]
    lu = lu[nanmask]
    glw = glw[nanmask]
    uv10 = uv10[nanmask] 
    median = numpy.nanmedian(diffT_station[(abs(diffT_station)<10)])
    std = numpy.nanstd(diffT_station[(abs(diffT_station)<10)])
    # depending on the number of observations, calculate the temperature
    # increment differently
    if (len(lu)<3):
      # no temperature increment for <3 observations
      diffT = numpy.zeros(numpy.shape(glw_IND))
    elif ((len(lu) >=3) & (len(lu)<5)):
      # use median if between 3 and 5 observations
      diffT = median * numpy.ones(numpy.shape(glw_IND))
      diffT[LU_IND!=1] = 0
    else:
      # fit statistical model
      # define mask
      mask = (diffT_station > median - 3*std) & (diffT_station < median + 3*std) & (lu==1)
      fit = reg_m(diffT_station[mask], [(glw)[mask], uv10[mask]])
      # calculate diffT for every gridpoint
      if fit.f_pvalue<=0.1:  # use fit if significant
        diffT = fit.params[1] * glw_IND + fit.params[0] * uv10_IND + fit.params[2]
      else:  # use median
        diffT = median * numpy.ones(numpy.shape(glw_IND))
      diffT[LU_IND!=1] = 0  # set to 0 if LU_IND!=1
    self.wrfinput2 = Dataset(os.path.join(wrfda_workdir, 'wrfvar_output'), 'r+')
    # define variables to increment
    variables_2d = ['TC_URB','TR_URB','TB_URB','TG_URB','TS_URB']
    variables_3d = ['TRL_URB','TBL_URB', 'TGL_URB', 'TSLB']
    TC_URB = self.wrfinput2.variables['TC_URB']
    TC_URB[:] = TC_URB[:] + diffT
    TR_URB = self.wrfinput2.variables['TR_URB']
    TR_URB[:] = TR_URB[:] + diffT
    TB_URB = self.wrfinput2.variables['TB_URB']
    TB_URB[:] = TB_URB[:] + diffT
    TG_URB = self.wrfinput2.variables['TG_URB']
    TG_URB[:] = TG_URB[:] + diffT
    TS_URB = self.wrfinput2.variables['TS_URB']
    TS_URB[:] = TS_URB[:] + diffT
    TGR_URB = self.wrfinput2.variables['TGR_URB']
    TGR_URB[:] = TGR_URB[:] + diffT

    TRL_URB = self.wrfinput2.variables['TRL_URB']
    levs = numpy.shape(self.wrfinput2.variables['TRL_URB'][:])[1]
    for lev in range(0,levs):
      if lev == 0:
        TRL_URB[0,lev,:] = TRL_URB[0,lev,:] + diffT * 0.675
      elif lev == 1:
        TRL_URB[0,lev,:] = TRL_URB[0,lev,:] + diffT * 0.038
      elif lev == 2:
        TRL_URB[0,lev,:] = TRL_URB[0,lev,:] + diffT * 0.021
      elif lev == 3:
        TRL_URB[0,lev,:] = TRL_URB[0,lev,:] + diffT * 0.010

    TBL_URB = self.wrfinput2.variables['TBL_URB']
    levs = numpy.shape(self.wrfinput2.variables['TBL_URB'][:])[1]
    for lev in range(0,levs):
      if lev == 0:
        TBL_URB[0,lev,:] = TBL_URB[0,lev,:] + diffT * 0.608
      elif lev == 1:
        TBL_URB[0,lev,:] = TBL_URB[0,lev,:] + diffT * 0.029
      elif lev == 2:
        TBL_URB[0,lev,:] = TBL_URB[0,lev,:] + diffT * 0.013
      elif lev == 3:
        TBL_URB[0,lev,:] = TBL_URB[0,lev,:] + diffT * 0.005

    TGL_URB = self.wrfinput2.variables['TGL_URB']
    levs = numpy.shape(self.wrfinput2.variables['TGL_URB'][:])[1]
    TGL_URB[0,0,:] = TGL_URB[0,0,:] + diffT * 0.435

    #adjustment soil for vegetation fraction urban cell, only first two levels
    TSLB = self.wrfinput2.variables['TSLB']
    levs = numpy.shape(self.wrfinput2.variables['TSLB'][:])[1]
    for lev in range(0,levs):
      if lev == 0:
        TSLB[0,lev,:] = TBL_URB[0,lev,:] + diffT * 0.590
      elif lev == 1:
        TSLB[0,lev,:] = TBL_URB[0,lev,:] + diffT * 0.001
      else:
        pass

    # close netcdf file
    self.wrfinput2.close()


if __name__ == "__main__":
  # define argument menu
  description = ('Push urban temperatures towards observed temperatures in ' +
                 'the urban environmetn')
  parser = argparse.ArgumentParser(description=description)
  parser.add_argument('-f', '--filename',
                      help=('netcdf file with observed temperatures, or ' +
                            ' directory containing a list of netcdf files'),
                      required=True)
  args = parser.parse_args()
  bumpskin(args.filename)
