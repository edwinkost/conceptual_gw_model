#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import os
import sys
import shutil
import gc

import pcraster as pcr

# output folder
out_folder = "/quanta1/home/sutan101/github/edwinkost/conceptual_gw_model/get_upstream_areas/output/"

# open and read txt file containing a table of edwin_code, lat_usgs, lon_usgs, and usgs_drain_area_km2
table_txt_file_name = "edwin_code_and_usgs_drain_area_km2.txt"
table_txt_file = open(table_txt_file_name, "r")
table_lines = table_txt_file.readlines()
table_txt_file.close()

# cleaning output folder
if os.path.exists(out_folder) and (" " not in out_folder) and (out_folder != ""):
    cmd = "rm -r " + out_folder
    os.system(cmd)

# prepare output folder 
if os.path.exists(out_folder) == False: os.makedirs(out_folder)
os.chdir(out_folder)


#~ sutan101@node001.cluster:/scratch/depfg/sutan101/data/pcrglobwb2_input_release/version_2019_11_beta_extended/pcrglobwb2_input/global_05min/routing/ldd_and_cell_area$ ls -lah
#~ total 188M
#~ drwxr-xr-x 2 sutan101 depfg    7 Nov 12  2019 .
#~ drwxr-xr-x 5 sutan101 depfg    3 Nov 11  2019 ..
#~ -rwxr-xr-x 1 sutan101 depfg  36M Nov 11  2019 cellsize05min.correct.map
#~ -rw-r--r-- 1 sutan101 depfg  36M Nov 14  2019 cellsize05min_correct.nc
#~ -rw-r--r-- 1 sutan101 depfg  36M Nov 14  2019 cellsize05min.correct.nc
#~ -rw-r--r-- 1 sutan101 depfg  129 Nov 14  2019 hydroworld_source.txt
#~ -rwxr-xr-x 1 sutan101 depfg 8.9M Nov 11  2019 lddsound_05min.map
#~ -rw-r--r-- 1 sutan101 depfg  36M Nov 14  2019 lddsound_05min.nc
#~ -rw-r--r-- 1 sutan101 depfg  36M Nov 14  2019 lddsound_05min_unmask.nc


# calculate pcrglobwb catchment area
# - reading input files
ldd_file_name = "/scratch/depfg/sutan101/data/pcrglobwb2_input_release/version_2019_11_beta_extended/pcrglobwb2_input/global_05min/routing/ldd_and_cell_area/lddsound_05min.map"
ldd = pcr.readmap(ldd_file_name)
cell_area_file_name =  "/scratch/depfg/sutan101/data/pcrglobwb2_input_release/version_2019_11_beta_extended/pcrglobwb2_input/global_05min/routing/ldd_and_cell_area/cellsize05min.correct.map"
cellarea = pcr.readmap(cell_area_file_name) 
# - calculate pcrglobwb catchment area (km2)
pcrglobwb_catchment_area_km2 = pcr.catchmenttotal(cellarea, ldd) / 1e6

# loop through the table
#~ for table_line in table_lines[1:len(table_lines) + 1]:
for table_line in table_lines[1:3]:

    # select one line (representing each station) and save it to a tmp file
    tmp_file_name = "one_line.tmp"
    if os.path.exists(tmp_file_name): os.remove(tmp_file_name)
    one_line_txt_file = open(tmp_file_name, "w")
    one_line_txt_file.write(table_line)
    one_line_txt_file.close()
    
    # edwin_code.map: col2map --clone lddsound_05min.map -N -x 3 -y 2 -v 1 one_line_from_edwin_code_and_usgs_drain_area_km2.txt edwin_code.map
    cmd = "col2map --clone " + ldd_file_name + \
          " -N -x 3 -y 2 -v 1 " + ldd_file_name + " edwin_code.map"
    print(cmd)
    os.system(cmd)
    edwin_code = pcr.readmap( "edwin_code.map" )

    # usgs_drain_area.map: col2map --clone lddsound_05min.map -S -x 3 -y 2 -v 4 one_line_from_edwin_code_and_usgs_drain_area_km2.txt usgs_drain_area.map
    cmd = "col2map --clone " + ldd_file_name + \
          " -S -x 3 -y 2 -v 4 " + ldd_file_name + " usgs_drain_area.map"
    print(cmd)
    os.system(cmd)
    usgs_drain_area_km2 = pcr.readmap( "usgs_drain_area.map" )

    # pcrglobwb catchment area
    edwin_code_pcrglobwb_catchment_area_km2 = pcr.ifthen(defined(edwin_code), pcrglobwb_catchment_area_km2)

    # calculate the absolute difference
    abs_diff = pcr.abs(usgs_drain_area - edwin_code_pcrglobwb_catchment_area_km2)
    
    # make correction if required 
    abs_diff_value = pcr.cellvalue(pcr.mapmaximum(abs_diff), 1)[0]
    usgs_drain_area_km2 =  pcr.cellvalue(pcr.mapmaximum(usgs_drain_area_km2), 1)[0]

    if (usgs_drain_area_km2 > 1000.0) and \
       (abs_diff_value > 0.10 * usgs_drain_area_km2):
        
        # class within 0.1 arc degree windows
        edwin_code = pcr.windowmajority(edwin_code, 0.1)      

        # find the most accurate cell: 
        areaorder = pcr.areaorder( windowmaximum(usgs_drain_area_km2, 0.1) - pcrglobwb_catchment_area_km2, edwin_code)
        
        # select pixel
        edwin_code = pcr.ifthen(areaorder == 1., edwin_code)
        
        # pcrglobwb catchment area
        edwin_code_pcrglobwb_catchment_area_km2 = pcr.ifthen(areaorder == 1., pcrglobwb_catchment_area_km2)

    
    # save using map2col
    pcr.report(edwin_code, "edwin_code.map")
    pcr.report(edwin_code_pcrglobwb_catchment_area_km2, "edwin_code_pcrglobwb_catchment_area_km2.map")
    cmd = "map2col edwin_code.map edwin_code_pcrglobwb_catchment_area_km2.map edwin_code_pcrglobwb_catchment_area_km2.txt" 
    print(cmd)
    os.system(cmd)

    # save columnn file
    cmd = "cat edwin_code_pcrglobwb_catchment_area_km2.txt >> table_edwin_code_pcrglobwb_catchment_area_km2 edwin_code_pcrglobwb_catchment_area_km2.txt"
    print(cmd)
    os.system(cmd)

    # show the content of columnn file
    cmd = "cat edwin_code_pcrglobwb_catchment_area_km2.txt"
    print(cmd)
    os.system(cmd)
    
    # delete temporary map and tmp file
    cmd = "rm -r *.map *.tmp"
    print(cmd)
    os.system(cmd)
    

