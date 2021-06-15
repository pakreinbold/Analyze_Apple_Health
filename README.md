## Functionality
Processes the `.xml` export file from Apple Health into dataframes containing heart rate data and information about running workouts. These are then used to construct a detailed plot of the running history.

## How to use
1: Export the Apple Health data https://www.computerworld.com/article/2889310/how-to-export-apple-health-data-as-a-document-to-share.html?page=2. Once done processing, it can be e-mailed to yourself

2: Download the `.zip` file and un-zip the contents of `apple_health_export` into this repo (placeholder already exists).

3: Run the following code (further examples given in the notebook)

```python
from fitness_processing import FitnessProcessor

# This is the main class
fp = FitnessProcessor()

# To plot: (arguments can be changed)
fp.run_plot(y_data='pace', clr_data='avg hr', sz_data='distance')

# The dataframes are attached
display(fp.runs.tail(10))
display(fp.heart_rates.tail(10))
```
