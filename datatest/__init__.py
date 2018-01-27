# -*- coding: utf-8 -*-

# Datatest Core API (__all__ property defined in submodules)
from .validation import *  # Validation error and functions.
from .difference import *  # Difference classes.
from .allowance import *   # Allowance context mangers.

# Unittest-style API
from .case import DataTestCase
from .runner import mandatory
from .runner import skip
from .runner import skipIf
from .runner import skipUnless
from .runner import DataTestRunner
from .main import DataTestProgram
from .main import main

# Data Access API
from ._dataaccess.dataaccess import DataSource
from ._dataaccess.dataaccess import DataQuery
from ._dataaccess.dataaccess import DataResult
from ._dataaccess.dataaccess import working_directory
from ._dataaccess.get_reader import get_reader

__version__ = '0.8.4.dev0'

required = mandatory  # Temporary alias for old "required" decorator.
