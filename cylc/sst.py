#!/usr/bin/env python2

from netCDF4 import Dataset
import argparse

class sst:
  def __init__(self, var, file1, file2):
    self.var = var
    self.file1 = file1
    self.file2 = file2
    self.load_files()
    self.change_sst()
    self.close_files()
  def load_files(self):
    self.f1 = Dataset(self.file1, 'r')
    self.f2 = Dataset(self.file2, 'r+')
  def change_sst(self):
    self.f2.variables[self.var][0,:] = self.f1.variables[self.var][:]
  def close_files(self):
    self.f2.close()
    self.f1.close()    

if __name__=="__main__":
  parser = argparse.ArgumentParser(description='change sst')
  parser.add_argument('variable', metavar='N', type=str,
                      help='netcdf variable to change')
  parser.add_argument('netcdf1', metavar='I', type=str,
                      help='first netcdf file')
  parser.add_argument('netcdf2', metavar='J', type=str,
                      help='second netcdf file')
  # parse arguments
  args = parser.parse_args()
  # call main
  sst(args.variable, args.netcdf1, args.netcdf2)

