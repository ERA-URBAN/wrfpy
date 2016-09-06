#!/usr/bin/env python2

from netCDF4 import Dataset
import numpy
from geopy.distance import vincenty
from config import config


class wrfda_imbalance(config):
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
    for dom in range(1, ndoms):
      cdomain = dom + 1
      self.read_init(dom, cdomain)
      self.method="boundary"
      self.fix_2d_field('PSFC')
      self.fix_3d_field('P', 'T')
      self.cleanup()


  def read_init(self, pdom, cdom):
    '''
    Read lon/lat information from netCDF files
    '''
    # load netcdf files
    self.wrfinput1 = Dataset(os.path.join(
                             self.config['filesystem']['wrf_run_dir'],
                             'wrfinput_d' + str(pdom).zfill(2)), 'r')
    self.wrfinput2 = Dataset(os.path.join(
                             self.config['filesystem']['wrf_run_dir'],
                             'wrfinput_d' + str(cdom).zfill(2)), 'r+')
    # lon/lat information parent domain
    XLONG1 = self.wrfinput1.variables['XLONG'][:]
    XLAT1 = self.wrfinput1.variables['XLAT'][:]
    self.area1 = calculate_area(XLAT1, XLONG1)
    # convert to an average lon/lat array to simplify computation
    self.xlon = numpy.mean(XLONG1[0,:],axis=0)
    self.xlat = numpy.mean(XLAT1[0,:], axis=1)
    # lon/lat information child domain
    XLONG2 = self.wrfinput2.variables['XLONG'][:]
    XLAT2 = self.wrfinput2.variables['XLAT'][:]
    self.area2 = calculate_area(XLAT2, XLONG2)
    # min/max longitude and latitude of child domain
    self.XLONG2MIN = numpy.min(XLONG2[0,:],axis=None)
    self.XLONG2MAX = numpy.max(XLONG2[0,:],axis=None)
    self.XLAT2MIN = numpy.min(XLAT2[0,:],axis=None)
    self.XLAT2MAX = numpy.max(XLAT2[0,:],axis=None)


  def fix_3d_field(self,  *variables):
    '''
    Handle 3d fields
    '''
    for variable in variables:
      # read variables
      var1 = (self.wrfinput1.variables[variable][
              0,:,(self.XLAT2MIN<self.xlat) & (self.xlat<self.XLAT2MAX),
              (self.XLONG2MIN<self.xlon) & (self.xlon<self.XLONG2MAX)])
      self.var2 = self.wrfinput2.variables[variable]
      self.get_weights()
      if self.method=="domain":
        # average difference wrt parent domain
        diff_var = (numpy.average(
                    var1,axis=tuple([1,2]),weights=numpy.ones(
                    numpy.shape(var1))*self.sm_area1) - numpy.average(
                    self.var2[:], axis=tuple([2,3]),
                    weights=numpy.ones(numpy.shape(self.var2))*self.area2)[0])
      elif self.method=="boundary":
        # calculate average difference only along the boundary
        b1 = numpy.hstack((var1[:,-1,:],var1[:,1,:],var1[:,:,-1],var1[:,:,1]))
        b2 = numpy.hstack((self.var2[0,:,-1,:],self.var2[0,:,1,:],
                           self.var2[0,:,:,-1],self.var2[0,:,:,1]))
        diff_var = (numpy.average(b1,axis=1,weights=self.w1) -
                    numpy.average(b2[:], axis=1, weights=self.w2))
      else:
        # oops
        pass
      # add average difference to child domain
      self.var2[:] = (numpy.swapaxes([self.var2[:,level,:] + diff_var[level]
                      for level in range(0,len(diff_var))], 0, 1))


  def fix_2d_field(self, *variables):
    '''
    Handle surface fields
    '''
    for variable in variables:
      # read variables
      var1 = (self.wrfinput1.variables[variable][
              0,(self.XLAT2MIN<self.xlat) & (self.xlat<self.XLAT2MAX),
              (self.XLONG2MIN<self.xlon) & (self.xlon<self.XLONG2MAX)])
      self.var2 = self.wrfinput2.variables[variable]
      self.get_weights()
      # average difference wrt parent domain 
      if self.method=="domain":
        diff_var = (numpy.average(var1,axis=None, weights=self.sm_area1) -
                    numpy.average(self.var2[0,:],
                    axis=None, weights=self.area2))
      elif self.method=="boundary":
        # calculate average difference only along the boundary
        b1 = numpy.hstack((var1[-1,:],var1[1,:],var1[:,-1],var1[:,1]))
        b2 = numpy.hstack((self.var2[0,-1,:], self.var2[0,1,:],
                           self.var2[0,:,-1],self.var2[0,:,1]))
        diff_var = (numpy.average(b1,weights=self.w1) -
                    numpy.average(b2[:], weights=self.w2))
      else:
        # oops
        pass
      # add average difference to child domain
      self.var2[:] = self.var2 + diff_var


  def get_weights(self):
    '''
    return boundary area weights
    '''
    try:
      self.sm_area1
    except AttributeError:
      self.sm_area1 = (self.area1[
                       (self.XLAT2MIN<self.xlat) & (self.xlat<self.XLAT2MAX),:]
                       [:,(self.XLONG2MIN<self.xlon)
                        & (self.xlon<self.XLONG2MAX)])
    if self.method=="boundary":
      try:
        self.w1
      except AttributeError:
        self.w1 = numpy.hstack((self.sm_area1[-1,:], self.sm_area1[1,:],
                                self.sm_area1[:,-1],self.sm_area1[:,1]))
      try:
        self.w2
      except AttributeError:
        self.w2 = numpy.hstack((self.area2[-1,:], self.area2[1,:],
                                self.area2[:,-1],self.area2[:,1]))


  def cleanup(self):
    '''
    close netcdf files and write changes
    '''
    self.wrfinput2.close()
    self.wrfinput1.close()
    del self.sm_area1, self.w1, self.w2


def calculate_area(XLAT, XLONG):
  '''
  calculate area from lat & lon arrays
  in: XLONG: nxn array of longitude for each grid point
      XLAT: nxn array of latitude for each grid point
  out: area: nxn array of area of each grid point (in km)
  '''
  dist1 = [[vincenty(
            (XLAT[0,lat,lon],XLONG[0,lat,lon]),
            (XLAT[0,lat+1,lon],XLONG[0,lat+1,lon])).km if
            lat<numpy.shape(XLAT)[1]-1 else vincenty(
            (XLAT[0,lat-1,lon],XLONG[0,lat-1,lon]),
            (XLAT[0,lat,lon],XLONG[0,lat,lon])).km for lat in 
            range(0,numpy.shape(XLAT)[1])] for lon in
            range(0,numpy.shape(XLONG)[2])]
  dist2 = [[vincenty((XLAT[0,lat,lon],XLONG[0,lat,lon]),
            (XLAT[0,lat,lon+1],XLONG[0,lat,lon+1])).km if
            lon<numpy.shape(XLAT)[2]-1 else vincenty(
            (XLAT[0,lat,lon-1],XLONG[0,lat,lon-1]),
            (XLAT[0,lat,lon],XLONG[0,lat,lon])).km for lat in
            range(0,numpy.shape(XLAT)[2])] for lon in
            range(0,numpy.shape(XLONG)[2])]
  area = numpy.array(dist1) * numpy.array(dist2)
  return area


if __name__ == "__main__":
  wrfda_imbalance()
