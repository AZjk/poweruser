# activate your environment 
python fast_G2_average.py flist_short.txt -o test_average.hdf --num-workers 56 --precision single

# If using G2average_master_plan.py which calls fast_G2_average.py, do this innstead.
# Parameters needed for the G2 average can be found in G2average_info
# The standard Bluesky environment '8idi_bits' will work for this code
python G2average_master_plan.py G2average_info.json
