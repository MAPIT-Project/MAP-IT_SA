#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 19 15:27:06 2024

@author: marco
"""
import os
import sys


PROJECT_PATH = os.getcwd()

SOURCE_PATH = os.path.join(
    PROJECT_PATH,"src"
)
sys.path.append(SOURCE_PATH)

SOURCE_PATH = os.path.join(
    PROJECT_PATH,"tests"
)
sys.path.append(SOURCE_PATH)