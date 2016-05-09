#!/usr/bin/env python3

'''
description:    boundary part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

def prepare_boundaries():
  # check WPS
  pass
  # clean WPS boundaries
  clean_boundaries_wps()

def clean_boundaries_wps():
  '''
  clean old leftover boundary files in WPS directory
  '''
  files = [ os.path.join(env.WPSDIR, ext) for ext in
           ['GRIBFILE.*', 'FILE:', 'PFILE:', 'PRES:'] ]
  [ silentremove(filename) for filename in files ]

