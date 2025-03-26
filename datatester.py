from astropy.io import fits

with fits.open("/home/andrey/TransientSearch/data/diff-17.fits") as hdul:
    hdul.info()