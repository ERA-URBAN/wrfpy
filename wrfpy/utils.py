#!/usr/bin/env python3

'''
description:    Utilities used in wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import logging
import sys
import os

# define global LOG variables
DEFAULT_LOG_LEVEL = 'debug'
LOG_LEVELS = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL}
LOG_LEVELS_LIST = LOG_LEVELS.keys()
# LOG_FORMAT = '%(asctime)-15s %(message)s'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
DATE_FORMAT = "%Y/%m/%d/%H:%M:%S"
logger = None


def devnull():
    '''
    define devnull based on python version
    '''
    if sys.version_info >= (3, 3):
        from subprocess import DEVNULL as devnull
    elif sys.version_info >= (2, 4):
        devnull = open(os.devnull, 'wb')
    else:
        assert sys.version_info >= (2, 4)
    return devnull


def silentremove(filename):
    '''
    Remove a file or directory without raising an error if the file or
    directory does not exist
    '''
    import errno
    import shutil
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
            if e.errno == errno.EISDIR:
                shutil.rmtree(filename)
            else:
                raise  # re-raise exception if a different error occured


def return_validate(date_text, format='%Y-%m-%d_%H'):
    '''
    validate date_text and return datetime.datetime object
    '''
    from datetime import datetime
    try:
        date_time = datetime.strptime(date_text, format).replace(tzinfo=None)
    except ValueError:
        logger.error('Incorrect date format, should be %s' % format)
        raise ValueError('Incorrect date format, should be %s' % format)
    return date_time


def check_file_exists(filename, boolean=False):
    '''
    check if file exists and is readable, else raise IOError
    '''
    try:
        with open(filename):
            if boolean:
                return True
            else:
                pass  # file exists and is readable, nothing else to do
    except IOError:
        if boolean:
            return False
        else:
            # file does not exist OR no read permissions
            logger.error('Unable to open file: %s' % filename)
            raise  # re-raise exception


def validate_time_wrfout(wrfout, current_time):
    '''
    Validate if current_time is in wrfout file
    '''
    # get list of timesteps in wrfout file (list of datetime objects)
    time_steps = timesteps_wrfout(wrfout)
    # convert current_time to datetime object
    ctime = return_validate(current_time)
    if ctime not in time_steps:
        message = ('Time ' + current_time + 'not found in wrfout file: ' +
                   wrfout)
        logger.error(message)
        raise ValueError(message)


def timesteps_wrfout(wrfout):
    '''
    return a list of timesteps (as datetime objects) in a wrfout file
    Input variables:
        - wrfout: path to a wrfout file
    '''
    from netCDF4 import Dataset as ncdf
    from datetime import timedelta
    check_file_exists(wrfout)  # check if wrfout file exists
    # read time information from wrfout file
    ncfile = ncdf(wrfout, format='NETCDF4')
    # minutes since start of simulation, rounded to 1 decimal float
    tvar = [round(nc, 0) for nc in ncfile.variables['XTIME'][:]]
    ncfile.close()
    # get start date from wrfout filename
    time_string = wrfout[-19:-6]
    start_time = return_validate(time_string)
    # times in netcdf file
    time_steps = [start_time + timedelta(minutes=step) for step in tvar]
    return time_steps


def datetime_to_string(dtime, format='%Y-%m-%d_%H'):
    '''
    convert datetime object to string. Standard format is 'YYYY-MM-DD_HH'
    Input variables:
        - dtime: datetime object
        - (optional) format: string format to return
    '''
    from datetime import datetime
    # check if dtime is of instance datetime
    if not isinstance(dtime, datetime):
        message = 'input variable dtime is not of type datetime'
        logger.error(message)
        raise IOError(message)
    # return datetime as a string
    return dtime.strftime(format)


def start_logging(filename, level=DEFAULT_LOG_LEVEL):
    '''
    Start logging with given filename and level.
    '''
    global logger
    if logger is None:
        logger = logging.getLogger()
    else:  # wish there was a logger.close()
        for handler in logger.handlers[:]:  # make a copy of the list
            logger.removeHandler(handler)
    logger.setLevel(LOG_LEVELS[level])
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    fh = logging.FileHandler(filename)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def get_logger():
    pass


def datetime_range(start, end, delta):
    '''
    Return a generator of all timesteps between two datetime.date(time)
    objects.
    Time between timesteps is provided by the argument delta.
    '''
    import datetime
    current = start
    if not isinstance(delta, datetime.timedelta):
        try:
            delta = datetime.timedelta(**delta)
        except TypeError:
            message = ('delta argument in utils.datetime_range should be of ',
                       'a mapping of datetime.timedelta type')
            logger.error(message)
            raise TypeError(message)
    while current < end:
        yield current
        current += delta


def excepthook(*args):
    '''
    Replace sys.excepthook with custom handler so any uncaught exception
    gets logged
    '''
    logger.error('Uncaught exception:', exc_info=args)


def _create_directory(path):
    '''
    Create a directory if it does not exist yet
    '''
    import errno
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:  # directory already exists, no problem
            raise  # re-raise exception if a different error occured


def get_wrfpy_path():
    '''
    get the path of wrfpy installation
    '''
    import wrfpy
    return os.path.dirname(os.path.realpath(wrfpy.__file__))


def testjob(j_id):
    import subprocess
    command = "squeue -j %s" % j_id
    output = subprocess.check_output(command.split())
    try:
        if j_id == int(output.split()[-8]):
            return True
        else:
            return False
    except ValueError:
        return False


def testjobsucces(j_id):
    import subprocess
    command = "sacct -j %s --format=state" % j_id
    output = subprocess.check_output(command.split())
    if any(x in ['CANCELED', 'FAILED', 'TIMEOUT'] for x in output.split()):
        raise IOError('slurm command failed')
    else:
        return True

def waitJobToFinish(j_id):
    import time
    while True:
        time.sleep(1)
        if not testjob(j_id):
              testjobsucces(j_id)
              break
    
def convert_cylc_time(string):
        import datetime
        import dateutil.parser
        try:
                return datetime.datetime.strptime(
                    string, '%Y%m%dT%H00+01').replace(tzinfo=None)
        except ValueError:
                return dateutil.parser.parse(string).replace(tzinfo=None)


def get_max_dom(namelist):
        '''
        get maximum domain number from WRF namelist.input
        '''
        import f90nml
        wrf_nml = f90nml.read(namelist)
        # maximum domain number
        return wrf_nml['domains']['max_dom']


def days_hours_minutes_seconds(td):
        ''' return days, hours, minutes, seconds
                input: datetime.timedelta
        '''
        return (td.days, td.seconds//3600, (td.seconds//60) % 60,
                td.seconds % 60)
