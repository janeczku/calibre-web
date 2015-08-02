#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
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
DB_ROOT = check_setting_str(CFG, 'General', 'DB_ROOT', os.path.join(os.getcwd(), "Calibre Library"))
TEMPLATEDIR = check_setting_str(CFG, 'General', 'TEMPLATEDIR', os.path.join(os.getcwd(), "views"))
MAIN_DIR = check_setting_str(CFG, 'General', 'MAIN_DIR', os.getcwd())
PORT = check_setting_int(CFG, 'General', 'PORT', 8083)
NEWEST_BOOKS = check_setting_str(CFG, 'General', 'NEWEST_BOOKS', 60)
RANDOM_BOOKS = check_setting_int(CFG, 'General', 'RANDOM_BOOKS', 6)
ALL_BOOKS = check_setting_str(CFG, 'General', 'ALL_BOOKS', 100)

CheckSection('Mail')
MAIL_SERVER = check_setting_str(CFG, 'Mail', 'MAIL_SERVER', 'mail.example.com')
MAIL_LOGIN = check_setting_str(CFG, 'Mail', 'MAIL_LOGIN', "mail@example.com")
MAIL_PASSWORD = check_setting_str(CFG, 'Mail', 'MAIL_PASSWORD', "mypassword")
MAIL_PORT = check_setting_int(CFG, 'Mail', 'MAIL_PORT', 25)
MAIL_FROM = check_setting_str(CFG, 'Mail', 'MAIL_FROM', "library automailer <mail@example.com>")

CheckSection('Advanced')
TITLE_REGEX = check_setting_str(CFG, 'Advanced', 'TITLE_REGEX', '^(Der|Die|Das|Ein|Eine)\s+')
DEVELOPMENT = bool(check_setting_int(CFG, 'Advanced', 'DEVELOPMENT', 1))
FIRST_RUN = bool(check_setting_int(CFG, 'Advanced', 'FIRST_RUN', 1))

SYS_ENCODING="UTF-8"

configval={}
configval["DB_ROOT"] = DB_ROOT
configval["TEMPLATEDIR"] = TEMPLATEDIR
configval["MAIN_DIR"] = MAIN_DIR
configval["PORT"] = PORT
configval["NEWEST_BOOKS"] = NEWEST_BOOKS
configval["ALL_BOOKS"] = ALL_BOOKS
configval["DEVELOPMENT"] = DEVELOPMENT
configval["MAIL_SERVER"] = MAIL_SERVER
configval["MAIL_FROM"] = MAIL_FROM
configval["MAIL_PORT"] = MAIL_PORT
configval["MAIL_LOGIN"] = MAIL_LOGIN
configval["MAIL_PASSWORD"] = MAIL_PASSWORD
configval["TITLE_REGEX"] = TITLE_REGEX
configval["FIRST_RUN"] = FIRST_RUN

def save_config(configval):
    new_config = ConfigObj()
    new_config.filename = CONFIG_FILE
    new_config['General'] = {}
    new_config['General']['DB_ROOT'] = configval["DB_ROOT"]
    new_config['General']['TEMPLATEDIR'] = configval["TEMPLATEDIR"]
    new_config['General']['MAIN_DIR'] = configval["MAIN_DIR"]
    new_config['General']['PORT'] = configval["PORT"]
    new_config['General']['NEWEST_BOOKS'] = configval["NEWEST_BOOKS"]
    new_config['General']['ALL_BOOKS'] = configval["ALL_BOOKS"]
    new_config['Mail'] = {}
    new_config['Mail']['MAIL_PORT'] = int(configval["MAIL_PORT"])
    new_config['Mail']['MAIL_SERVER'] = configval["MAIL_SERVER"]
    new_config['Mail']['MAIL_FROM'] = configval["MAIL_FROM"]
    new_config['Mail']['MAIL_LOGIN'] = configval["MAIL_LOGIN"]
    new_config['Mail']['MAIL_PASSWORD'] = configval["MAIL_PASSWORD"]
    new_config['Advanced'] = {}
    new_config['Advanced']['TITLE_REGEX'] = configval["TITLE_REGEX"]
    new_config['Advanced']['DEVELOPMENT'] = int(configval["DEVELOPMENT"])
    new_config['Advanced']['FIRST_RUN'] = int(configval["FIRST_RUN"])
    new_config.write()
    return "Saved"

save_config(configval)
