# -*- coding: utf-8 -*-
from bottle import route,request,send_file
from siteglobals import env, db, config
from utils import *
from backend import Player,Tourney

@route('/', method='GET')
def output():
	try:
		session = db.sessionmaker()
				
		ret = env.get_template('index.html').render( )
		session.close()
		return ret

	except Exception, m:
		return env.get_template('error.html').render(err_msg=str(m))

