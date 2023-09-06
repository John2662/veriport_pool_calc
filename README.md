# veriport_pool_calc


# Run all tests in the directory veriport_input:
for i in veriport_input/*.csv; do python main.py --dir test --file $i; done

# run random tests:
python main.py --dir test


# This module is set up so it can be run as a stand alone where data is loaded
# from a file and the calculations are made on that data
#
# We need to replace DataPersist in the Calculator class with
# VeriportDataBaseInterface
# which we still need to implement.
# The VeriportDataBaseInterface will likely have a foreign key to the
# RandomSample object (maybe a OneToOneField)
# It will need to get these data structures:
#  - population as a dict from days of the pool year to the number of participanyts on that day
#  - inception date
#  - testing schedule (as an integer -> 12 == monthly, 4 == quarterly)
#  - previous calculations for this RandomSample for the pool year
# It will also have to persist the results each period