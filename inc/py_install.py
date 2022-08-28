import os
import logging
from ebbs import Builder

#Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class py_install(Builder):
    def __init__(this, name="Python Local Installer"):
        super().__init__(name)
        
        this.supportedProjectTypes.append("lib")
        this.supportedProjectTypes.append("bin")

        this.optionalKWArgs["requirements_file"] = "requirements.txt"

    #Required Builder method. See that class for details.
    def Build(this):
        # this.RunCommand(f"python3 -m pip install -U -r {this.requirements_file}")
        this.RunCommand("python3 -m pip install . -U")

    #Required Builder method. See that class for details.
    def DidBuildSucceed(this):
        return True #TODO: actually check result.