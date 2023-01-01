import os
import logging
from ebbs import Builder

#Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class py_test(Builder):
    def __init__(this, name="Python Builder"):
        super().__init__(name)

        this.requiredKWArgs.append("test_path") #path to tests

    #Required Builder method. See that class for details.
    def Build(this):
        options = []
        if (this.executor.verbosity > 3):
            options.append("-o log_cli=true")
        if (this.executor.verbosity > 3):
            options.append("-o log_cli_level=debug")

        this.RunCommand(f"pytest {' '.join(options)} {this.test_path}/*")    
    
    #Required Builder method. See that class for details.
    def DidBuildSucceed(this):
        return True #TODO: check test results.