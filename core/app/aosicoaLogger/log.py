import logging
import os
import sys

class AosiLog:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        '''self.logger.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.file_handler = logging.FileHandler('log/aosi.log')
        self.file_handler.setLevel(logging.DEBUG)
        self.file_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.file_handler)
        self.stream_handler = logging.StreamHandler(sys.stdout)
        self.stream_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.stream_handler)
        self.logger.info('Logger initialized')'''


    def welcome(self):
        self.logger.info('Welcome to AOSICOA')
        #print('Welcome to AOSICOA')

        with open("aosicoaLogger/welcome1.txt", 'r') as f:
            print(f.read())
        print(f"\nREST API: /docs")


log = AosiLog()
