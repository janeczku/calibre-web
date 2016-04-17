#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *
import os
from cps import config
from werkzeug.security import generate_password_hash

dbpath = os.path.join(config.APP_DB_ROOT, "app.db")
engine = create_engine('sqlite:///{0}'.format(dbpath), echo=False)
Base = declarative_base()

ROLE_USER = 0
ROLE_ADMIN = 1
DEFAULT_PASS = "admin123"

class User(Base):
	__tablename__ = 'user'

	id = Column(Integer, primary_key = True)
	nickname = Column(String(64), unique = True)
	email = Column(String(120), unique = True, default = "")
	role = Column(SmallInteger, default = ROLE_USER)
	password = Column(String)
	kindle_mail = Column(String(120), default="")
	shelf = relationship('Shelf', backref = 'user', lazy = 'dynamic')
	whislist = relationship('Whislist', backref = 'user', lazy = 'dynamic')
	downloads = relationship('Downloads', backref= 'user', lazy = 'dynamic')

	def is_authenticated(self):
		return True

	def is_active(self):
		return True

	def is_anonymous(self):
		return False

	def get_id(self):
		return unicode(self.id)

	def __repr__(self):
		return '<User %r>' % (self.nickname)

class Shelf(Base):
	__tablename__ = 'shelf'

	id = Column(Integer, primary_key = True)
	name = Column(String)
	is_public = Column(Integer, default=0)
	user_id = Column(Integer, ForeignKey('user.id'))

	def __repr__(self):
		return '<Shelf %r>' % (self.name)


class Whislist(Base):
	__tablename__ = "wishlist"

	id = Column(Integer, primary_key=True)
	name = Column(String)
	is_public = Column(String)
	user_id = Column(Integer, ForeignKey('user.id'))

	def __init__(self):
		pass

	def __repr__(self):
		return '<Whislist %r>' % (self.name)


class BookShelf(Base):
	__tablename__ = 'book_shelf_link'

	id = Column(Integer, primary_key=True)
	book_id = Column(Integer)
	shelf = Column(Integer, ForeignKey('shelf.id'))

	def __repr__(self):
		return '<Book %r>' % (self.id)


class Downloads(Base):
	__tablename__ = 'downloads'

	id = Column(Integer, primary_key=True)
	book_id = Column(Integer)
	user_id = Column(Integer, ForeignKey('user.id'))

	def __repr__(self):
		return '<Download %r' % (self.book_id)

class Whish(Base):
	__tablename__ = 'whish'

	id = Column(Integer, primary_key=True)
	title = Column(String)
	url = Column(String)
	wishlist = Column(Integer, ForeignKey('wishlist.id'))

	def __repr__(self):
		return '<Whish %r>' % (self.title)

class Settings(Base):
	__tablename__ = 'settings'

	id = Column(Integer, primary_key=True)
	mail_server = Column(String)
	mail_port = Column(Integer, default = 25)
	mail_use_ssl = Column(SmallInteger, default = 0)
	mail_login = Column(String)
	mail_password = Column(String)
	mail_from = Column(String)

	def __repr__(self):
		#return '<Smtp %r>' % (self.mail_server)
		pass

def create_default_config():
	settings = Settings()
	settings.mail_server = "mail.example.com"
	settings.mail_port = 25
	settings.mail_use_ssl = 0
	settings.mail_login = "mail@example.com"
	settings.mail_password = "mypassword"
	settings.mail_from = "automailer <mail@example.com>"

	session.add(settings)
	session.commit()

def get_mail_settings():
	settings = session.query(Settings).first()

	if not settings:
	  return {}

	data = {
	  'mail_server': settings.mail_server,
	  'mail_port': settings.mail_port,
	  'mail_use_ssl': settings.mail_use_ssl,
	  'mail_login': settings.mail_login,
	  'mail_password': settings.mail_password,
	  'mail_from': settings.mail_from
	}

	return data

def create_admin_user():
	user = User()
	user.nickname = "admin"
	user.role = 1
	user.password = generate_password_hash(DEFAULT_PASS)

	session.add(user)
	session.commit()

Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

if not os.path.exists(dbpath):
	try:
		Base.metadata.create_all(engine)
		create_default_config()
		create_admin_user()
	except Exception:
		pass

