#!/usr/bin/env python2

from netCDF4 import Dataset
from netCDF4 import date2num
import bisect
import numpy
from geopy.distance import vincenty
from wrfpy.config import config
from wrfpy import utils
import os
from datetime import datetime
import operator
from numpy import unravel_index
from numpy import shape as npshape
import glob
import statsmodels.api as sm
import astral
import csv


def return_float_int(value):
    try:
        return int(value.strip(','))
    except ValueError:
        return float(value.strip(','))


def convert_to_number(list):
    if len(list) == 0:
        return list
    elif len(list) == 1:
        return return_float_int(list[0])
    elif len(list) > 1:
        return [return_float_int(value) for value in list]
    else:
        return list


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
        distance = [vincenty((lat_in, lon_in), (latx[idx], lonx[idx])).km for
                    idx in range(0, len(lonx))]
        # find index of closest reference station to wunderground station
        try:
            min_index, min_value = min(enumerate(distance),
                                       key=operator.itemgetter(1))
            lat_sel = latx[min_index]
            # indices of gridpoint
            latidx = lat.reshape(-1).tolist().index(lat_sel)
            (lat_idx, lon_idx) = unravel_index(latidx, npshape(lon))
            return lat_idx, lon_idx
        except ValueError:
            return None, None


class urbparm(config):
    def __init__(self, dt, deltaT, infile):
        config.__init__(self)
        self.options = self.read_tbl(infile)
        self.change_AH(dt, deltaT)
        self.write_tbl()

    @staticmethod
    def read_tbl(tblfile):
        COMMENT_CHAR = '#'
        OPTION_CHAR = ':'
        # process GEOGRID.TBL
        options = {}
        with open(tblfile) as openfileobject:
            for line in openfileobject:
                # First, remove comments:
                if COMMENT_CHAR in line:
                    # split on comment char, keep only the part before
                    line, comment = line.split(COMMENT_CHAR, 1)
                # Second, find lines with an option=value:
                if OPTION_CHAR in line:
                    # split on option char:
                    option, value = line.split(OPTION_CHAR, 1)
                    # strip spaces:
                    option = option.strip()
                    value = convert_to_number(value.strip().split())
                    # store in dictionary:
                    options[option] = value
        return options

    def write_tbl(self):
        outfile = os.path.join(self.config['filesystem']['wrf_run_dir'],
                               'URBPARM.TBL')
        # remove outfile if exists
        utils.silentremove(outfile)
        # write new outfile
        file = open(outfile, 'w')
        space_sep = ['HSEQUIP', 'AHDIUPRF', 'ALHDIUPRF']
        for key in self.options.keys():
            if key not in ['STREET PARAMETERS', 'BUILDING HEIGHTS']:
                try:
                    if key not in space_sep:
                        file.write("{0} : {1}\n".format(
                            key, ", ".join(str(x) for x in
                                           self.options.get(key))))
                    else:
                        file.write("{0} : {1}\n".format(
                            key, " ".join(str(x) for x in
                                          self.options.get(key))))
                except TypeError:
                        file.write("{0} : {1}\n".format(
                            key, self.options.get(key)))
        file.close()

    def change_AH(self, dt, deltaT):
        '''
        # define hours local time in AHDIURPF
        hours = [x%24 for x in range(1,25)]
        # convert dt to local time
        from_zone = tz.gettz('UTC')
        to_zone = tz.gettz('Europe/Amsterdam')
        dt = dt.replace(tzinfo=from_zone)
        for hour in range(0, int(self.config['options_general']['run_hours'])):
            ctime = dt + timedelta(hours=hour)
            local = ctime.astimezone(to_zone)
            diuprf_index = hours.index(local.hour)
            # set factor for 1 for current time step
            self.options['AHDIUPRF'][diuprf_index] = 1.0
            # compute AH that we need
        '''
        ah = [self.options['AH'][-1] * x for x in self.options['AHDIUPRF']]
        added = 32.0 * deltaT
        self.options['AHDIUPRF'] = numpy.around((ah+added)/max(ah+added), 2)
        self.options['AH'][-1] = numpy.around(max(ah+added), 2)
        self.options['AHDIUPRF'][self.options['AHDIUPRF'] < 0] = 0.001
        self.options['AH'][self.options['AH'] < 0] = 0.1
        print('deltaT: ', deltaT)
        print('AHDIUPRF: ', self.options['AHDIUPRF'])
        print('AH: ', self.options['AH'])


class bumpskin(config):
    def __init__(self, filename, nstationtypes=None, dstationtypes=None):
        config.__init__(self)
        self.nstationtypes = nstationtypes
        self.dstationtypes = dstationtypes
        self.wrfda_workdir = os.path.join(
            self.config['filesystem']['work_dir'], 'wrfda')
        self.wrf_rundir = self.config['filesystem']['work_dir']
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
            return dtobj, datestr

    def get_urban_temp(self, wrfinput, ams):
        '''
        get urban temperature TC2M
        '''
        wrfinput = Dataset(wrfinput, 'r')  # open netcdf file
        # get datetime string from wrfinput file
        LU_IND = wrfinput.variables['LU_INDEX'][0, :]
        GLW_IND = wrfinput.variables['GLW'][0, :]
        U10_IND = wrfinput.variables['U10'][0, :]
        V10_IND = wrfinput.variables['V10'][0, :]
        UV10_IND = numpy.sqrt(U10_IND**2 + V10_IND**2)
        lat = wrfinput.variables['XLAT'][0, :]
        lon = wrfinput.variables['XLONG'][0, :]
        T2 = []
        U10 = []
        V10 = []
        GLW = []
        LU = []
        for point in ams:
            i_idx, j_idx = find_gridpoint(point[0], point[1], lat, lon)
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
        return (T2, numpy.array(GLW), UV10, numpy.array(LU), LU_IND,
                GLW_IND, UV10_IND)

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
                    # sorted to find the closest date
                    ind = bisect.bisect_left(dt[:], dtobj_num)
                    if ind == 0:
                        continue
                    else:
                        am = numpy.argmin([abs(dt[ind]-dtobj_num),
                                          abs(dt[ind-1]-dtobj_num)])
                        if am == 0:
                            idx = ind
                        else:
                            idx = ind - 1
                    if abs((dt[:]-dtobj_num)[idx]) > 900:
                        # ignore observation if
                        # time difference between model and observation
                        # is > 15 minutes
                        continue
                    temp = obs.variables['temperature'][idx]
                    sname = f[:]  # stationname
                    # print(f, str(temp-273.15))
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
            obs = zip(obs_lat, obs_lon, obs_temp, obs_stype, obs_sname)
        except UnboundLocalError:
            obs = [()]
        return obs

    def filter_stationtype(self, stobs, dtobj):
        # check if it is day or night based on the solar angle
        # construct location
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

    def write_csv(self, data, datestr):
        '''
        write output of stations used to csv file
        '''
        self.wrf_rundir = self.config['filesystem']['work_dir']
        fname = 'obs_stations_' + datestr + '.csv'
        outfile = os.path.join(self.wrf_rundir, fname)
        with open(outfile, 'wb') as out:
            csv_out = csv.writer(out)
            csv_out.writerow(['lat', 'lon', 'temperature', 'stationtype',
                              'stationname'])
            for row in data:
                csv_out.writerow(row)

    def fix_temp(self, domain):
        '''
        calculate increment of urban temperatures and apply increment
        to wrfinput file in wrfda directory
        '''
        # load netcdf files
        wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(domain))
        wrfinput = os.path.join(wrfda_workdir, 'wrfvar_output')
        # get datetime from wrfinput file
        dtobj, datestr = self.get_time(wrfinput)
        # get observed temperatures
        obs = self.obs_temp(dtobj)
        obs_temp = [obs[idx][2] for idx in range(0, len(obs))]
        # get modeled temperatures at location of observation stations
        t_urb, glw, uv10, lu, LU_IND, glw_IND, uv10_IND = self.get_urban_temp(
            wrfinput, obs)
        diffT_station = numpy.array(obs_temp) - numpy.array(t_urb)
        # calculate median and standard deviation, ignore outliers > 10K
        # only consider landuse class 1
        nanmask = (~numpy.isnan(diffT_station)) & (lu == 1) & (
                   abs(diffT_station) < 5)
        obs = numpy.array(obs)
        obs = obs[nanmask]
        diffT_station = diffT_station[nanmask]
        lu = lu[nanmask]
        glw = glw[nanmask]
        uv10 = uv10[nanmask]
        median = numpy.nanmedian(diffT_station[(abs(diffT_station) < 5)])
        std = numpy.nanstd(diffT_station[(abs(diffT_station) < 5)])
        print('print diffT station')
        print(diffT_station[(abs(diffT_station) < 5)])
        print('end print diffT station')
        # depending on the number of observations, calculate the temperature
        # increment differently
        if (len(lu) < 3):
            # no temperature increment for <3 observations
            diffT = numpy.zeros(numpy.shape(glw_IND))
        elif ((len(lu) >= 3) & (len(lu) < 5)):
            # use median if between 3 and 5 observations
            diffT = median * numpy.ones(numpy.shape(glw_IND))
            diffT[LU_IND != 1] = 0
        else:
            # fit statistical model
            # define mask
            mask = ((diffT_station > median - 2*std) &
                    (diffT_station < median + 2*std) &
                    (lu == 1) & (abs(diffT_station) < 5))
            # filter obs
            obs = obs[mask]
            self.write_csv(obs, datestr)
            # recalculate median
            median = numpy.nanmedian(diffT_station[mask])
            fit = reg_m(diffT_station[mask], [(glw)[mask], uv10[mask]])
            # calculate diffT for every gridpoint
            if fit.f_pvalue <= 0.1:  # use fit if significant
                diffT = fit.params[1] * glw_IND + fit.params[0] * uv10_IND + fit.params[2]
            else:  # use median
                diffT = median * numpy.ones(numpy.shape(glw_IND))
            diffT[LU_IND != 1] = 0  # set to 0 if LU_IND!=1
        # open wrfvar_output (output after data assimilation)
        self.wrfinput2 = Dataset(os.path.join(
                                 wrfda_workdir, 'wrfvar_output'), 'r+')
        # open wrfvar_input (input before data assimulation)
        start_date = utils.return_validate(
            self.config['options_general']['date_start'])
        if (dtobj == start_date):  # very first timestep
            self.wrfinput3 = Dataset(os.path.join(
                                     self.wrf_rundir,
                                     ('wrfinput_d0' + str(domain))), 'r')
        else:
            self.wrfinput3 = Dataset(os.path.join(
                                     self.wrf_rundir,
                                     ('wrfvar_input_d0' + str(domain) +
                                      '_' + datestr)), 'r')
        # define variables to increment
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
        for lev in range(0, levs):
            if lev == 0:
                TRL_URB[0, lev, :] = TRL_URB[0, lev, :] + diffT * 0.811
            elif lev == 1:
                TRL_URB[0, lev, :] = TRL_URB[0, lev, :] + diffT * 0.657
            elif lev == 2:
                TRL_URB[0, lev, :] = TRL_URB[0, lev, :] + diffT * 0.532
            elif lev == 3:
                TRL_URB[0, lev, :] = TRL_URB[0, lev, :] + diffT * 0.432

        TBL_URB = self.wrfinput2.variables['TBL_URB']
        levs = numpy.shape(self.wrfinput2.variables['TBL_URB'][:])[1]
        for lev in range(0, levs):
            if lev == 0:
                TBL_URB[0, lev, :] = TBL_URB[0, lev, :] + diffT * 0.803
            elif lev == 1:
                TBL_URB[0, lev, :] = TBL_URB[0, lev, :] + diffT * 0.645
            elif lev == 2:
                TBL_URB[0, lev, :] = TBL_URB[0, lev, :] + diffT * 0.518
            elif lev == 3:
                TBL_URB[0, lev, :] = TBL_URB[0, lev, :] + diffT * 0.416

        TGL_URB = self.wrfinput2.variables['TGL_URB']
        levs = numpy.shape(self.wrfinput2.variables['TGL_URB'][:])[1]
        for lev in range(0, levs):
            if lev == 0:
                TGL_URB[0, lev, :] = TGL_URB[0, lev, :] + diffT * 0.740
            elif lev == 1:
                TGL_URB[0, lev, :] = TGL_URB[0, lev, :] + diffT * 0.164
            elif lev == 2:
                TGL_URB[0, lev, :] = TGL_URB[0, lev, :] + diffT * 0.008
            else:  
                pass

        # adjustment soil for vegetation fraction urban cell,
        # only first three levels
        TSLB = self.wrfinput2.variables['TSLB']  # after update_lsm
        TSLB_in = self.wrfinput3.variables['TSLB']  # before update_lsm
        levs = numpy.shape(self.wrfinput2.variables['TSLB'][:])[1]
        for lev in range(0, levs):
            # reset TSLB for urban cells to value before update_lsm
            TSLB[0, lev, :][LU_IND == 1] = TSLB_in[0, lev, :][LU_IND == 1]
            # apply diffT for first and second level
            if lev == 0:
                TSLB[0, lev, :] = TSLB[0, lev, :] + diffT * 0.679
            elif lev == 1:
                TSLB[0, lev, :] = TSLB[0, lev, :] + diffT * 0.098
            elif lev == 2:
                TSLB[0, lev, :] = TSLB[0, lev, :] + diffT * 0.004
            else:
                pass

        # close netcdf file
        self.wrfinput2.close()
        self.wrfinput3.close()
        self.median = median
