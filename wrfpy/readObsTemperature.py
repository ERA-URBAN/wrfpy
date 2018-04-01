#!/usr/bin/env python

##
from wrfpy.config import config
import csv
import os
import astral
from netCDF4 import Dataset
from netCDF4 import date2num
import numpy as np
import bisect
from datetime import datetime
import glob


class readObsTemperature(config):
    def __init__(self, dtobj, nstationtypes=None, dstationtypes=None):
        config.__init__(self)
        # optional define station types to be used
        self.nstationtypes = nstationtypes  # stationtypes at night
        self.dstationtypes = dstationtypes  # stationtypes during daytime
        # define datestr
        datestr = datetime.strftime(dtobj, '%Y-%m-%d_%H:%M:%S')
        # define name of csv file
        self.wrf_rundir = self.config['filesystem']['work_dir']
        fname = 'obs_stations_' + datestr + '.csv'
        self.csvfile = os.path.join(self.wrf_rundir, fname)
        try:
            # try to read an existing csv file
            self.read_csv(datestr)
        except IOError:
            if self.config['options_urbantemps']['urban_stations']:
                # reading existing csv file failed, start from scratch
                self.urbStations = self.config['options_urbantemps']['urban_stations']
                self.verify_input()
                self.obs_temp(dtobj)
                self.write_csv(datestr)
            else:
                raise

    def verify_input(self):
        '''
        verify input and create list of files
        '''
        try:
            f = Dataset(self.urbStations, 'r')
            f.close()
            self.filelist = [self.urbStations]
        except IOError:
            # file is not a netcdf file, assuming a txt file containing a 
            # list of netcdf files
            if os.path.isdir(self.urbStations):
                # path is actually a directory, not a file
                self.filelist = glob.glob(os.path.join(self.urbStations, '*nc'))
            else:
                # re-raise error
                raise

    def obs_temp(self, dtobj):
        '''
        get observed temperature in amsterdam
        '''
        obs_lon = []
        obs_lat = []
        obs_temp = []
        obs_stype = []
        obs_sname = []
        for f in self.filelist:
            try:
                obs = Dataset(f, 'r')
                lon = obs.variables['longitude'][0]
                lat = obs.variables['latitude'][0]
                elevation = 0
                try:
                    stationtype = obs.stationtype
                except AttributeError:
                    stationtype = None
                stobs = (lat, lon, elevation, stationtype)
                use_station = self.filter_stationtype(stobs, dtobj)
                if use_station:
                    dt = obs.variables['time']
                    # convert datetime object to dt.units units
                    dtobj_num = date2num(dtobj, units=dt.units,
                                         calendar=dt.calendar)
                    # make use of the property that the array is already
                    #  sorted to find the closest date
                    ind = bisect.bisect_left(dt[:], dtobj_num)
                    if (ind == 0):
                        continue
                    else:
                        am = np.argmin([abs(dt[ind]-dtobj_num),
                                        abs(dt[ind-1]-dtobj_num)])
                        if (am == 0):
                            idx = ind
                        else:
                            idx = ind - 1
                    if abs((dt[:]-dtobj_num)[idx]) > 900:
                        # ignore observation if time difference
                        # between model and observation is > 15 minutes
                        continue
                    temp = obs.variables['temperature'][idx]
                    sname = f[:]  # stationname
                    obs.close()
                    # append results to lists
                    obs_lon.append(lon)
                    obs_lat.append(lat)
                    obs_temp.append(temp)
                    obs_stype.append(stationtype)
                    obs_sname.append(sname)
            except IOError:
                pass
            except AttributeError:
                pass
        try:
            self.obs = zip(obs_lat, obs_lon, obs_temp, obs_stype, obs_sname)
        except UnboundLocalError:
            self.obs = [()]

    def filter_stationtype(self, stobs, dtobj):
        '''
        check if it is day or night based on the solar angle
        construct location
        '''
        lat = stobs[0]
        lon = stobs[1]
        elevation = 0  # placeholder
        loc = astral.Location(info=('name', 'region', lat, lon, 'UTC',
                                    elevation))
        solar_elevation = loc.solar_elevation(dtobj)
        # set stime according to day/night based on solar angle
        if (solar_elevation > 0):
            stime = 'day'
        else:
            stime = 'night'
        if ((stime == 'day') and self.dstationtypes):
            try:
                mask = any([x.lower() in stobs[3].lower() for
                            x in self.dstationtypes])
            except AttributeError:
                mask = False
        elif ((stime == 'night') and self.nstationtypes):
            try:
                mask = any([x.lower() in stobs[3].lower() for
                            x in self.nstationtypes])
            except AttributeError:
                mask = False
        else:
            mask = True
        return mask

    def write_csv(self, datestr):
        '''
        write output of stations used to csv file
        '''
        with open(self.csvfile, 'wb') as out:
            csv_out = csv.writer(out)
            csv_out.writerow(['lat', 'lon', 'temperature', 'stationtype',
                              'stationname'])
            for row in self.obs:
                csv_out.writerow(row)

    def read_csv(self, datestr):
        '''
        read station temperatures from csv file
        '''
        # initialize variables in csv file
        obs_lat = []
        obs_lon = []
        obs_temp = []
        obs_stype = []
        obs_sname = []
        # start reading csv file
        with open(self.csvfile, 'r') as inp:
            reader = csv.reader(inp)
            next(reader)  # skip header
            for row in reader:
                # append variables
                obs_lat.append(float(row[0]))
                obs_lon.append(float(row[1]))
                obs_temp.append(float(row[2]))
                obs_stype.append(str(row[3]))
                obs_sname.append(str(row[4]))
        # zip variables
        self.obs = zip(obs_lat, obs_lon, obs_temp, obs_stype, obs_sname)
