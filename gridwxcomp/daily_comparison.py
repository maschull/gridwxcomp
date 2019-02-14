import argparse
import datetime as dt
import logging
import pandas as pd
import numpy as np
import os
import sys

from bokeh.plotting import figure, output_file, show, save
from bokeh.layouts import gridplot


def main(input_csv, out_dir, year_filter=''):

    """Compare daily Wx Station Data from PyWeatherQAQC with gridMET for each
    month in year specified above.
    Args:
        input_csv (str): path to input CSV file containing
            paired station/gridMET metadata. This file is
            created by running :mod:`prep_input.py` followed by
            :mod:`download_gridmet_ee.py`
        out_dir (str): Directory to save comparison plots
        year_filter (list): single year (YYYY)

    Returns:
        None
    """

    if not os.path.isdir(out_dir):
        print('{} does not exist, creating directory'.format(out_dir))
        os.mkdir(out_dir)

    year = year_filter
    logging.info('\nProcessing Year: {}'.format(year))

    # # Import Station/GRIDMET meta data shapefile
    paired_data = pd.read_csv(input_csv, sep=',')

    # List of variables to compare (STATION/gridMET ORDER SHOULD MATCH)
    station_vars = ['TMin (C)', 'TMax (C)', 'wx_Ko_c', 'Rs (w/m2)',
                    'ws_2m (m/s)', 'Vapor Pres (kPa)', 'Calc_ETo (mm)',
                    'Calc_ETr (mm)']

    gridmet_vars = ['tmin_c', 'tmax_c', 'grid_Ko_c', 'srad_wm2', 'u2_ms',
                    'ea_kpa', 'eto_mm', 'etr_mm']

    # # Limit row processing range (testing)
    # start = 0
    # end = 1
    #Loop through each station/gridmet pair
    for index, row in paired_data.iterrows():
    # #    Limit iteration during development
    #     if index < start:
    #         continue
    #     if index >= end:
    #       break

        # clear previous datasets
        grid_data = []
        station_data = []

        station_path = row.STATION_FILE_PATH
        logging.info('\nStation: {}'.format(row.STATION_ID))

        # Skip If FILE DOES NOT EXIST
        if not os.path.exists(station_path):
            logging.info('SKIPPING {}. NO STATION FILE FOUND.'.format(
                station_path))
            continue
        else:
            station_data = pd.read_excel(station_path,
                                         sheet_name='Corrected Data')
            # Filter to specific year
            station_data = station_data[station_data['year']==year]

        # Import GRIDMET Data
        grid_path = row.GRIDMET_FILE_PATH
        # Skip if GRIDMET FILE DOES NOT EXIST
        if not os.path.exists(grid_path):
            print('SKIPPING {}. NO FILE GRIDMET FOUND.'.format(grid_path))
            continue
        else:
            grid_data = pd.read_csv(grid_path, sep=',',parse_dates=True,
                                    index_col='date')
            # Filter to specific year
            # grid_data = grid_data[grid_data['year'] == year]

            # Add Tdew to gridmet dataset Teten's equation ASCE REF-ET
            #  supporting equations Appendix 2-1

            grid_data['tdew_c'] = (116.91 + 237.3 * np.log(grid_data.ea_kpa)) /\
                                  (16.78 - np.log(grid_data.ea_kpa))

            # Calculate Tmin - Tdew = Ko for both Station and GridMET
            # Dew Point Depression
            grid_data['grid_Ko_c'] = grid_data.tmin_c - grid_data.tdew_c

            station_data['wx_Ko_c'] = station_data['TMin (C)'] - \
                                      station_data['TDew (C)']

            # Combine station and gridMET dataframes (only plotting variables)
            merged = []
            merged = pd.concat([station_data[station_vars],
                                grid_data[gridmet_vars]], axis=1,
                               join_axes=[station_data.index])
            # Remove results with na
            merged = merged.dropna()

            for month in range(1,13):
                logging.info('Month: {}'.format(month))
                monthly_data = merged[merged.index.month==month]

                if len(monthly_data.index)<= 5:
                     logging.info('Skipping. Less than 5 observations in '
                                  'month.')
                     continue
                # Output Folder
                out_folder =  os.path.join(out_dir, 'comaprison_plots',
                                           '{}'.format(
                                               row.STATION_ID.replace(" ","")))

                # Create path if it doesn't exist
                if not os.path.exists(out_folder):
                    os.makedirs(out_folder)

                # Output to HTML file
                out_file_path = os.path.join(out_folder, '{}_{:02}_{}.html')\
                    .format(row.STATION_ID.replace(" ", ""), month, year)
                output_file(out_file_path)

                station_vars = ['TMin (C)', 'TMax (C)', 'wx_Ko_c', 'Rs (w/m2)',
                                'ws_2m (m/s)', 'Vapor Pres (kPa)',
                                'Calc_ETo (mm)', 'Calc_ETr (mm)']

                gridmet_vars = ['tmin_c', 'tmax_c', 'grid_Ko_c', 'srad_wm2',
                                'u2_ms', 'ea_kpa', 'eto_mm', 'etr_mm']

                # list of x variables
                x_var_list= station_vars
                # list of y variables
                y_var_list= gridmet_vars
                # title list
                title_list= ['TMin', 'TMax', 'Ko' , 'Rs', 'WS 2m',
                               'ea', 'ETo', 'ETr']
                # timeseries y label list
                ts_ylabel_list = ['TMin (C)', 'TMax (C)', 'Ko (C)' ,'Rs (w/m2)',
                                  'WS 2m (m/s)', 'ea (kPa)', 'ETo (mm)',
                                  'ETr (mm)']
                # scatter xlabel list
                xlabel_list= ['Station TMin (C)', 'Station TMax (C)',
                              'Station Ko (C)','Station Rs (w/m2)',
                              'Station WS 2m (m/s)', 'Station ea (kPa)',
                              'Station ETo (mm)', 'Station ETr (mm)']
                # scatter ylabel list
                ylabel_list=['gridMET TMin (C)', 'gridMET TMax (C)',
                             'gridMET Ko (C)','gridMET Rs (w/m2)',
                             'gridMET WS 2m (m/s)', 'gridMET ea (kPa)',
                             'gridMET ETo (mm)', 'gridMET ETr (mm)']
                # legendx list
                legendx_list = ['Station'] * len(title_list)
                # legend y list
                legendy_list = ['gridMET'] * len(title_list)

                # empty list to append figures to
                figure_list = []

                # loop through and create figures for each variable using vars
                # and plot labels from lists above
                for i, (x_var, y_var, title, ts_ylabel, xlabel, ylabel, legendx,
                        legendy) in enumerate(zip(x_var_list, y_var_list,
                                                  title_list, ts_ylabel_list,
                                                  xlabel_list, ylabel_list,
                                                  legendx_list, legendy_list)):
                    if i == 0:
                        # Initial timeseries plot to establish xrange for link axes
                        p1 = figure(plot_width=800, plot_height=400,
                                    x_axis_type="datetime",title = title,
                                    y_axis_label = ts_ylabel)
                        p1.line(monthly_data.index.to_pydatetime(),
                                monthly_data[x_var],  color="navy",
                                alpha=0.5, legend=legendx,line_width=2)
                        p1.line(monthly_data.index.to_pydatetime(),
                                monthly_data[y_var],  color="red",
                                alpha=0.5, legend=legendy,line_width=2)
                    else:
                        # Timeseries plots after first pass
                        p1 = figure(plot_width=800, plot_height=400,
                                    x_axis_type="datetime",title = title,
                                    y_axis_label = ts_ylabel,
                                    x_range=p1.x_range)
                        p1.line(monthly_data.index.to_pydatetime(),
                                monthly_data[x_var],  color="navy", alpha=0.5,
                                legend=legendx,line_width=2)
                        p1.line(monthly_data.index.to_pydatetime(),
                                monthly_data[y_var],  color="red", alpha=0.5,
                                legend=legendy,line_width=2)

                    # 1 to 1 Plot
                    # Regression through Zero
                    # https://stackoverflow.com/questions/9990789/how-to-force-
                    # zero-interception-in-linear-regression/9994484#9994484
                    m = np.linalg.lstsq(monthly_data[x_var].values.reshape(-1,1),
                                        monthly_data[y_var], rcond=None)[0][0]
                    r_x, r_y = zip(*((i, i*m ) for i in range(
                        int(np.min([monthly_data[y_var],monthly_data[x_var]])-2),
                                     int(np.max([monthly_data[y_var],
                                                 monthly_data[x_var]])+3),1)))
                    # Plots
                    p2 = figure(plot_width=400, plot_height=400,
                                x_axis_label = xlabel, y_axis_label = ylabel,
                                title = 'Slope Through Zero: m = {}'.format(
                                    round(m,4)))
                    p2.circle(monthly_data[x_var], monthly_data[y_var],
                              size=15, color="navy", alpha=0.5)
                    p2.line([int(np.min([monthly_data[y_var],
                                         monthly_data[x_var]])-2),int(np.max(
                        [monthly_data[y_var],monthly_data[x_var]])+2)],
                             [int(np.min([monthly_data[y_var],
                                          monthly_data[x_var]])-2),int(np.max(
                                 [monthly_data[y_var],monthly_data[x_var]])+2)],
                              color = "black", legend = '1 to 1 line')
                    p2.line(r_x, r_y, color="red", legend = 'Reg thru zero')
                    p2.legend.location = "top_left"

                    # Append [p1, p2] to figure_list (create list of lists)
                    figure_list.append([p1, p2])

                # Plot all figures in list
                fig = gridplot(figure_list, toolbar_location="left")
                # Show the figure
    #            show(fig)
                # Save the figure
                save(fig)


def arg_parse():
    """
    Command line usage
    """
    parser = argparse.ArgumentParser(
        description=arg_parse.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    optional = parser._action_groups.pop()  # optionals listed second
    required = parser.add_argument_group('required arguments')
    required.add_argument(
        '-i', '--input', metavar='PATH', required=True,
        help='Input file containing station and gridMET IDs created by ' + \
             'prep_input.py')
    required.add_argument(
        '-o', '--out', metavar='PATH', required=True,
        help='Output directory to save comparison plots')
    required.add_argument(
        '-y', '--year', default=None, type=int,
        help='Year to analyze, single year (YYYY)')
    optional.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    parser._action_groups.append(optional)  # to avoid optionals listed first
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = arg_parse()

    logging.basicConfig(level=args.loglevel, format='%(message)s')
    logging.info('\n{}'.format('#' * 80))
    logging.info('{0:<20s} {1}'.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format('Current Directory:', os.getcwd()))
    logging.info('{0:<20s} {1}'.format(
        'Script:', os.path.basename(sys.argv[0])))

    main(input_csv=args.input, out_dir=args.out,
         year_filter=args.year)