# https://matplotlib.org/stable/tutorials/images.html
import matplotlib.pyplot as pl
from PIL import Image
import numpy as np
import pandas as pd

img = pl.imread("abbott NACA 2412 CL CD.png")
height, width = img.shape[:2]

# --- Example points to overlay ---
# Coordinates are in (x, y) pixel space

df = pd.read_csv("abbott NACA 2412 CL CD.csv")



# --- Plot ---
fig, ax = pl.subplots()
# Display image so that pixel (0,0) is bottom-left and each pixel = 1 unit
ax.imshow(img, extent=[0, width, 0, height], origin='lower')
ax.scatter(df['PixelX'], df['PixelY'], c='blue', s=20, marker='o', label='Points',)  

# Hide axes
ax.axis('off')

# Keep aspect ratio so pixels are square
ax.set_aspect('equal')

ax.invert_yaxis()


ax.legend()
pl.show()