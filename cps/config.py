#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from configobj import ConfigObj


CONFIG_FILE= os.path.join(os.getcwd(), "config.ini")
CFG = ConfigObj(CONFIG_FILE)

def CheckSection(sec):
    """ Check if INI section exists, if not create it """
    try:
        CFG[sec]
        return True
    except:
        CFG[sec] = {}
        return False

def check_setting_str(config, cfg_name, item_name, def_val, log=True):
    try:
        my_val = config[cfg_name][item_name]
        if my_val == "":
            my_val = def_val
            config[cfg_name][item_name] = my_val
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val
    return my_val


def check_setting_int(config, cfg_name, item_name, def_val):
    try:
        my_val = int(config[cfg_name][item_name])
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val
    return my_val

CheckSection('General')
DB_ROOT = check_setting_str(CFG, 'General', 'DB_ROOT', "")
APP_DB_ROOT = check_setting_str(CFG, 'General', 'APP_DB_ROOT', os.getcwd())
MAIN_DIR = check_setting_str(CFG, 'General', 'MAIN_DIR', os.getcwd())
LOG_DIR = check_setting_str(CFG, 'General', 'LOG_DIR', os.getcwd())
PORT = check_setting_int(CFG, 'General', 'PORT', 8083)
NEWEST_BOOKS = check_setting_str(CFG, 'General', 'NEWEST_BOOKS', 60)
RANDOM_BOOKS = check_setting_int(CFG, 'General', 'RANDOM_BOOKS', 4)

CheckSection('Advanced')
TITLE_REGEX = check_setting_str(CFG, 'Advanced', 'TITLE_REGEX', '^(A|The|An|Der|Die|Das|Den|Ein|Eine|Einen|Dem|Des|Einem|Eines)\s+')
DEVELOPMENT = bool(check_setting_int(CFG, 'Advanced', 'DEVELOPMENT', 0))
PUBLIC_REG = bool(check_setting_int(CFG, 'Advanced', 'PUBLIC_REG', 0))
UPLOADING = bool(check_setting_int(CFG, 'Advanced', 'UPLOADING', 0))

SYS_ENCODING="UTF-8"

if DB_ROOT == "":
    print "Calibre database directory (DB_ROOT) is not configured"
    sys.exit(1)

configval={}
configval["DB_ROOT"] = DB_ROOT
configval["APP_DB_ROOT"] = APP_DB_ROOT
configval["MAIN_DIR"] = MAIN_DIR
configval["LOG_DIR"] = LOG_DIR
configval["PORT"] = PORT
configval["NEWEST_BOOKS"] = NEWEST_BOOKS
configval["DEVELOPMENT"] = DEVELOPMENT
configval["TITLE_REGEX"] = TITLE_REGEX
configval["PUBLIC_REG"] = PUBLIC_REG
configval["UPLOADING"] = UPLOADING

def save_config(configval):
    new_config = ConfigObj()
    new_config.filename = CONFIG_FILE
    new_config['General'] = {}
    new_config['General']['DB_ROOT'] = configval["DB_ROOT"]
    new_config['General']['APP_DB_ROOT'] = configval["APP_DB_ROOT"]
    new_config['General']['MAIN_DIR'] = configval["MAIN_DIR"]
    new_config['General']['LOG_DIR'] = configval["LOG_DIR"]
    new_config['General']['PORT'] = configval["PORT"]
    new_config['General']['NEWEST_BOOKS'] = configval["NEWEST_BOOKS"]
    new_config['Advanced'] = {}
    new_config['Advanced']['TITLE_REGEX'] = configval["TITLE_REGEX"]
    new_config['Advanced']['DEVELOPMENT'] = int(configval["DEVELOPMENT"])
    new_config['Advanced']['PUBLIC_REG'] = int(configval["PUBLIC_REG"])
    new_config['Advanced']['UPLOADING'] = int(configval["UPLOADING"])
    new_config.write()
    return "Saved"

save_config(configval)
