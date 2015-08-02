#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *
import os
from cps import config

dbpath = os.path.join(config.MAIN_DIR, "app.db")
engine = create_engine('sqlite:///{0}'.format(dbpath), echo=False)
Base = declarative_base()

ROLE_USER = 0
ROLE_ADMIN = 1

class User(Base):
	__tablename__ = 'user'

	id = Column(Integer, primary_key = True)
	nickname = Column(String(64), unique = True)
	email = Column(String(120), unique = True)
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

Base.metadata.create_all(engine)
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()
