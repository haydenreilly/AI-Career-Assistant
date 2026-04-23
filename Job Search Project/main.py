#!/usr/bin/env python3

import streamlit as st
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ui import *

if __name__ == "__main__":
    # This will be run by streamlit
    pass