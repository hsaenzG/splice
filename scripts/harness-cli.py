#!/usr/bin/env python3
"""Deprecated: use splice-cli.py instead. Kept for backward compatibility."""
import os, sys
sys.argv[0] = os.path.join(os.path.dirname(__file__), "splice-cli.py")
exec(open(sys.argv[0]).read())
