#!/usr/bin/env python2

from netCDF4 import Dataset
from netCDF4 import num2date
import numpy
from geopy.distance import vincenty
from config import config
import f90nml
import os
from datetime import datetime
from numpy import meshgrid as npmeshgrid
from geopy.distance import vincenty
import operator
from numpy import unravel_index
from numpy import shape as npshape

def find_gridpoint(lat_in, lon_in, lat, lon):
    '''
    lat_in, lon_in: lat/lon coordinate of point of interest
    lat, lon: grid of lat/lon to find closest index of gridpoint
    '''
    # extract window surrounding point
    #lon_window = lon[(lon >= lon_in - 0.10) & (lon <= lon_in + 0.10)]
    #lat_window = lat[(lat >= lat_in - 0.10) & (lat <= lat_in + 0.10)]
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
    # create meshgrid
    #lonx, latx = npmeshgrid(lon_window,lat_window)
    # reshape to one dimensional arrays
    #lonx = lonx.reshape(-1)
    #latx = latx.reshape(-1)
    # calculate distance to each point in the surrounding window
    #distance = [sqrt((lon_in_t-lonx[idx])**2 + (lat_in_t-latx[idx])**2) for idx
    #            in range(0,len(lonx))]
    distance = [vincenty((lat_in,lon_in),(latx[idx],lonx[idx])).km for idx in range(0,len(lonx))]
    # find index of closest reference station to wunderground station
    min_index, min_value = min(enumerate(distance), key=operator.itemgetter(1))
    lon_sel, lat_sel = lonx[min_index], latx[min_index]
    # indices of gridpoint
    latidx = lat.reshape(-1).tolist().index(lat_sel)
    lonidx = lon.reshape(-1).tolist().index(lon_sel)
    #print(latidx,lonidx)
    (lat_idx,lon_idx) = unravel_index(latidx, npshape(lon)) 
    return lat_idx, lon_idx


class bumpskin(config):
  def __init__(self):
    config.__init__(self)
    # read WRF namelist in WRF work_dir
    wrf_nml = f90nml.read(self.config['options_wrf']['namelist.input'])
    # get number of domains
    ndoms = wrf_nml['domains']['max_dom']
    # check if ndoms is an integer and >0
    if not (isinstance(ndoms, int) and ndoms>0):
      raise ValueError("'domains_max_dom' namelist variable should be an " \
                      "integer>0")
    self.wrfda_workdir = os.path.join(self.config['filesystem']['work_dir'],
                                      'wrfda')
    for dom in range(1, ndoms+1):
      self.fix_temp(dom)


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
    #import pdb; pdb.set_trace()
    #T2 = wrfinput.variables['T2'][0,:][LU_IND==1]
    lat = wrfinput.variables['XLAT'][0,:]#[LU_IND==1]
    lon = wrfinput.variables['XLONG'][0,:]#[LU_IND==1]
    T2 = []
    FRC_URB = []
    for point in ams:
      i_idx, j_idx = find_gridpoint(point[0], point[1],lat,lon)
      T2.append(wrfinput.variables['T2'][0, i_idx, j_idx])
      FRC_URB.append(wrfinput.variables['FRC_URB2D'][0, i_idx, j_idx])
    wrfinput.close()
    return T2, FRC_URB, LU_IND, URB_IND


  def ams_temp(self, dtobj):
    '''
    get observed temperature in amsterdam
    '''
    ams = Dataset('/home/haren/daobs2/all.nc', 'r')
    dt = ams.variables['time'] 
    dtobj_ams = num2date(dt[:], units=dt.units, calendar=dt.calendar)
    #idx=numpy.argsort([abs(a.total_seconds()) for a in dtobj_ams-dtobj])[0]
    idx = numpy.argsort(abs(dtobj_ams-dtobj))[0]
    ams_temp = 273.15 + ams.variables['temperature'][idx,:]
    p50 = numpy.percentile(ams_temp, 50) 
    latitude = ams.variables['lat'][(ams_temp>p50 - 5) & (ams_temp<p50 + 5)]
    longitude = ams.variables['lon'][(ams_temp>p50 - 5) & (ams_temp<p50 + 5)]
    ams_temp = ams_temp[(ams_temp>p50 - 5) & (ams_temp<p50 + 5)]
    ams.close()
    return zip(latitude, longitude, ams_temp)
    #return ams_temp


  def fix_temp(self, domain):
    '''
    description
    '''
    # load netcdf files
    wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(domain))
    wrfinput = os.path.join(wrfda_workdir, 'fg')
    dtobj = self.get_time(wrfinput)
    ams = self.ams_temp(dtobj)[:-5]
    ams_temp = [ams[idx][2] for idx in range(0,len(ams))]
    t_urb, frc_urb, LU_IND, URB_IND = self.get_urban_temp(wrfinput, ams)
    diffT_station = numpy.array(ams_temp) - numpy.array(t_urb)
    pf = numpy.polyfit(frc_urb, diffT_station,deg=1)  # fix y = a + bx
    diffT = pf[1] + pf[0] * URB_IND
    diffT[LU_IND!=1] = 0  # set to 0 if LU_IND!=1
    self.wrfinput2 = Dataset(os.path.join(wrfda_workdir, 'wrfvar_output'), 'r+')
    # 
    variables_2d = ['TSK', 'TC_URB','TR_URB','TB_URB','TG_URB','TS_URB']
    variables_3d = ['TRL_URB','TBL_URB', 'TGL_URB'] 
    TSK = self.wrfinput2.variables['TSK']
    TSK[:] = TSK[:] + diffT
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
      TRL_URB[0,lev,:] = TRL_URB[0,lev,:] + diffT

    TBL_URB = self.wrfinput2.variables['TBL_URB']
    levs = numpy.shape(self.wrfinput2.variables['TBL_URB'][:])[1]
    for lev in range(0,levs):
      TBL_URB[0,lev,:] = TBL_URB[0,lev,:] + diffT

    TGL_URB = self.wrfinput2.variables['TGL_URB']
    levs = numpy.shape(self.wrfinput2.variables['TGL_URB'][:])[1]
    for lev in range(0,levs):
      TGL_URB[0,lev,:] = TGL_URB[0,lev,:] + diffT

    self.wrfinput2.close()


if __name__ == "__main__":
  bumpskin()
