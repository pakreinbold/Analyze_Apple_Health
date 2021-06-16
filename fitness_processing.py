import xml.etree.ElementTree as ET
import pandas as pd
import datetime as dt
import plotly.express as px
from os import path


class FitnessProcessor():
    '''
    Methods
    -------
    __init__()
        Instantiate DataFrames
    check_cache()
        Check if data is in csv & up-to-date
    load_csvs()
        Load DataFrames from csvs
    save_csvs()
        Save DataFrames to csvs
    convert_temp(s)
        Convert temperature strings into floats
    convert_hum(s)
        Convert humidity strings into ints
    find_hr(row, mode)
        Returns heart rate aggregate for a row of runs DataFrame
        mode (str): which aggregate to compute
    enforce_dtypes()
    get_hrs()
        Get heart rate DataFrame from xml file
    get_runs()
        Construct run DataFrame from xml file & heart rates DataFrame
    run_plot(y_data, clr_data, sz_data)
        Customizable plot of runs DataFrame. X-axis is always date.
        y_data (str): column of `runs` to use for the y-axis
        clr_data (str): column of `runs` to use to color points
        sz_data (str): column of `runs` to use to size points
    hr_plot(date_str, idx)

    Attributes
    ----------
    xml_file : str
        Path to the xml file
    root : xml.ElementTree.root
        Root of xml tree
    is_cached : bool
        Whether or not the cache exists & is up-to-date
    heart_rates : pd.DataFrame
        Entries for date (dt.date), time (dt.time), value (float), unit (str)
    runs : pd.DataFrame
        Entries for date (dt.date), distance [mi] (float),
        duration [min] (float), pace [min/mi] (float), speed [mph] (float),
        avg hr [bpm] (float), max hr [bpm] (float), energy [kCal] (float),
        temperature [deg F] (float), humidity [%] (int), indoor (bool),
        start (dt.time), end (dt.time)
    is_github : bool
    '''
    def __init__(self):
        self.xml_file = './apple_health_export/export.xml'
        self.root = ET.parse(self.xml_file).getroot()
        self.is_cached = self.check_cache()
        self.is_github = False
        if self.is_cached:
            print('Loading cached csvs')
            self.load_csvs()
            self.enforce_dtypes()
        else:
            print('Processing xml files')
            self.heart_rates = self.get_hrs()
            self.runs = self.get_runs()
            self.save_csvs()

    def check_cache(self):
        today = dt.datetime.today().date()
        as_of_path = './storage/as_of.txt'
        if path.exists(as_of_path):
            with open(as_of_path, 'r') as text_file:
                as_of = [int(s) for s in text_file.read().split('-')]
            as_of_date = dt.date(as_of[0], as_of[1], as_of[2])
            is_cached = today == as_of_date
        else:
            is_cached = False
        return is_cached

    def load_csvs(self):
        self.runs = pd.read_csv('./storage/runs.csv')
        self.heart_rates = pd.read_csv('./storage/heart_rates.csv')

    def save_csvs(self):
        self.runs.to_csv('./storage/runs.csv', index=False)
        self.heart_rates.to_csv('./storage/heart_rates.csv', index=False)
        today = str(dt.datetime.today().date())
        with open('./storage/as_of.txt', 'w+') as text_file:
            text_file.write(today)

    def convert_temp(self, s):
        if type(s) == str:
            return float(s.split()[0])
        else:
            return s

    def convert_hum(self, s):
        if type(s) == str:
            return float(s.split()[0]) / 100
        else:
            return s

    def find_hr(self, row, mode='mean'):
        # Load the times of the workout
        start = row['start']
        end = row['end']
        date = row['date']

        # Find the heart rates within that time-frame
        cond1 = self.heart_rates['time'].dt.date == date
        cond2 = self.heart_rates['time'].dt.time < end
        cond3 = start < self.heart_rates['time'].dt.time
        hrs = self.heart_rates[cond1 & cond2 & cond3]

        # Return the requested aggregate
        if mode == 'max':
            return hrs['value'].max()
        elif mode == 'median':
            return hrs['value'].median()
        elif mode == 'mean':
            return hrs['value'].mean()
        elif mode == 'all':
            return hrs
        else:
            raise Exception('Inappropriate mode specified')

    def enforce_dtypes(self):
        if type(self.runs['date'][0]) == str:
            self.runs['date'] = pd.to_datetime(self.runs['date']).dt.date
        if type(self.runs['start'][0]) == str:
            self.runs['start'] = pd.to_datetime(self.runs['start']).dt.time
        if type(self.runs['end'][0]) == str:
            self.runs['end'] = pd.to_datetime(self.runs['end']).dt.time
        if type(self.heart_rates['time'][0]) == str:
            self.heart_rates['time'] = pd.to_datetime(
                self.heart_rates['time'])

    def get_hrs(self):
        # Find heart rate records
        heart_rates = self.root\
            .findall('./Record[@type="HKQuantityTypeIdentifierHeartRate"]')

        # Extract into list
        heart_rates = [hr.attrib for hr in heart_rates]

        # Put into DataFrame
        heart_rates = pd.DataFrame(heart_rates)

        # Make some convenience columns
        heart_rates['time'] = pd.to_datetime(heart_rates['endDate'])
        heart_rates['value'] = heart_rates['value'].astype(float)
        heart_rates = heart_rates[['time', 'value', 'unit']]

        return heart_rates

    def get_runs(self):
        # Get the records
        workouts = self.root.findall(
            './Workout[@workoutActivityType="HKWorkoutActivityTypeRunning"]'
            )

        # Process data into DataFrame
        runs = pd.DataFrame(
            [{**workout.attrib,
              **{md.attrib['key']: md.attrib['value']
                 for md in workout.findall('./MetadataEntry')}}
             for workout in workouts]
        )

        # Create shorter columns names
        col_maps = {
            'startDate': 'date', 'endDate': 'end',
            'totalDistance': 'distance',            # mi
            'duration': 'duration',                 # min
            'totalEnergyBurned': 'energy',          # kCal
            'HKWeatherTemperature': 'temperature',  # deg F
            'HKWeatherHumidity': 'humidity',        # %
            'HKIndoorWorkout': 'indoor',
        }
        runs = runs[col_maps.keys()].rename(columns=col_maps)

        # Handle columns with units in their name
        runs['temperature'] = runs['temperature'].apply(self.convert_temp)
        runs['humidity'] = runs['humidity'].apply(self.convert_hum)

        # Convert to floats from strings
        float_cols = ['distance', 'duration', 'energy']
        runs[float_cols] = runs[float_cols].astype(float)

        # Split date & time
        runs['start'] = pd.to_datetime(runs['date']).dt.time    # hour:min:sec
        runs['end'] = pd.to_datetime(runs['end']).dt.time       # hour:min:sec
        runs['date'] = pd.to_datetime(runs['date']).dt.date     # yyyy-mm-dd
        runs.sort_values('date', inplace=True)

        # Get the pace & speed
        runs['speed'] = 60 * runs['distance'] / runs['duration']    # mph
        runs['pace'] = runs['duration'] / runs['distance']          # min/mi

        # Find max & avg heart rates for each workout
        runs['max hr'] = runs.apply(lambda x: self.find_hr(x, mode='max'),
                                    axis=1)
        runs['avg hr'] = runs.apply(lambda x: self.find_hr(x, mode='mean'),
                                    axis=1)

        # Rearrange columns
        runs = runs[['date', 'distance', 'duration', 'pace', 'speed', 'avg hr',
                     'max hr', 'energy', 'temperature', 'humidity', 'indoor',
                     'start', 'end']]

        return runs

    def run_plot(self, y_data='pace', clr_data='avg hr', sz_data='distance'):
        fig = px.scatter(
            self.runs, x='date', y=y_data, color=clr_data, size=sz_data,
            hover_data={'date': True, 'pace': ':.2f', 'speed': ':.2f',
                        'distance': ':.2f', 'avg hr': ':.1f', 'max hr': ':.1f',
                        'temperature': ':.1f', 'humidity': True,
                        'energy': ':.0f', 'start': True},
            labels={col: col.capitalize() for col in self.runs.columns}
        )
        fig.update_layout(width=1500, height=600)

        if y_data == 'pace':
            fig.update_yaxes(autorange="reversed")

        if self.is_github:
            fig.show('svg')
        else:
            fig.show()

    def hr_plot(self, date_str, idx=0):
        '''
        Currently only works for data < a y/o.
        Older data stored in export_cda.xml...?
        '''
        try:
            parts = [int(s) for s in date_str.split('-')]
            date = dt.date(parts[0], parts[1], parts[2])
        except Exception as e:
            print(f'Problem interpreting {date_str}. \
                    Make sure in %Y-%m-%d format')
            raise e
        run = self.runs[self.runs['date'] == date]
        if run.shape[0] > 1:
            print(f'Multiple workouts match this {date_str}. Defaulting to the \
                    earliest. Change the idx parameter to select a different \
                    one.')
        elif run.shape[0] == 0:
            print(f'No workouts on {date_str}. Cannot plot.')
            return
        run = run.iloc[idx, :]
        hrs = self.find_hr(run, mode='all')

        fig = px.scatter(hrs, x='time', y='value',
                         color_discrete_sequence=['red'])
        fig.update_layout(
            width=1500, height=600, title=f'Run on {date_str}',
            xaxis_title="Time",
            yaxis_title="Heart Rate (bpm)",
            xaxis={'tickformat': '%I:%M', 'dtick': 60000.0}
        )
        fig.update_xaxes(tickformat='%I:%M')

        if self.is_github:
            fig.show('svg')
        else:
            fig.show()
        return fig
