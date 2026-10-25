#!/usr/bin/python
import sys, os

sys.path.append(os.path.dirname(__file__))

from cameras.run import record
a = record.recorder()
a.start()
