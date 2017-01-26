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
    # Select bias exposures within ~2 months of the target observations:     
    qdf = {'use_me':1,
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
    
    #Create query dictionaries for the standard star observation
    qd_std = copy.deepcopy(qdf)
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

    #This SQL query generates the list of full-frame files to process. Note that since the std star has the 
    # same RoI, CCD binning, and CCD gain/read-out speed, we only need to make one bias file.     
    SQL = fs.createQuery('bias', qdf)
    biasFull = fs.fileListQuery(dbFile, SQL, qdf)
    
    # The join function originally used runs into problems - use this f.write
    # to make a string of comma-separated files that IRAF can understand.
    print (" --Generating MasterCal for Full-- ")
    with open('biases.lis', 'w') as f:
     [f.write(x+'\n') for x in biasFull]
    #Create the bias MasterCal
    gmos.gbias('@biases.lis', 'MCbiasFull.fits', **biasFlags)
     
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

    #Perform flat-field normalization for the science images
    print ("  -Full Flat (GCAL & Twi) normalization for science images, non-interactive-")
    qdf['DateObs'] = '*'
    qdf['Filter2'] = 'open2-8'
    cwf = {'B6-520':520.0, 'B6-525':525.0, 'B6-522':522.5}
    #flatType = ['gcalFlat', 'twiFlat']
    #No twilight flats were available for this observation - calibrating using only the gcal flats
    flatType = ['gcalFlat']	
    for ft in flatType:
        for tag,w in cwf.iteritems():
            qdf['Disperser'] = tag[0:2] + '00+_%'
            qdf['CentWave'] = w
            flatName = 'MC' + ft + '-M01_' + tag
            combName = 'MC' + ft + 'Comb-M01_' + tag
            flatFull = fs.fileListQuery(dbFile, fs.createQuery(ft, qdf), qdf)
            with open('flats_sci.lis', 'w') as f:
                [f.write(x+'\n') for x in flatFull]
	    print "Flatfielding for " + str(ft) + " and " + str(w)
            gmos.gsflat ('@flats_sci.lis', flatName, bias='MCbiasFull',
                         fl_keep='yes', combflat=combName, fl_usegrad='yes', 
                         fl_seprows='no', order='53')
            os.remove('flats_sci.lis')
    
    #Perform flat-field normalization for the standard star. Standard star was taken at centw 415,520,625	
    print ("  -Full Flat (GCAL & Twi) normalization for the standard star, non-interactive-")
    qd_std['DateObs'] = '*'
    qd_std['Filter2'] = 'open2-8'
    cws = {'B6-415':415.0, 'B6-520':520.0, 'B6-625':625.0}
    #flatType = ['gcalFlat', 'twiFlat']
    #No twilight flats were available for this observation - calibrating using only the gcal flats
    flatType = ['gcalFlat']
    for ft in flatType:
        for tag,w in cws.iteritems():
            qd_std['Disperser'] = tag[0:2] + '00+_%'
            qd_std['CentWave'] = w
            flatName = 'MC' + ft + '-M01_' + tag
            combName = 'MC' + ft + 'Comb-M01_' + tag
            flatFull = fs.fileListQuery(dbFile, fs.createQuery(ft, qd_std), qd_std)
            with open('flats_std.lis', 'w') as f:
                [f.write(x+'\n') for x in flatFull]
            gmos.gsflat ('@flats_std.lis', flatName, bias='MCbiasFull',
                         fl_keep='yes', combflat=combName, fl_usegrad='yes', 
                         fl_seprows='no', order='53')
            os.remove('flats_std.lis')    

    print ("=== Processing Science Files ===")
    print (" -- Performing Basic Processing --")
                 

    # Use primarily the default task parameters.
    gmos.gsreduce.unlearn()
    gmos.gsreduce.logfile = 'gsreduceLog.txt'
    gmos.gsreduce.rawpath = './raw'
    gmos.gsreduce.verbose = 'no'
    gmos.gsreduce.fl_fixpix = 'no'
    gmos.gsreduce.fl_oversize = 'no'
    #Perform single-frame CR rejection
    #gmos.gsreduce.fl_gscr = 'yes'

    print ("  - GSReducing MOS Science and Arc exposures -")
    for tag,w in cwf.iteritems():
        qdf['Disperser'] = tag[0:2] + '00+_%'
        qdf['CentWave'] = w
        flatName = 'MCgcalFlat-M01_' + tag
        gradName = 'MCgcalFlatComb-M01_' + tag
        arcFull = fs.fileListQuery(dbFile, fs.createQuery('arc', qdf), qdf)
        gmos.gsreduce (','.join(str(x) for x in arcFull), bias='MCbiasFull',
                  gradimage=gradName, fl_flat='no')
        sciFull = fs.fileListQuery(dbFile, fs.createQuery('sciSpec', qdf), qdf)
        gmos.gsreduce (','.join(str(x) for x in sciFull), bias='MCbiasFull',
                  flatim=flatName, gradimage=gradName,
                  fl_vardq='yes', fl_fulldq='yes')
    
    print ("  - GSReducing Longslit Std-star and Arc exposures -")
    for tag,w in cws.iteritems():
        qd_std['Disperser'] = tag[0:2] + '00+_%'
        qd_std['CentWave'] = w
        flatName = 'MCgcalFlat-M01_' + tag
        arc_std = fs.fileListQuery(dbFile, fs.createQuery('arc', qd_std), qd_std)
        gmos.gsreduce (','.join(str(x) for x in arc_std), bias='MCbiasFull',
                  fl_flat='no')
        std_files = fs.fileListQuery(dbFile, fs.createQuery('std', qd_std), qd_std)
        gmos.gsreduce (','.join(str(x) for x in std_files), bias='MCbiasFull',
                  flatim=flatName, fl_fixpix='yes')

    # Clean up - uncomment this eventually
    #iraf.imdel('gS2008*.fits')

    print ("=== Finished Basic Calibration Processing ===")
    print ("\n")
    print ("=== Performing cosmic-ray rejection using gemcrspec ===")
    
    #note that this construction works because there's only one exposure per position/grating/cenwave combo 
    #if you have multiple exposures, comment this block out and use gemcombine to do outlier rejection when combining images instead
    gemtools.gemcrspec.unlearn()

    prefix = 'gs'
    for tag,w in cwf.iteritems():
        qdf['Disperser'] = tag[0:2] + '00+_%'
        qdf['CentWave'] = w
        outFile = qdf['Object'] + tag
        sciFull = fs.fileListQuery(dbFile, fs.createQuery('sciSpec', qdf), qdf)
        gemtools.gemcrspec(','.join(prefix+str(x) for x in sciFull), outFile)
    # Do the same for the standard star
    for tag,w in cws.iteritems():
        qdf['Disperser'] = tag[0:2] + '00+_%'
        qdf['CentWave'] = w
        outFile = qd_std['Object'] + tag
        stdFull = fs.fileListQuery(dbFile, fs.createQuery('std', qd_std), qd_std)
        gemtools.gemcrspec(','.join(prefix+str(x) for x in stdFull), outFile)  


    '''
    # Use primarily the default task parameters.
    gemtools.gemcombine.unlearn()
    gemtools.gemcombine.logfile = 'gemcombineLog.txt'
    gemtools.gemcombine.reject = 'ccdclip'
    gemtools.gemcombine.fl_vardq = 'yes'
    gemtools.gemcombine.fl_dqprop = 'yes'
    gemtools.gemcombine.verbose = 'no'       
    prefix = 'gs'
    for tag,w in cwf.iteritems():
        qdf['Disperser'] = tag[0:2] + '00+_%'
        qdf['CentWave'] = w
        outFile = qdf['Object'] + tag
        sciFull = fs.fileListQuery(dbFile, fs.createQuery('sciSpec', qdf), qdf)
        gemtools.gemcombine (','.join(prefix+str(x) for x in sciFull), outFile)
    # Do the same for the standard star
    for tag,w in cws.iteritems():
        qdf['Disperser'] = tag[0:2] + '00+_%'
        qdf['CentWave'] = w
        outFile = qd_std['Object'] + tag
        stdFull = fs.fileListQuery(dbFile, fs.createQuery('std', qd_std), qd_std)
        gemtools.gemcombine (','.join(prefix+str(x) for x in stdFull), outFile)
    '''

    print (" --Processing done-- ")
    
if __name__ == "__main__":
    gmos_mos_proc()
    
