import os
import logging
import eons as e

class SAMPLE(e.Executor):

    def __init__(this):

        super().__init__(name="sample package", descriptionStr="TESTING ONLY")

    #Override of eons.Executor method. See that class for details
    def Configure(this):
        super().Configure()

    #Override of eons.Executor method. See that class for details
    def UserFunction(this, **kwargs):
        super().UserFunction(**kwargs)
        logging.info("hello world")