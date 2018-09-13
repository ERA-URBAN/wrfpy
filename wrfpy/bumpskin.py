#!/usr/bin/env python2

from netCDF4 import Dataset
import numpy
from geopy.distance import vincenty
from wrfpy.config import config
from wrfpy import utils
from wrfpy.readObsTemperature import readObsTemperature
import os
from datetime import datetime
import operator
from numpy import unravel_index
from numpy import shape as npshape
import glob
import statsmodels.api as sm
import csv
import numpy as np
import f90nml
from scipy import interpolate


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
    distance = [vincenty((lat_in, lon_in), (latx[idx], lonx[idx])).km
                for idx in range(0, len(lonx))]
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
    def __init__(self, dtobj, infile):
        config.__init__(self)
        if self.config['options_urbantemps']['ah.csv']:
            ahcsv = self.config['options_urbantemps']['ah.csv']
            self.read_ah_csv(ahcsv, dtobj)
            self.options = self.read_tbl(infile)
            self.change_AH()
            self.write_tbl()

    def read_ah_csv(self, ahcsv, dtobj):
        '''
        read anthropogenic heat from csv file
        columns are: yr, month, ah, alh
        alh column is optional
        '''
        # initialize variables in csv file
        yr = []
        mnth = []
        ah = []
        alh = []  # optional
        # start reading csv file
        with open(ahcsv, 'r') as inp:
            reader = csv.reader(inp)
            next(reader)  # skip header
            for row in reader:
                # append variables
                yr.append(int(row[0]))
                mnth.append(int(row[1]))
                ah.append(float(row[2]))
                try:
                    alh.append(float(row[3]))
                except IndexError:
                    alh.append(None)
        yr = np.array(yr)
        mnth = np.array(mnth)
        ah = np.array(ah)
        alh = np.array(alh)
        self.ah = ah[(yr==dtobj.year) & (mnth==dtobj.month)][0]
        if not float(self.ah)>0:
            self.ah = None
        self.alh = alh[(yr==dtobj.year) & (mnth==dtobj.month)][0]
        if not float(self.alh)>0:
            self.alh = None

    @staticmethod
    def read_tbl(tblfile):
        '''
        Read URBPARM.TBL
        '''
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
        '''
        Write URBPARM.TBL to wrf run directory
        '''
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
                        file.write("{0} : {1}\n".format
                                   (key, ", ".join(str(x)
                                    for x in self.options.get(key))))
                    else:
                        file.write("{0} : {1}\n".format
                                   (key, " ".join(str(x)
                                    for x in self.options.get(key))))
                except TypeError:
                    file.write("{0} : {1}\n".format
                               (key, self.options.get(key)))
        file.close()

    def change_AH(self):
        '''
        Modify anthropogenic heat with ones in csv file
        '''
        if self.ah:
            self.options['AH'][-1] = self.ah
        if self.alh:
            self.options['ALH'][-1] = self.alh




class bumpskin(config):
    def __init__(self, filename, nstationtypes=None, dstationtypes=None):
        config.__init__(self)
        # optional define station types to be used
        self.nstationtypes = nstationtypes  # stationtypes at night
        self.dstationtypes = dstationtypes  # stationtypes during daytime
        self.wrfda_workdir = os.path.join(self.config
                                          ['filesystem']['work_dir'], 'wrfda')
        self.wrf_rundir = self.config['filesystem']['work_dir']
        # verify input
        self.verify_input(filename)
        # get number of domains
        wrf_nml = f90nml.read(self.config['options_wrf']['namelist.input'])
        ndoms = wrf_nml['domains']['max_dom']
        # check if ndoms is an integer and >0
        if not (isinstance(ndoms, int) and ndoms>0):
            raise ValueError("'domains_max_dom' namelist variable should be an " \
                             "integer>0")
        try:
            (lat, lon, diffT) = self.findDiffT(1)
            for domain in range(1, ndoms+1):
                self.applyToGrid(lat, lon, diffT, domain)
        except TypeError:
            pass

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

    @staticmethod
    def getCoords(wrfinput):
        '''
        Return XLAT,XLONG coordinates from wrfinput file
        '''
        wrfinput = Dataset(wrfinput, 'r')  # open netcdf file
        lat = wrfinput.variables['XLAT'][0, :]
        lon = wrfinput.variables['XLONG'][0, :]
        lu_ind = wrfinput.variables['LU_INDEX'][0, :]
        wrfinput.close()
        return (lat,lon, lu_ind)

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
                try:
                    frcurb = wrfinput.variables['FRC_URB2D'][0, i_idx, j_idx]
                    tp2m = wrfinput.variables['TP2M_URB'][0, i_idx, j_idx]
                    tc2m = wrfinput.variables['TC2M_URB'][0, i_idx, j_idx]
                    t2urb = (1-frcurb) * tp2m + frcurb * tc2m
                except KeyError:
                    t2urb = wrfinput.variables['T2'][0, i_idx, j_idx]
                if t2urb < 225:  # defautl back to T2 for non-urb
                    t2urb = wrfinput.variables['T2'][0, i_idx, j_idx]
                T2.append(t2urb)
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

    def findDiffT(self, domain):
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
        obs = readObsTemperature(dtobj, nstationtypes=None,
                                 dstationtypes=None).obs
        obs_temp = [obs[idx][2] for idx in range(0, len(obs))]
        # get modeled temperatures at location of observation stations
        t_urb, glw, uv10, lu, LU_IND, glw_IND, uv10_IND = self.get_urban_temp(
          wrfinput, obs)
        lat, lon, lu_ind = self.getCoords(wrfinput)  # get coordinates
        diffT_station = numpy.array(obs_temp) - numpy.array(t_urb)
        # calculate median and standard deviation, ignore outliers > 10K
        # only consider landuse class 1
        nanmask = ((~numpy.isnan(diffT_station)) & (lu == 1) &
                   (abs(diffT_station) < 5))
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
            # recalculate median
            median = numpy.nanmedian(diffT_station[mask])
            print('deltaT: ', median)
            fit = reg_m(diffT_station[mask], [(glw)[mask], uv10[mask]])
            # calculate diffT for every gridpoint
            if fit.f_pvalue <= 0.1:  # use fit if significant
                diffT = (fit.params[1] * glw_IND +
                         fit.params[0] * uv10_IND + fit.params[2])
            else:  # use median
                diffT = median * numpy.ones(numpy.shape(glw_IND))
            diffT[LU_IND != 1] = 0  # set to 0 if LU_IND!=1
            return (lat, lon, diffT)

    def applyToGrid(self, lat, lon, diffT, domain):
        # load netcdf files
        wrfda_workdir = os.path.join(self.wrfda_workdir, "d0" + str(domain))
        wrfinputFile = os.path.join(wrfda_workdir, 'wrfvar_output')
        lat2, lon2, lu_ind2 = self.getCoords(wrfinputFile)
        # get datetime from wrfinput file
        dtobj, datestr = self.get_time(wrfinputFile)
        # if not ((lat==lat2) and (lon==lon2)) we need to interpolate
        if not (np.array_equal(lat, lat2) and np.array_equal(lon, lon2)):
            # do interpolation to get new diffT
            diffT = interpolate.griddata((lon.reshape(-1), lat.reshape(-1)), diffT.reshape(-1),
                                         (lon2.reshape(-1),lat2.reshape(-1)),
                                          method='cubic').reshape(np.shape(lon2))
            diffT[lu_ind2 != 1] = 0  # set to 0 if LU_IND!=1
        # open wrfvar_output (output after data assimilation)
        self.wrfinput2 = Dataset(os.path.join(wrfda_workdir, 'wrfvar_output'),
                                 'r+')
        # open wrfvar_input (input before DA (last step previous run)
        start_date = utils.return_validate(
          self.config['options_general']['date_start'])
        if (dtobj == start_date):  # very first timestep
            self.wrfinput3 = Dataset(os.path.join
                                     (self.wrf_rundir,
                                      ('wrfinput_d0' + str(domain))), 'r')
            return
        else:
            self.wrfinput3 = Dataset(os.path.join
                                     (self.wrf_rundir,
                                      ('wrfvar_input_d0' + str(domain) +
                                       '_' + datestr)), 'r')
        # define variables to increment
        # variables_2d = ['TC_URB', 'TR_URB', 'TB_URB', 'TG_URB', 'TS_URB']
        # variables_3d = ['TRL_URB', 'TBL_URB', 'TGL_URB', 'TSLB']
        # begin determining multiplying factor
        rhocp = 1231
        uc_urb = self.wrfinput2.variables['UC_URB'][:]
        lp_urb = self.wrfinput2.variables['BUILD_AREA_FRACTION'][:]
        hgt_urb = self.wrfinput2.variables['BUILD_HEIGHT'][:]
        lb_urb = self.wrfinput2.variables['BUILD_SURF_RATIO'][:]
        frc_urb = self.wrfinput2.variables['FRC_URB2D'][:]
        chc_urb = self.wrfinput2.variables['CHC_SFCDIF'][:]
        R = numpy.maximum(numpy.minimum(lp_urb/frc_urb, 0.9), 0.1)
        RW = 1.0 - R
        HNORM = 2. * hgt_urb * frc_urb / (lb_urb - lp_urb)
        HNORM[lb_urb <= lp_urb] = 10.0
        ZR = numpy.maximum(numpy.minimum(hgt_urb, 100.0), 3.0)
        h = ZR / HNORM
        W = 2 * h
        # set safety margin on W/RW >=8 or else SLUCM could misbehave
        # make sure to use the same safety margin in module_sf_urban.F
        W[(W / RW) < 8.0] = ((8.0 / (W / RW)) * W)[(W / RW) < 8.0]
        CW = numpy.zeros(numpy.shape(uc_urb))
        CW[uc_urb > 5] = 7.51 * uc_urb[uc_urb > 5]**0.78
        CW[uc_urb <= 5] = 6.15 + 4.18 * uc_urb[uc_urb <= 5]
        DTW = diffT * (1 + ((RW * rhocp) / (W + RW)) * (chc_urb/CW))

        diffT = DTW  # change 09/01/2018
        diffT = numpy.nan_to_num(diffT)  # replace nan by 0
        # apply temperature changes
        TSK = self.wrfinput2.variables['TSK']
        TSK[:] = TSK[:] + diffT
        TB_URB = self.wrfinput2.variables['TB_URB']
        TB_URB[:] = TB_URB[:] + diffT
        TG_URB = self.wrfinput2.variables['TG_URB']
        TG_URB[:] = TG_URB[:] + diffT
        TS_URB = self.wrfinput2.variables['TS_URB']
        TS_URB[:] = TS_URB[:] + diffT
        TGR_URB = self.wrfinput2.variables['TGR_URB']
        TGR_URB[:] = TGR_URB[:] + diffT

        # wall layer temperature
        try:
            TBL_URB_factors = self.config['options_urbantemps']['TBL_URB']
        except KeyError:
            # fallback values if none are defined in config
            # these may not work correctly for other cities than Amsterdam
            TBL_URB_factors = [0.823, 0.558, 0.379, 0.257]
        if not (isinstance(TBL_URB_factors, list) and
                len(TBL_URB_factors) > 1):
            TBL_URB_factors = [0.823, 0.558, 0.379, 0.257]
        TBL_URB = self.wrfinput2.variables['TBL_URB']
        levs = numpy.shape(self.wrfinput2.variables['TBL_URB'][:])[1]
        TBL_URB = self.wrfinput2.variables['TBL_URB']
        for lev in range(0, levs):
            try:
                TBL_URB[0, lev, :] = (TBL_URB[0, lev, :] + 
                                      diffT * float(TBL_URB_factors[lev]))
            except IndexError:
                # no factor for this layer => no increment
                pass

        # road layer temperature
        try:
            TGL_URB_factors = self.config['options_urbantemps']['TGL_URB']
        except KeyError:
            # fallback values if none are defined in config
            # these may not work correctly for other cities than Amsterdam
            TGL_URB_factors = [0.776, 0.170, 0.004]
        if not (isinstance(TGL_URB_factors, list) and
                len(TGL_URB_factors) > 1):
            TGL_URB_factors = [0.776, 0.170, 0.004]
        TGL_URB = self.wrfinput2.variables['TGL_URB']
        levs = numpy.shape(self.wrfinput2.variables['TGL_URB'][:])[1]
        TGL_URB = self.wrfinput2.variables['TGL_URB']
        for lev in range(0, levs):
            try:
                TGL_URB[0, lev, :] = (TGL_URB[0, lev, :] + 
                                      diffT * float(TGL_URB_factors[lev]))
            except IndexError:
                # no factor for this layer => no increment
                pass

        #  adjustment soil for vegetation fraction urban cell
        try:
            TSLB_factors = self.config['options_urbantemps']['TSLB']
        except KeyError:
            # fallback values if none are defined in config
            # these may not work correctly for other cities than Amsterdam
            TSLB_factors = [0.507, 0.009]
        if not (isinstance(TSLB_factors, list) and
                len(TSLB_factors) > 1):
            TSLB_factors = [0.507, 0.009]
        TSLB = self.wrfinput2.variables['TSLB']  # after update_lsm
        TSLB_in = self.wrfinput3.variables['TSLB']  # before update_lsm
        levs = numpy.shape(self.wrfinput2.variables['TSLB'][:])[1]
        for lev in range(0, levs):
            # reset TSLB for urban cells to value before update_lsm
            TSLB[0, lev, :][lu_ind2 == 1] = TSLB_in[0, lev, :][lu_ind2 == 1]
            try:
                TSLB[0, lev, :] = TSLB[0, lev, :] + diffT * float(TSLB_factors[lev])
            except IndexError:
                pass

        # close netcdf file
        self.wrfinput2.close()
        self.wrfinput3.close()
