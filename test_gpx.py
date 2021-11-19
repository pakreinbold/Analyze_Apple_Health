# %%
import gpxpy
import gpxpy.gpx
import numpy as np
import plotly.express as px
import pandas as pd


def pytha(x1, x2, y1, y2):
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)


# Extract points from gpx file
gpx_file = open('apple_health_export/workout-routes/route_2021-08-09_6.54pm.gpx', 'r')  # noqa
gpx = gpxpy.parse(gpx_file)
points = gpx.tracks[0].segments[0].points

# Convert the gpx-points into numpy array
xyz = np.array([[point.latitude, point.longitude, point.elevation, point.time] for point in points])

# Shift coordinate system
xyz[:, :3] = xyz[:, :3] - xyz[:, :3].mean(axis=0).reshape(1, 3)

# Convert the numpy array into a pandas DataFrame for plotting
df = pd.DataFrame(xyz, columns=['lat', 'long', 'ele', 'time'])

# Estimate the mile change per lat change
s_x = 69                                        # mi / lat deg
s_y = np.cos(35.2271 * np.pi / 180) * 69.172    # mi / long deg

df['x'] = df['lat'] * s_x
df['y'] = df['long'] * s_y
df['x_ft'] = df['x'] * 5280
df['y_ft'] = df['y'] * 5280

display(df)

# %% Plot with plotly
px.line(df, x='time', y=['x', 'y'])

# %% Get the pytha distance
x1 = df['x'].values[:-1]
x2 = df['x'].values[1:]
y1 = df['y'].values[:-1]
y2 = df['y'].values[1:]
lengths = pytha(x1, x2, y1, y2)
print(f'Total distance travelled: {lengths.sum():.2f} mi')
