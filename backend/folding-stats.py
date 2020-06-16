
#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Generali AG, Rene Fuehrer <rene.fuehrer@generali.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os
import sys
import json
import re
import subprocess
from json import loads, dumps
import sqlite3
import datetime
import requests
from datetime import datetime as dt
import logging


def initialize_logger(output_dir):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
     
    # create console handler and set level to info
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)-8s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
 
    # create error file handler and set level to error
    handler = logging.FileHandler(os.path.join(output_dir, "folding-stats-error.log"),"a", encoding=None, delay="true")
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)-8s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
 
    # create debug file handler and set level to debug
    handler = logging.FileHandler(os.path.join(output_dir, "folding-stats.log"),"a")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)-8s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class DictQuery(dict):
    '''
    Dictionary class to get JSON hierarchical data structures

    Parameters:
        dict (dict): Dictionary with hierachical structures

    Returns:
        val (dict): Dictionary where hierachical structured keys be seperated with slashes
    '''
    def get(self, path, default=None):
        keys = path.split("/")
        val = None

        for key in keys:
            if val:
                if isinstance(val, list):
                    val = [v.get(key, default) if v else None for v in val]
                else:
                    val = val.get(key, default)
            else:
                val = dict.get(self, key, default)

            if not val:
                break

        return val

def getconfig(this_dict, this_setting, this_default=""):
    return DictQuery(this_dict).get(this_setting, this_default)



mypath = os.path.dirname(os.path.realpath(sys.argv[0]))
#print("mypath = ", mypath)

initialize_logger(mypath+"/logs/")

logging.debug("Script was started at %s", (dt.now()))

# Load config
config_file = mypath + "/folding-stats.json"
with open(config_file, 'r') as cfg:
    config = loads(cfg.read())

logging.info("Checking Folding@Home stats...")
url=getconfig(config,"baseurl","")+str(getconfig(config,"team"))
myResponse = requests.get(url)

# For successful API call, response code will be 200 (OK)
if(myResponse.ok):
    jStats = json.loads(myResponse.content)

    # read rid file (old rank)
    rank_old = 0
    rank_new = 0
    if getconfig(config,"database/rid","") != "":
        try:
            with open(mypath + "/" + getconfig(config,"database/rid",""), 'r') as f:
                rank_old = f.readline()
                f.close()
            logging.debug("Previous rank : %s", (str(rank_old)))
        except IOError:
            logging.warning("Could not read file: %s", (mypath + "/" + getconfig(config,"database/rid","")))
            pass

    rank_new = getconfig(jStats,"rank","0")
    logging.debug("Current rank  : %s", (rank_new))

    # write rid file (new rank (or old if not updated))
    rank_updated = False
    # rank id file
    if getconfig(config,"database/rid","") != "":
        # write csv if value is given
        with open(mypath + "/" + getconfig(config,"database/rid",""), 'w') as f:
            f.write(str(rank_new))
            f.close()

        if int(rank_new) != int(rank_old):
            rank_updated = True

    # update database/csv if rank was changed
    if rank_updated == True:
        logging.info("Rank changed (%s -> %s)", rank_old, rank_new)

        if getconfig(config,"database/sqlite","") != "":
            # write database
            logging.info("Rank changed. SQlite is being updated...")
            file_db = mypath + "/" + getconfig(config,"database/sqlite","")
            logging.debug("filename: %s", (file_db))
            conn = sqlite3.connect(file_db)
            cur = conn.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS stats(datetime TEXT, team integer, rank integer)')
            cur.execute("INSERT INTO stats VALUES(datetime('now', 'localtime'), 263581, "+str(rank_new)+")")
            conn.commit()
            # Close the connection
            conn.close()
        else:
            logging.info("No CSV file given.")    

        # write csv
        if getconfig(config,"database/csv","") != "":
            logging.info("Rank changed. CSV file is being updated...")

            # write csv if value is given
            file_csv = mypath + "/" + getconfig(config,"database/csv","")
            logging.debug("filename: %s", (file_csv))
            with open(file_csv, 'a') as f:
                x = datetime.datetime.now()
                f.write(x.strftime("%Y-%m-%d %X") + ","+str(getconfig(config,"team"))+","+str(rank_new)+"\n")
                f.close()
        else:
            logging.info("No CSV file given.")    

    else:
        logging.info("Rank unchanged (%s).", rank_new)
        pass

else:
  # If response code is not ok (200), print the resulting http error code with description
    myResponse.raise_for_status()