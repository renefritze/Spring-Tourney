# -*- coding: utf-8 -*-
from bottle import request,send_file,route
from siteglobals import env, db, config
from utils import *
from backend import Player,ElementNotFoundException
from decorators import saferoute

@route('/tourneys/:filename')
def tourney_js(filename):
	return send_file( filename, root=os.getcwd()+'/tourneys/' )

@saferoute('/profile/:id', method='GET')
def output(session, id=0):
	if not id:
		raise ElementNotFoundException( id )
	try:
		player = session.query( Player ).filter( Player.id == id ).one()
	except:
		try: 
			player = session.query( Player ).filter( Player.nick == id ).one()
		except:
			raise ElementNotFoundException( id )

	ret = env.get_template('profile.html').render( player=player )
	session.close()
	return ret

