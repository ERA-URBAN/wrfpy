#!/usr/bin/env python

'''
description:    Database part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''
import sqlite3
import utils
import os
import datetime

class database:
  '''
  description
  '''
  def __init__(self):
    # set some config variables for now for testing purposes
    global config
    config = {}
    config['dbase_dir'] = './'
    config['dbase_name'] = 'wrfpy.db'
    self.database = os.path.join(config['dbase_dir'], config['dbase_name'])

  def _new_database(self):
    '''
    create and connect to a new sqlite database. 
    raise an error if there already is a database in place, asking the
    user to manually remove the database (for safety reasons)
    '''
    # TODO: remove next two lines after testing -> don't automatically remove
    if os.path.exists(self.database):
      os.remove(self.database)
    if os.path.exists(self.database):
      message = ('Database already exists, please remove manually: %s'
                 %self.database)
      logger.error(message)
      raise IOError(message)
    else:
      logger.info('Database not found, creating database %s' %self.database)
      try:
        self.connection = sqlite3.connect(
          self.database,
          detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
      except:
        message = 'Failed to create database: %s' %self.database
        logger.error(message)
        raise sqlite3.OperationalError(message) # re-raise error
      self._create_dbstructure()
      sqlite3.register_adapter(bool, int)
      sqlite3.register_converter("BOOLEAN", lambda v: bool(int(v)))
      # tuples
      self.connection.row_factory = sqlite3.Row

  def _connect_to_database(self):
    '''
    check if database exists and try to connect to the database
    '''
    utils.check_file_exists(self.database)  # check if database exists
    try:
      logger.debug('Connecting to database: %s' %self.database)
      self.connection = sqlite3.connect(
        self.database,
        detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    except:
      message = 'Database %s exists, but failed to connect' %self.database
      logger.error(message)
      raise


  def _close_connection(self):
    '''
    close connection to database
    '''
    try:
      logger.debug('Closing database connection')
      self.connection.close()
    except NameError:
      logger.error(('Failed to close database connection, '
                    'variable does not exist'))


  def _create_dbstructure(self):
    '''
    create database structure
    '''
    #  self.connection.row_factory = sqlite3.Row  # use dict instread of tuple
    self.cursor = self.connection.cursor()
    # create table
    self.cursor.execute('''CREATE TABLE steps
                           (timestep TIMESTAMP, pass BOOLEAN)''')
    self.cursor.execute('''CREATE TABLE finished
                           (timestep TIMESTAMP, pass BOOLEAN)''')
    self.cursor.execute('''CREATE TABLE tasks
                           (timestep TIMESTAMP, task1 BOOLEAN, task2 BOOLEAN,
                           task3 BOOLEAN)''')


  def _add_timestep_to_db(self, timestep):
    '''
    add data to table
    '''
    if not isinstance(timestep, datetime.datetime):
      message = ('database._add_timestemp_to_db input variable dtime is '
                 'not of type datetime')
      logger.error(message)
      raise IOError(message)
    #self.cursor.execute('''INSERT INTO steps(timestep) VALUES (?)''',
    #                    (timestep,))
    logger.info('Adding timestep %s to database' %timestep)
    self.cursor.execute('''INSERT INTO steps VALUES (?,?)''',
                        (timestep, False))
    self.cursor.execute('''INSERT INTO tasks VALUES (?,?,?,?)''',
                        (timestep, False, False, False))
    self.connection.commit()


  def _add_steps_to_db(self):
    '''
    Each interval consists of a number of steps, add the steps to the
    database
    '''
    pass


  def create_list_datetimes(self, start_date, end_date, nhours):
    '''
    Create a list of timesteps between start_date and end_date with a 
    time interval of nhours.
    Add timesteps to database
    '''
    from datetime import datetime
    from datetime import timedelta
    if not(isinstance(start_date, datetime) and isinstance(end_date, datetime)):
      message = ('input start_date and end_date of function ',
                 'create_list_datetimes should be datetime.datetime objects')
      logger.error(message)
      raise IOError(message)
    if not(isinstance(nhours, int)):
      message = ('nhours input argement of create_list_datetimes should be ',
                 'an integer number of hours')
      logger.error(message)
      raise IOError(message)
    # check if the frequency between boundary conditions is not larger than the
    # period between start and end date of the simulation
    if ((nhours*3600) > (end_date - start_date).total_seconds()):
      message = ('Interval of boundary conditions larger than timedelta ',
                 'between start_date and end_date in function ',
                 'database.create_list_datetimes')
      logger.error(message)
      raise IOError(message)
    timesteps = utils.datetime_range(start_date, end_date, {'hours':nhours})
    for idx,timestep in enumerate(timesteps):
      self._add_timestep_to_db(timestep)


  def testcode(self):
    # small code for testing TODO: delete testing code
    #-# start testing code
    for i in [0,1,2,3]:
      self.cursor.execute("SELECT timestep FROM steps WHERE pass=(?)", (False,))
      # first timestep that didn't finish yet
      data = self.cursor.fetchone()[0]
      # update pass=True for timestep
      self.cursor.execute("UPDATE steps SET pass=(?) WHERE timestep=(?)",
                          (True,data,))
    # commit changes
    self.connection.commit()


if __name__=="__main__":
  logger = utils.start_logging('test.log')
  db = database()
  db._new_database()
  #db._connect_to_database()
  start_date = datetime.datetime(2014,07,16,0)
  end_date = datetime.datetime(2014,07,20,0)
  db.create_list_datetimes(start_date, end_date, nhours=1)
  db.testcode()
  #db._add_timesteps_to_db()
  db._close_connection()
  exit()
