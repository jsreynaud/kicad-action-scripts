from __future__ import print_function
import pprint
import traceback
import sys

print("Starting plugin CircularZone")
try:
    from .CircularZone import *
    CircularZone().register()
except Exception as e:
    traceback.print_exc(file=sys.stdout)
    pprint.pprint(e)
