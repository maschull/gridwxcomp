# -*- coding: utf-8 -*-
"""
Read a CSV of climate station information and match each with nearest gridMET
cell information. Produce a CSV file that will be used for input for main
bias correction workflow.

TODO:
    add logging and example for docs.
"""

import os                                                                       
import argparse                                                                 
import logging                                                                  
import pandas as pd                                                             
import numpy as np        
from scipy import spatial

def main(station_file, gridmet_meta_file, out_path):
    """
    Take list of climate stations and merge each with overlapping gridMET cell
    information, write new CSV for next step in bias correction workflow.

    Raises:
        FileNotFoundError: if the gridmet_cell_data.csv file is not 
            passed as a command line argument and it is not in the current
            working directory.
    """
    # check if paths to input and output files were given, assign defaults
    if not gridmet_meta_file:
        gridmet_meta_file = 'gridmet_cell_data.csv'
    if not os.path.exists(gridmet_meta_file):
        raise FileNotFoundError('GridMET file path was not given and '\
                +'gridmet_cell_data.csv was not found in the current '\
                +'directory. Please assign the correct path or put '\
                +'gridmet_cell_data.csv in the current directory.\n')
    if not out_path:
        out_path='merged_input.csv'

    print('station list CSV: ', 
          os.path.join(os.getcwd(),station_file), 
          '\ngridMET cell info CSV: ', 
          os.path.join(os.getcwd(),gridmet_meta_file),
          '\nmerged CSV will be saved to: ', 
          os.path.join(os.getcwd(),out_path))
   
    # read climate station data, rename columns and condence then merge 
    # station info with overlapping gridMET and save CSV
    join_station_to_gridmet(station_file, 
            gridmet_meta_file, 
            out_path)

def gridMET_centroid(lat,lon):
    """
    Calculate the centroid lattitude and longitude for an arbitrary
    gridMET cell given its lower left corner coordinates. Used for
    finding closest neighboring climate station locations.
    
    Arguments:
        lat (float): decimal degree latitude of lower left corner 
            of a gridMET cell
        lon (float): decimal degree longitude of lower left corner 
            of a gridMET cell
            
    Returns:
        gridcell_lat,gridcell_lon (tuple): tuple of latitude and 
            longitude of gridMET cell centroid location.
    """
    gridmet_lon = -124.78749996666667
    gridmet_lat = 25.04583333333334
    gridmet_cs = 0.041666666666666664
    gridcell_lat = int(
        abs(lat - gridmet_lat) / gridmet_cs) * gridmet_cs +\
        gridmet_lat + gridmet_cs/2
    gridcell_lon = int(
        abs(lon - gridmet_lon) / gridmet_cs) * gridmet_cs +\
        gridmet_lon + gridmet_cs/2
    
    return gridcell_lat, gridcell_lon

def read_station_list(station_path):
    """
    Read station list CSV file and return condensed version.

    Arguments:
        station_path (str): path to CSV file containing list of climate
            stations that will later be used to calculate monthly
            bias rations to GridMET reference ET.

    Returns:
        station_list (:class:`pandas.DataFrame`): ``Pandas.DataFrame`` that
            contains FID, lattitude, longitude, elevation, and full file path 
            to each corresponding climate station time series file for
            later joining with gridMET cell information.
    """
    station_list = pd.read_csv(station_path)
    cols = ['FID','LATDECDEG','LONGDECDEG','Elev_m','FileName']
    station_list = station_list[cols]
    station_list.rename(columns={'LATDECDEG':'STATION_LAT',
                            'LONGDECDEG':'STATION_LON',
                            'Elev_m':'STATION_ELEV_M',
                            'FileName':'STATION_FILE_PATH'},
                   inplace=True)
    # get station name only for matching to file name
    station_list.STATION_FILE_PATH =\
            station_list.STATION_FILE_PATH.str.split('_').str.get(0)
    # look at path for station CSV, look for time series files in same directory
    station_path_tuple = os.path.split(station_path)
    path_root = station_path_tuple[0]
    file_name = station_path_tuple[1]
    # look in child directory that contains station CSV file
    if path_root != '' and file_name != '':
        file_names = os.listdir(path_root)   
    # if station CSV file is in same directory look there
    else:
        file_names = os.listdir(os.getcwd())
    # match station name with time series excel files full path,
    # assumes no other files in the directory have station names in their name
    # will accept files of any extension, e.g. xlx, csv, txt
    for station in station_list.STATION_FILE_PATH:
        match = [s for s in file_names if station in s][0]
        if match:
            station_list.loc[station_list.STATION_FILE_PATH == station,\
                'STATION_FILE_PATH'] = os.path.abspath(
                                       os.path.join(path_root,match))
        else:
            print('No file was found that matches station: ', station,
                    '\nin directory: ', os.path.abspath(path_root),
                    '\nskipping.\n')
            continue

    return station_list

def join_station_to_gridmet(station_list, gridmet_meta_path, out_path):
    """
    Read list of climate stations and match each with its
    closest GridMET cell, save CSV with information from both.

    Arguments:
        station_list (:class:`pandas.DataFrame`): ``Pandas.DataFrame``
            containing a list of climate stations with latitude, longitude,
            elevation, and ID fields.
        gridmet_meta_path (str): path to metadata CSV file that contains
            all gridMET cells for the contiguous United States. Can be
            found at ``etr-biascorrect/gridmet_cell_data.csv``.
        out_path (str): path to save output CSV, default is to save as 
            "merged_input.csv" to current working directory if not passed
            at command line to script.

    Returns:
        None

    Note:
        The CSV file that is saved contains latitude, longitude, and elevation
        fields for both the station and nearest gridMET cell. Those refering
        to the climate station are prefixed with "STATION_" and those refering
        to gridMET have no prefix.
    """
    stations = read_station_list(station_list)
    gridmet_meta = pd.read_csv(gridmet_meta_path)
    gridmet_pts = list(zip(gridmet_meta.LAT,gridmet_meta.LON))
    # calculate centroids, doesn't seem to work on GridMET meta file
    gridmet_pts = [gridMET_centroid(pt[0],pt[1]) for pt in gridmet_pts]
    # scipy KDTree to find nearest neighbor between station and centroids
    tree = spatial.KDTree(gridmet_pts)
    # loop through each station find closest GridMET
    for index, row in stations.iterrows():
        try:
            station_lat = row.STATION_LAT
            station_lon = row.STATION_LON
            pt = np.array([station_lat,station_lon])
            # index of nearest GridMET point, same as GRIDMET_ID
            ind = tree.query(pt)[1]
            stations.loc[index,'GRIDMET_ID'] = ind
        except:
            print('Failed to find matching gridMET info for climate '\
                    +'station with FID = ', row.FID,'\n')  
    stations.GRIDMET_ID = stations.GRIDMET_ID.astype(int)
    out_df = stations.merge(gridmet_meta,on='GRIDMET_ID')
    out_df = out_df.reindex(columns=['GRIDMET_ID',
                                     'LAT',
                                     'LON',
                                     'ELEV_M',
                                     'FID',
                                     'STATION_LAT',
                                     'STATION_LON',
                                     'STATION_ELEV_M',
                                     'STATION_FILE_PATH'])
    # if no out_path given save to current working directory
    if not out_path:
        out_df.to_csv('merged_input.csv', index=False)
    else:
        out_df.to_csv(out_path, index=False)

def arg_parse():
    """
    Parse command line arguments for merging climate station and gridMET
    metadata into a single table (CSV file).
    """
    parser = argparse.ArgumentParser(
        description='Create input table for gridMET bias correction',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--input', metavar='PATH', required=True,
        help='Input CSV file of climate stations')
    parser.add_argument(
        '-g', '--gridmet', metavar='PATH', required=False,
        help='GridMET master CSV file with cell data, packaged with '+\
             'etr-biascorrect at etr-biascorrect/gridmet_cell_data.csv '+\
             'if not given it needs to be located in the currect directory')
    parser.add_argument(
        '-o', '--out', metavar='PATH', required=False,
        help='Optional output path for CSV with merged climate/gridMET data')
#    parser.add_argument(
#        '--debug', default=logging.INFO, const=logging.DEBUG,
#        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = arg_parse()

    main(station_file=args.input, 
         gridmet_meta_file=args.gridmet,
         out_path=args.out)