# -*- coding: utf-8 -*-
"""
Created on Wed Jul 27 14:25:37 2016

@author: rarnason
this reduction script was adapted from Richard Shaw's GMOS Data Reduction Cookbook, available at:
http://ast.noao.edu/sites/default/files/GMOS_Cookbook/
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
    iraf.imdel('gS2008*.fits')

    print ("=== Finished Basic Calibration Processing ===")
    print ("\n")
    print ("=== Performing cosmic-ray rejection using gemcrspec ===")
    
    #note that this construction works because there's only one exposure per position/grating/cenwave combo 
    #if you have multiple exposures, comment this block out and use gemcombine to do outlier rejection when combining images instead
    gemtools.gemcrspec.unlearn()
    gemtools.gemcrspec.xorder = '9'
    gemtools.gemcrspec.yorder = '-1'
    gemtools.gemcrspec.sigclip = '4.5'   
    gemtools.gemcrspec.sigfrac= '0.5'
    gemtools.gemcrspec.objlim = '1.0'
    gemtools.gemcrspec.verbose = 'no'
    prefix = 'gs'
    for tag,w in cwf.iteritems():
        qdf['Disperser'] = tag[0:2] + '00+_%'
        qdf['CentWave'] = w
        outFile = qdf['Object'] + '-M01_' + tag
        sciFull = fs.fileListQuery(dbFile, fs.createQuery('sciSpec', qdf), qdf)
        gemtools.gemcrspec(','.join(prefix+str(x) for x in sciFull), outFile)
    # Do the same for the standard star
    for tag,w in cws.iteritems():
        qd_std['Disperser'] = tag[0:2] + '00+_%'
        qd_std['CentWave'] = w
        outFile = qd_std['Object'] + '-M01_' + tag
        stdFull = fs.fileListQuery(dbFile, fs.createQuery('std', qd_std), qd_std)
        gemtools.gemcrspec(','.join(prefix+str(x) for x in stdFull), outFile)  


    #comment block for doing outlier rejection with multiple exposures per position/grating/cenwave combo
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

    print ("=== Begining wavelength calibration ===")
    print (" -- Deriving wavelength calibration --")
    
    # Begin with longslit Arcs.
    # The fit to the dispersion relation should be performed interactively;
    # here we will us a previously determined result.
    # There are many arcs to choose from: we only need one for each setting.

    gmos.gswavelength.unlearn()
    waveFlags = {
    	'coordlist':'gmos$data/CuAr_GMOS.dat','fwidth':6,'nsum':50,
    	'function':'chebyshev','order':5,
    	'fl_inter':'no','logfile':'gswaveLog.txt','verbose':'no'
    	}


    for seq in ['091','092','093']:
        inFile = prefix + 'S20081129S0' + seq
        gmos.gswavelength(inFile,**waveFlags)
    
    #  Now for the MOS arcs
    waveFlags.update({'order':7,'nsum':20,'step':2})
    
    for seq in ['249','250','251']:
        inFile = prefix + 'S20081120S0' + seq
        gmos.gswavelength(inFile,**waveFlags)

    #This block is in the tutorial but it seems incorrect - it applies the calibration to non gsreduced arcs!!
    '''
    for tag,w in cwf.iteritems():
    	qdf['Disperser'] = tag[0:2] + '00+_%'
    	qdf['CentWave'] = w
    	outFile = qdf['Object'] + tag
    	arcFull = fs.fileListQuery(dbFile, fs.createQuery('arcP', qdf), qdf)
    	gmos.gswavelength (','.join(prefix+str(x) for x in arcFull),**waveFlags)
    '''
    
    print (" -- Applying wavelength calibration -- ")
    gmos.gstransform.unlearn()
    transFlags = {
    'fl_vardq':'no','interptype':'linear','fl_flux':'yes',
    'logfile':'gstransformLog.txt','verbose':'no'
    }
    
    #Construct a mapping for the wavelength calibration. Format (arc id,sci/std id,target):'filter/disperser'
    print (" -- Calibrating standard star exposures -- ")
    gmos.gstransform ('LTT1020-M01_B6-415', wavtraname='gsS20081129S0091',
                  **transFlags)
    gmos.gstransform ('LTT1020-M01_B6-520', wavtraname='gsS20081129S0092',
                  **transFlags)
    gmos.gstransform ('LTT1020-M01_B6-625', wavtraname='gsS20081129S0093',
                  **transFlags)
    #This block seems to operate on the non CR-cleaned images! 
    '''
    transMap = {
	('091','036','LTT1020'):'B6-415',
        ('092','039','LTT1020'):'B6-520',
	('093','040','LTT1020'):'B6-625'
	}
    print (" -- Calibrating standard star exposures -- ")
    for id,tag in transMap.iteritems():
        inFile = 'gsS20081129S0' + id[1]
        wavFile = 'gsS20081129S0' + id[0]
        outFile = 't' + id[2] + '_' + tag
	gmos.gstransform(inFile,outimages=outFile,wavtraname=wavFile)
    '''
    print (" -- Calibrating MOS science exposures -- ")
    
    transFlags.update({'fl_vardq':'yes'})
    gmos.gstransform ('Sculptor-field1-M01_B6-520', wavtraname='gsS20081120S0249',
                  **transFlags)
    gmos.gstransform ('Sculptor-field1-M01_B6-522', wavtraname='gsS20081120S0250',
                  **transFlags)
    gmos.gstransform ('Sculptor-field1-M01_B6-525', wavtraname='gsS20081120S0251',
                  **transFlags)
    

    print (" --Processing done-- ")
    
if __name__ == "__main__":
    gmos_mos_proc()
    
