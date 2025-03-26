import time
t0 = time.time()

# IMPORTS
import os
import sys
import psutil
import warnings
import tempfile
import multiprocessing as mp

import numpy as np
import matplotlib.pyplot as plt

import sep as sep
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.wcs import FITSFixedWarning
from reproject import reproject_interp

# 


# GLOBAL PARAMETERS
# data & preprocessing
data_dir  = "/home/andrey/TransientSearch/data/" # data directory
dsf       = 1                                    # downsampling factor
sci_index = 1                                    # index of scientific data

# source extraction
threshold = 5 # objection detection threshold in σ above noise floor (use 3-5)
minarea   = 5 # minimum area (use 5-10)

# visualization
blackpoint = 0      # visualization blackpoint (vmin)
dpi        = 500    # visualization dpi (resolution)
lw         = 0.03   # visualization line width
imgpath    = "img/" # output image path

# alignment
wcs_target_17 = "diff-17.fits" # target images for alignment
wcs_target_18 = "diff-18.fits"

# warnings
warnings.filterwarnings("ignore", category=FITSFixedWarning) # unnecessary
warnings.filterwarnings("ignore", message=".*OBSGEO.*") # taken care of with the .celestial method




# USEFUL FUNCTIONS
def display(data, name):
    plt.clf()
    m, s = np.mean(data), np.std(data)
    plt.imshow(data, interpolation='nearest', cmap='gray', vmin=blackpoint, vmax=m+s, origin='lower')
    plt.colorbar()
    plt.savefig(name, dpi=dpi)

def preprocess(file):
    data = file[::dsf, ::dsf]
    data = np.ascontiguousarray(data)
    bg = sep.Background(data)
    data = data - bg

    return data

def load(file):
    with fits.open(data_dir + file) as hdu:
        data = hdu[sci_index].data
        wcs = WCS(hdu[sci_index].header).celestial

    return data, wcs

def align(data, wcs, ref_wcs, ref_shape):
    reprojected, fp = reproject_interp((data, wcs), ref_wcs, shape_out=ref_shape)

    return reprojected

def datainfo(files):
    for file in files:
        with fits.open(data_dir + file) as hdu:
            print(f"\nFile: {file}")
            hdu.info()

    return 0

def check_overlap(wcs1, shape1, wcs2, shape2):
    h1, w1 = shape1
    corners1 = np.array([[0, 0], [0, h1-1], [w1-1, 0], [w1-1, h1-1]])
    sky_corners1 = wcs1.pixel_to_world(corners1[:, 0], corners1[:, 1])
    
    h2, w2 = shape2
    corners2 = np.array([[0, 0], [0, h2-1], [w2-1, 0], [w2-1, h2-1]])
    sky_corners2 = wcs2.pixel_to_world(corners2[:, 0], corners2[:, 1])
    
    ra1_min, ra1_max = np.min(sky_corners1.ra.deg), np.max(sky_corners1.ra.deg)
    dec1_min, dec1_max = np.min(sky_corners1.dec.deg), np.max(sky_corners1.dec.deg)
    
    ra2_min, ra2_max = np.min(sky_corners2.ra.deg), np.max(sky_corners2.ra.deg)
    dec2_min, dec2_max = np.min(sky_corners2.dec.deg), np.max(sky_corners2.dec.deg)
    
    ra_overlap = not (ra1_max < ra2_min or ra2_max < ra1_min)
    dec_overlap = not (dec1_max < dec2_min or dec2_max < dec1_min)
    
    overlap = ra_overlap and dec_overlap
    
    print(f"\nRef RA range:    {ra1_min:.6f} to {ra1_max:.6f}")
    print(f"Image RA range:  {ra2_min:.6f} to {ra2_max:.6f}")
    print(f"Ref Dec range:   {dec1_min:.6f} to {dec1_max:.6f}")
    print(f"Image Dec range: {dec2_min:.6f} to {dec2_max:.6f}")
    print(f"Overlap: {overlap}")
    
    return 0



starttime = time.time()
print(f"instantiation completed in: {starttime - t0} [s]")



# LOADING
diff17, wcs_ref_17 = load("diff-17.fits")
diff18, wcs_ref_18 = load("diff-18.fits")
c3d17, wcs_c3d17 = load("c3d-17.fits")
c3d18, wcs_c3d18 = load("c3d-18.fits")
cweb17, wcs_cweb17 = load("cweb-17.fits")
cweb18, wcs_cweb18 = load("cweb-18.fits")

loadtime = time.time()
print(f"data loaded in: {loadtime - starttime} [s]")



# CHECKS
print("\n\n-System and Data info-")
print(f"\nAvailable threads: {mp.cpu_count()}")
print(f"Available memory:  {np.round(psutil.virtual_memory().available/(1024*1024*1024), 2)} [GiB]")
#datainfo(["diff-17.fits", "diff-18.fits", "c3d-17.fits"\
#        , "c3d-18.fits", "cweb-17.fits", "cweb-18.fits"])

check_overlap(wcs_ref_17, diff17.shape, wcs_cweb17, cweb17.shape)
check_overlap(wcs_ref_17, diff17.shape, wcs_c3d17, c3d17.shape)
check_overlap(wcs_ref_18, diff18.shape, wcs_cweb18, cweb18.shape)
check_overlap(wcs_ref_18, diff18.shape, wcs_c3d18, c3d18.shape)
print("\n")


# PREPROCESSING
if __name__ == "__main__":
    mp.set_start_method('fork', force=True)
    with mp.Pool(processes=6) as pool:
        print("async process started with 6 workers")
        r_diff17 = pool.apply_async(preprocess, (diff17,))
        r_diff18 = pool.apply_async(preprocess, (diff18,))
        r_c3d17  = pool.apply_async(preprocess, (c3d17,))
        r_c3d18  = pool.apply_async(preprocess, (c3d18,))
        r_cweb17 = pool.apply_async(preprocess, (cweb17,))
        r_cweb18 = pool.apply_async(preprocess, (cweb18,))

        diff17, diff18 = r_diff17.get(), r_diff18.get()
        c3d17 , c3d18  = r_c3d17.get() , r_c3d18.get()
        cweb17, cweb18 = r_cweb17.get(), r_cweb18.get()

pptime = time.time()
print(f"preprocessing and background extraction completed in: {pptime - loadtime} [s]")



# ALIGNMENT
shape_ref_17 = diff17.shape
shape_ref_18 = diff18.shape

if __name__ == "__main__":
    mp.set_start_method('fork', force=True)
    with mp.Pool(processes=4) as pool:
        print("async process started with 4 workers")
        r_c3d17  = pool.apply_async(align, (c3d17 , wcs_c3d17 , wcs_ref_17, shape_ref_17)) 
        r_c3d18  = pool.apply_async(align, (c3d18 , wcs_c3d18 , wcs_ref_18, shape_ref_18))
        r_cweb17 = pool.apply_async(align, (cweb17, wcs_cweb17, wcs_ref_17, shape_ref_17))
        r_cweb18 = pool.apply_async(align, (cweb18, wcs_cweb18, wcs_ref_18, shape_ref_18))

        c3d17 , c3d18  = r_c3d17.get() , r_c3d18.get()
        cweb17, cweb18 = r_cweb17.get(), r_cweb18.get()

aligntime = time.time()
print(f"alignment completed in: {aligntime - pptime} [s]")



# SOURCE EXTRACTION
bg17 = sep.Background(diff17)
bg18 = sep.Background(diff18)

if __name__ == "__main__":
    with mp.Pool(processes=2) as pool:
        print("async process started with 2 workers")
        r_17 = pool.apply_async(sep.extract, args=(diff17, threshold), kwds={"minarea": minarea, "err": bg17.globalrms})
        r_18 = pool.apply_async(sep.extract, args=(diff18, threshold), kwds={"minarea": minarea, "err": bg18.globalrms})

        obj17, obj18 = r_17.get(), r_18.get()


septime = time.time()
print(f"source extraction completed in: {septime - aligntime} [s]")
