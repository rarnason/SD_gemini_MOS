'''
Created Feb 27, 2017

@author: rarnason

This script permits inspection of the unskysubtracted and skysubtracted 2D spectra for objects in MOS mode, in this case observations of Sculptor Dwarf field 1
from Gemini Program ID GS-2008B-Q-25



'''

from pyraf import iraf
import astropy.io.fits as fits
import subprocess


names = 'tSculptor-field1-M01_B6-'
prefix = 's'
cenwave = ['520','522','525']

#Iterate over each .fits file with different central wavelengths
for wave in cenwave: 
	filename = names + wave + '.fits'
	#Iterate over each pair of 2D MOS spectra in the fits file - in this case extensions 2 - 23 are the MOS spectra
	for i in range(2,24):
		print("Inspecting extension [" + str(i) + "] for cenwave " + str(wave))
		filename2 = filename + "[" + str(i) + "]"
		filename3 = prefix + filename2
		subprocess.check_output(['ds9',filename2,filename3,'-lock','frame','wcs','-lock','colorbar','yes','-lock','scalelimits','yes', \
			'-scale','linear','-tile','row','-geometry','1920x1080'])		
		#raw_input("Press enter to continue")
		
	



