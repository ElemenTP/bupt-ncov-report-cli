#!/usr/bin/python3
import os
from subprocess import call

import pkg_resources

filepath = os.path.dirname(os.path.realpath(__file__))

for dist in pkg_resources.working_set:
    if dist.location.startswith(filepath):
        call(
            "python3 -m pip install --upgrade " + "".join(dist.project_name), shell=True
        )
