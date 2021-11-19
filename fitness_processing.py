import xml.etree.ElementTree as ET
import pandas as pd
import datetime as dt
import plotly.express as px
from os import path


def convert_elevation(s):
    '''
    Convert the elevation change string, which comes in form "xxx cm"

    Args:
        s (str): Contains elevation change information

    Returns:
        (float): The elevation change in feet
    '''
    if type(s) == str:
        return float(s.split()[0]) * 2.54 / 12
    else:
        return s


def convert_temp(s):
    '''
    Convert the temperature into a float

    Args:
        s (str): Contains the temperature, in the form "__ degF"

    Returns:
        (float): Temperature with units degrees Fahrenheit
    '''
    if type(s) == str:
        return float(s.split()[0])
    else:
        return s


def convert_hum(s):
    '''
    Convert the humidity string into a float

    Args:
        s (str): Contains the humidity in the form "XX00 %"

    Returns:
        (float): Humidity with units % (i.e., 0-100)
    '''
    if type(s) == str:
        return float(s.split()[0]) / 100
    else:
        return s


def enforce_dtypes(df, mode):
    '''
    Make sure that the dtypes in the loaded DataFrames are correct

    Args:
        df (pd.DataFrame): Could be `heart_rates` or `runs`
            keys: "Date", "Start", "End" *or* "Time"
        mode (str): Which DataFrame to work enforce; options: "runs" or "heart_rates"

    Returns:
        (pd.DataFrame): `df`, but with properly formatted column dtypes
    '''
    if mode == 'runs':
        if type(df['Date'][0]) == str:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        if type(df['Start'][0]) == str:
            df['Start'] = pd.to_datetime(df['Start']).dt.time
        if type(df['End'][0]) == str:
            df['End'] = pd.to_datetime(df['End']).dt.time
        return df
    elif mode == 'heart_rates':
        if type(df['Time'][0]) == str:
            df['Time'] = pd.to_datetime(df['Time'])
        return df
    else:
        print('Mode must be "runs" or "heart_rates".')


class FitnessProcessor():
    '''
    Attributes:
        heart_rates (pd.DataFrame):
            date (dt.date)
            time (dt.time)
            Value (float)
            unit (str)
        runs (pd.DataFrame):
            date (dt.date)
            distance [mi] (float)
            duration [min] (float)
            pace [min/mi] (float)
            speed [mph] (float)
            avg hr [bpm] (float)
            max hr [bpm] (float)
            energy [kCal] (float)
            temperature [deg F] (float)
            humidity [%] (int)
            indoor (bool)
            start (dt.time)
            end (dt.time)
    '''

    def __init__(self):
        ''' Make sure heart_rates & runs are up-to-date and load them '''
        self.xml_file = './apple_health_export/export.xml'
        self.root = ET.parse(self.xml_file).getroot()
        self.is_cached = self.check_cache()
        self.is_github = False
        if self.is_cached:
            print('Loading cached csvs')
            self.load_csv('heart_rates')
            self.load_csv('runs')
        else:
            self.update_cache()

    def update_cache(self):
        ''' Call the data processing scripts & cache the csvs '''
        print('Processing xml files')
        self.heart_rates = self.get_hrs()
        self.runs = self.get_runs()
        self.save_csvs()

    def check_cache(self):
        '''
        See if the date in `as_of.txt` matches today. If not, set the `is_cached` variable to False
        '''
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

    def load_csv(self, mode):
        ''' Load the stored data into memory & make sure the data types are correct '''
        if mode == 'runs':
            self.runs = enforce_dtypes(
                pd.read_csv('./storage/runs.csv'), mode='runs'
            )
        elif mode == 'heart_rates':
            self.heart_rates = enforce_dtypes(
                pd.read_csv('./storage/heart_rates.csv'), mode='heart_rates'
            )
        else:
            print('Mode must be "runs" or heart_rates".')

    def save_csvs(self):
        ''' Store the DataFrames as csvs, and today's date in a .txt file '''
        self.runs.to_csv('./storage/runs.csv', index=False)
        self.heart_rates.to_csv('./storage/heart_rates.csv', index=False)
        today = str(dt.datetime.today().date())
        with open('./storage/as_of.txt', 'w+') as text_file:
            text_file.write(today)

    def find_hr(self, row, mode='mean'):
        '''
        Search the heart rate data for a given time-window that corresponds to a workout, and
        compute a statistic of the heart rates from within that window. Mostly used within an
        .apply() to add a heart rate column to `runs`.

        Args:
            row (pd.Series): A row of the `runs` DataFrame that corresponds to a single workout
            mode (str): The statistic to compute; options: "max", "median", "mean", "all"

        Returns:
            (float): If `mode` != "all", the computed statistic
            (pd.DataFrame): If `mode` == "all", a subset of `heart_rates`
        '''
        # Load the times of the workout
        start = row['Start']
        end = row['End']
        date = row['Date']

        # Find the heart rates within that time-frame
        cond1 = self.heart_rates['Time'].dt.date == date
        cond2 = self.heart_rates['Time'].dt.time < end
        cond3 = start < self.heart_rates['Time'].dt.time
        hrs = self.heart_rates[cond1 & cond2 & cond3]

        # Return the requested aggregate
        if mode == 'max':
            return hrs['Value'].max()
        elif mode == 'median':
            return hrs['Value'].median()
        elif mode == 'mean':
            return hrs['Value'].mean()
        elif mode == 'all':
            return hrs
        else:
            raise ValueError('Inappropriate mode specified')

    def get_hrs(self):
        '''
        Process `/apple_health_export/export.xml` to get all recorded heart rates & their times

        Returns:
            (pd.DataFrame):
                Time (datetime.datetime)
                Value (float)
                Unit (str)
        '''
        # Find heart rate records
        heart_rates = self.root\
            .findall('./Record[@type="HKQuantityTypeIdentifierHeartRate"]')

        # Extract into list
        heart_rates = [hr.attrib for hr in heart_rates]

        # Put into DataFrame
        heart_rates = pd.DataFrame(heart_rates).sort_values('endDate')

        # Make some convenience columns
        heart_rates['Time'] = pd.to_datetime(heart_rates['endDate'])
        heart_rates['Value'] = heart_rates['value'].astype(float)
        heart_rates.rename(columns={'unit': 'Unit'}, inplace=True)
        heart_rates = heart_rates[['Time', 'Value', 'Unit']]\
            .sort_values('Time')

        # Merge with old heart rates
        if self.is_cached:
            old_heart_rates = self.load_csv('heart_rates')
            heart_rates.merge(old_heart_rates, how='outer', on='Time')

        return heart_rates

    def get_bw(self):
        ''' Instantiate the `bodyweight` DataFrame '''
        self.bodyweight = self.root.findall(
            './Workout[@workoutActivityType="HKQuantityTypeIdentifierBodyMass"]'
        )

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
            'startDate': 'Date', 'endDate': 'End',
            'totalDistance': 'Distance',            # mi
            'duration': 'Duration',                 # min
            'totalEnergyBurned': 'Energy',          # kCal
            'HKWeatherTemperature': 'Temperature',  # deg F
            'HKWeatherHumidity': 'Humidity',        # %
            'HKIndoorWorkout': 'Indoor',
            'HKElevationAscended': 'Elevation',     # cm
        }
        runs = runs[col_maps.keys()].rename(columns=col_maps)

        # Handle columns with units in their name
        runs['Temperature'] = runs['Temperature'].apply(convert_temp)
        runs['Humidity'] = runs['Humidity'].apply(convert_hum)
        runs['Elevation'] = runs['Elevation'].apply(convert_elevation)

        # Convert to floats from strings
        float_cols = ['Distance', 'Duration', 'Energy']
        runs[float_cols] = runs[float_cols].astype(float)

        # Split date & time
        runs['Start'] = pd.to_datetime(runs['Date']).dt.time    # hour:min:sec
        runs['End'] = pd.to_datetime(runs['End']).dt.time       # hour:min:sec
        runs['Date'] = pd.to_datetime(runs['Date']).dt.date     # yyyy-mm-dd
        runs.sort_values('Date', inplace=True)

        # Get the pace & speed
        runs['Speed'] = 60 * runs['Distance'] / runs['Duration']    # mph
        runs['Pace'] = runs['Duration'] / runs['Distance']          # min/mi

        # Find max & avg heart rates for each workout
        runs['Max HR'] = runs.apply(lambda x: self.find_hr(x, mode='max'),
                                    axis=1)
        runs['Avg HR'] = runs.apply(lambda x: self.find_hr(x, mode='mean'),
                                    axis=1)

        # Rearrange columns
        runs = runs[['Date', 'Distance', 'Duration', 'Pace', 'Speed', 'Avg HR',
                     'Max HR', 'Energy', 'Temperature', 'Humidity', 'Indoor',
                     'Elevation', 'Start', 'End']]

        # Merge with old runs
        if self.is_cached:
            old_runs = self.load_csv('runs')
            runs.merge(old_runs, how='outer', on=['Date', 'Start'])

        return runs

    def run_plot(self, y_data='Pace', clr_data='Avg HR', sz_data='Distance'):
        fig = px.scatter(
            self.runs, x='Date', y=y_data,
            color=clr_data, size=self.runs[sz_data]**1.5,
            hover_data={'Date': True, 'Pace': ':.2f', 'Speed': ':.2f',
                        'Distance': ':.2f', 'Avg HR': ':.1f', 'Max HR': ':.1f',
                        'Temperature': ':.1f', 'Humidity': True,
                        'Energy': ':.0f', 'Start': True, 'Duration': ':.2f'},
            labels={col: col.capitalize() for col in self.runs.columns}
        )
        fig.update_layout(width=1500, height=600)

        if y_data == 'Pace':
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
        run = self.runs[self.runs['Date'] == date]
        if run.shape[0] > 1:
            print(f'Multiple workouts match this {date_str}. Defaulting to the \
                    earliest. Change the idx parameter to select a different \
                    one.')
        elif run.shape[0] == 0:
            print(f'No workouts on {date_str}. Cannot plot.')
            return
        run = run.iloc[idx, :]
        hrs = self.find_hr(run, mode='all')

        fig = px.scatter(hrs, x='Time', y='Value',
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
