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
        Entries for date (dt.date), time (dt.time), Value (float), unit (str)
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
            self.heart_rates = self.load_csv('heart_rates')
            self.runs = self.load_csv('runs')
        else:
            self.update_cache()
        return

    def update_cache(self):
        print('Processing xml files')
        self.heart_rates = self.get_hrs()
        self.runs = self.get_runs()
        self.save_csvs()
        return

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

    def load_csv(self, mode):
        if mode == 'runs':
            runs = self.enforce_dtypes(
                pd.read_csv('./storage/runs.csv'), mode='runs'
            )
            return runs
        elif mode == 'heart_rates':
            heart_rates = self.enforce_dtypes(
                pd.read_csv('./storage/heart_rates.csv'), mode='heart_rates'
            )
            return heart_rates
        else:
            print('Mode must be "runs" or heart_rates".')
            return

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
            raise Exception('Inappropriate mode specified')

    def enforce_dtypes(self, df, mode):
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

    def get_hrs(self):
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
        heart_rates = heart_rates[['Time', 'Value', 'Unit']].sort_values('Time')

        # Merge with old heart rates
        if self.is_cached:
            old_heart_rates = self.load_csv('heart_rates')
            heart_rates.merge(old_heart_rates, how='outer', on='Time')

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
            'startDate': 'Date', 'endDate': 'End',
            'totalDistance': 'Distance',            # mi
            'duration': 'Duration',                 # min
            'totalEnergyBurned': 'Energy',          # kCal
            'HKWeatherTemperature': 'Temperature',  # deg F
            'HKWeatherHumidity': 'Humidity',        # %
            'HKIndoorWorkout': 'Indoor',
        }
        runs = runs[col_maps.keys()].rename(columns=col_maps)

        # Handle columns with units in their name
        runs['Temperature'] = runs['Temperature'].apply(self.convert_temp)
        runs['Humidity'] = runs['Humidity'].apply(self.convert_hum)

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
                     'Start', 'End']]

        # Merge with old runs
        if self.is_cached:
            old_runs = self.load_csv('runs')
            runs.merge(old_runs, how='outer', on=['Date', 'Start'])

        return runs

    def run_plot(self, y_data='Pace', clr_data='Avg HR', sz_data='Distance'):
        fig = px.scatter(
            self.runs, x='Date', y=y_data, color=clr_data, size=sz_data,
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
