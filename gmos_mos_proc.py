# -*- coding: utf-8 -*-
"""
Created on Wed Jul 27 14:25:37 2016

@author: rarnason
"""

import sys
import copy
import os
from pyraf import iraf
from pyraf.iraf import gemini, gemtools, gmos, onedspec
import fileSelect as fs

def gmos_mos_proc():
    '''
    Modified version of the GMOS Data Reduction Cookbook companion script to the chapter:
    "Reduction of Multi-Object Spectra with IRAF"

    PyRAF script to:
    Process MOS exposures for Sculptor Dwarf field 1, in program GN-2008-B-Q-025

    The names for the relevant header keywords and their expected values are
    described in the DRC chapter entitled "Supplementary Material"

    Perform the following starting in the parent work directory:
        cd /path/to/work_directory

    Place the fileSelect.py module in your work directory. Now execute this
    script from the unix prompt:
        python gmos_img_proc.py
    '''
    print ("### Begin Processing GMOS/MOS Spectra ###")
    print (' ')
    print ("---> You must have the MDF files:")
    print ("--->    GS2008BQ025-01.fits and GS2008BQ025-02.fits")
    print ("---> in your work directory. ")
    print (' ')
    print ("=== Creating MasterCals ===")
    
    
    dbFile='raw/obsLog.sqlite3'
        
    #Create query dictionaries for the science observations at each CentWave       
    qdf_1_520 = {'use_me':1,
           'CcdBin':'4 2',
           'DateObs':'2008-09-10:2008-12-12',
           #'DateObs':'2008-10-20:2008-11-21',
           'Instrument':'GMOS-S',
           'Disperser':'B600+_%',
           'AperMask':'GS2008BQ025-01',
           'CentWave':520.0,
           'Object':'Sculptor-field1',
           'RoI':'Full'
           }
    
    qdf_1_5225 = copy.deepcopy(qdf_1_520)
    qdf_1_5225['CentWave'] = 522.5
    qdf_1_525 = copy.deepcopy(qdf_1_520)
    qdf_1_525['CentWave'] = 525.0
    #Create query dictionaries for the standard star observation
    qd_std = copy.deepcopy(qdf_1_520)
    qd_std['AperMask'] = '1.0arcsec'
    qd_std['Object'] = 'LTT1020'
    
    print (" --Creating Bias MasterCal-- ")
    
    #Use primarily the default task parameters
    gemtools.gemextn.unlearn()    # Disarm a bug in gbias
    gmos.gbias.unlearn()
    #gmos.gbias.logfile = 'biasLog.txt'
    #gmos.gbias.rawpath = './raw/'
    #gmos.gbias.fl_vardq = 'yes'
    #gmos.gbias.verbose = 'no'
    biasFlags = {
        'logfile':'biasLog.txt','rawpath':'./raw/','fl_vardq':'yes',    
        'verbose':'no'
    }    

    #This SQL query generates the list of full-frame files to process     
    SQL = fs.createQuery('bias', qdf_1_520)
    biasFull = fs.fileListQuery(dbFile, SQL, qdf_1_520)
    
    # The join function originally used runs into problems - use this f.write
    # to make a string of comma-separated files that IRAF can understand.
    print (" --Generating MasterCal for Full-- ")
    with open('biases.lis', 'w') as f:
     [f.write(x+'\n') for x in biasFull]
    gmos.gbias('@biases.lis', 'MCbiasFull.fits', **biasFlags)
    
    #Since there are no CenterSpec files, we don't need a MasterCal for CS
    
    # Clean up
    iraf.imdel('gS2008*.fits')

    print (" --Creating GCAL Spectral Flat-Field MasterCals--")
    # Set the task parameters.
    gmos.gireduce.unlearn()
    gmos.gsflat.unlearn()
    gmos.gsflat.fl_vardq = 'yes'
    gmos.gsflat.fl_fulldq = 'yes'
    gmos.gsflat.fl_oversize = 'no'
    gmos.gsflat.fl_inter = 'no'
    gmos.gsflat.logfile = 'gsflatLog.txt'
    gmos.gsflat.rawpath = './raw'
    gmos.gsflat.verbose = 'no'


    print ("  -Full Flat (GCAL & Twi) normalization, non-interactive-")
    qdf_1_520['DateObs'] = '*'
    qdf_1_520['Filter2'] = 'open2-8'
    cwf = {'B6-520':520.0, 'B6-525':525.0, 'B6-522':522.5}
    flatType = ['gcalFlat', 'twiFlat']
    for ft in flatType:
        for tag,w in cwf.iteritems():
            qdf_1_520['Disperser'] = tag[0:2] + '00+_%'
            qdf_1_520['CentWave'] = w
            flatName = 'MC' + ft + '-M01_' + tag
            combName = 'MC' + ft + 'Comb-M01_' + tag
            flatFull = fs.fileListQuery(dbFile, fs.createQuery(ft, qdf_1_520), qdf_1_520)
            with open('flats.lis', 'w') as f:
                [f.write(x+'\n') for x in flatFull]
            gmos.gsflat ('@flats.lis', flatName, bias='MCbiasFull',
                         fl_keep='yes', combflat=combName, fl_usegrad='yes', 
                         fl_seprows='no', order='53')
            os.remove('flats.lis')             
    print (" --Processing done-- ")
    
if __name__ == "__main__":
    gmos_mos_proc()
    
