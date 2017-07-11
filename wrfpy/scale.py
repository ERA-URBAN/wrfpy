#!/usr/bin/env python

from scipy import interpolate
from netCDF4 import Dataset
import os
import numpy as np
import shutil
import f90nml
from wrfpy.config import config

class wrfda_interpolate(config):
  def __init__(self):
    config.__init__(self)
    # read WRF namelist in WRF work_dir
    wrf_nml = f90nml.read(self.config['options_wrf']['namelist.input'])
    self.wrfda_workdir = os.path.join(self.config['filesystem']['work_dir'],
                                      'wrfda')
    # get number of domains
    ndoms = wrf_nml['domains']['max_dom']
    # check if ndoms is an integer and >0
    if not (isinstance(ndoms, int) and ndoms>0):
      raise ValueError("'domains_max_dom' namelist variable should be an " \
                      "integer>0")
    doms = range(2, ndoms+1)
    for dom in doms:
      pdomain = 1
      self.read_init(dom, pdomain)
      self.fix_2d_field('ALBBCK', 'CANWAT', 'MU', 'PSFC', 'SST', 'TMN', 'TSK')
      self.fix_3d_field('P', 'PH', 'SH2O', 'SMOIS', 'T', 'TSLB', 'W', 'QVAPOR')
      try:
        if self.config['options_general']['fix_urban_temps']:
          print("incrementing urban temperatures")
          # calculate 0/1 matrix for urban cells
          self.urb = np.zeros(np.shape(self.wrfinput_c.variables['LU_INDEX'][0,:]))
          self.urb[self.wrfinput_c.variables['LU_INDEX'][0,:]==1] = 1
          self.fix_2d_field('TC_URB','TR_URB','TB_URB','TG_URB','TS_URB')
          self.fix_3d_field('TRL_URB','TBL_URB', 'TGL_URB', 'TSLB')
      except KeyError:
        pass
      self.fix_3d_field_uv(self.XLAT_U_p, self.XLONG_U_p, self.XLAT_U_c, self.XLONG_U_c, 'U')
      self.fix_3d_field_uv(self.XLAT_V_p, self.XLONG_V_p, self.XLAT_V_c, self.XLONG_V_c, 'V')
    if ndoms > 1:
      self.cleanup()

  def read_init(self, cdom, pdom):
    c_wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(cdom))
    p_wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(pdom))
    self.fg_p = Dataset(os.path.join(p_wrfda_workdir, 'fg'), 'r')
    self.wrfinput_p = Dataset(os.path.join(p_wrfda_workdir, 'wrfvar_output'), 'r')
    shutil.copyfile(os.path.join(c_wrfda_workdir, 'fg'), os.path.join(c_wrfda_workdir, 'wrfvar_output'))
    self.wrfinput_c = Dataset(os.path.join(c_wrfda_workdir, 'wrfvar_output'), 'r+')
    # lon/lat information parent domain
    self.XLONG_p = self.wrfinput_p.variables['XLONG'][0,:]
    self.XLAT_p = self.wrfinput_p.variables['XLAT'][0,:]
    # lon/lat information child domain
    self.XLONG_c = self.wrfinput_c.variables['XLONG'][0,:]
    self.XLAT_c = self.wrfinput_c.variables['XLAT'][0,:]
    # lon/lat information parent domain
    self.XLONG_U_p = self.wrfinput_p.variables['XLONG_U'][0,:]
    self.XLAT_U_p = self.wrfinput_p.variables['XLAT_U'][0,:]
    # lon/lat information child domain
    self.XLONG_U_c = self.wrfinput_c.variables['XLONG_U'][0,:]
    self.XLAT_U_c = self.wrfinput_c.variables['XLAT_U'][0,:]
    # V
    # lon/lat information parent domain
    self.XLONG_V_p = self.wrfinput_p.variables['XLONG_V'][0,:]
    self.XLAT_V_p = self.wrfinput_p.variables['XLAT_V'][0,:]
    # lon/lat information child domain
    self.XLONG_V_c = self.wrfinput_c.variables['XLONG_V'][0,:]
    self.XLAT_V_c = self.wrfinput_c.variables['XLAT_V'][0,:]

  def fix_2d_field(self, *variables):
    for variable in variables:
      var =  self.wrfinput_p.variables[variable][0,:] - self.fg_p.variables[variable][0,:]
      intp_var = interpolate.griddata((self.XLONG_p.reshape(-1),self.XLAT_p.reshape(-1)), var.reshape(-1), (self.XLONG_c.reshape(-1),self.XLAT_c.reshape(-1)), method='nearest').reshape(np.shape(self.XLONG_c))
      # for urban variables, only increment where LU_INDEX==1
      if variable in ['TC_URB','TR_URB','TB_URB','TG_URB','TS_URB']:
        # only increment urban cells with LU_INDEX==1
        intp_var = intp_var * self.urb
      self.wrfinput_c.variables[variable][:] += intp_var

  def fix_3d_field(self, *variables):
    for variable in variables:
      var =  self.wrfinput_p.variables[variable][0,:] - self.fg_p.variables[variable][0,:]
      intp_var = [interpolate.griddata((self.XLONG_p.reshape(-1),self.XLAT_p.reshape(-1)), var[lev,:].reshape(-1), (self.XLONG_c.reshape(-1),self.XLAT_c.reshape(-1)), method='nearest').reshape(np.shape(self.XLONG_c)) for lev in range(0,len(var))]
      if variable in ['TRL_URB','TBL_URB', 'TGL_URB']:
        intp_var = [np.array(intp_var)[lev,:] * self.urb for lev in range(0, len(var))]
      self.wrfinput_c.variables[variable][:] += intp_var

  def fix_3d_field_uv(self,XLAT_p, XLONG_p, XLAT_c, XLONG_c, *variables):
    for variable in variables:
      var =  self.wrfinput_p.variables[variable][0,:] - self.fg_p.variables[variable][0,:]
      intp_var = [interpolate.griddata((XLONG_p.reshape(-1),XLAT_p.reshape(-1)), var[lev,:].reshape(-1), (XLONG_c.reshape(-1),XLAT_c.reshape(-1)), method='nearest').reshape(np.shape(XLONG_c)) for lev in range(0,len(var))]
      self.wrfinput_c.variables[variable][:] += intp_var

  def cleanup(self):
    '''
    close netcdf files and write changes
    '''
    self.wrfinput_p.close()
    self.wrfinput_c.close()
    self.fg_p.close()

if __name__=="__main__":
  wrfda_interpolate()
