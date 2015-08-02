#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
base_path = os.path.dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.append(os.path.join(base_path, 'lib'))

from cps import ub
from werkzeug.security import generate_password_hash

nickname = raw_input('Please select a username: ')
password = raw_input("Please select a password: ")

user = ub.User()
user.nickname = nickname
user.role = 1
user.password = generate_password_hash(password)

try:
	ub.session.add(user)
	ub.session.commit()
	print ""
	print "Admin User created: %s with password: %s" % (user.nickname, password)
	print "Please start the server again: 'python cps.py'"
except:
	print "There was an error creating the user: %s" % nickname