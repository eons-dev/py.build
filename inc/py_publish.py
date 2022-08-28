import os
import logging
from ebbs import Builder

#Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class pypi_publish(Builder):
    def __init__(this, name="PyPI Publisher"):
        super().__init__(name)
        
        this.supportedProjectTypes = []

        this.requiredKWArgs.append("pypi_username")
        this.requiredKWArgs.append("pypi_password")

    #Required Builder method. See that class for details.
    def Build(this):
        this.RunCommand(f"twine upload -u {this.pypi_username} -p {this.pypi_password} dist/*")

    #Required Builder method. See that class for details.
    def DidBuildSucceed(this):
        return True #TODO: check twine upload result.