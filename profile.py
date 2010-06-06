# -*- coding: utf-8 -*-
from bottle import route,request,send_file
from siteglobals import env, db, config
from utils import *
from backend import Player,ElementNotFoundException

@route('/tourneys/:filename')
def tourney_js(filename):
	return send_file( filename, root=os.getcwd()+'/tourneys/' )


@route('/profile/:id', method='GET')
def output(id=0):
	try:
		session = db.sessionmaker()
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

	except Exception, m:
		return env.get_template('error.html').render(err_msg=str(m))

