# -*- coding: utf-8 -*-
from bottle import route,request,send_file
from siteglobals import env, db, config
from utils import *
from backend import Match,Tourney

@route('/tourneys/:filename')
def tourney_js(filename):
	return send_file( filename, root=os.getcwd()+'/tourneys/' )


@route('/details', method='GET')
def output():
	try:
		session = db.sessionmaker()
		id = getSingleField( 'id', request )
		if not id:
			raise ElementNotFoundException( id )
		tourney = session.query( Tourney ).filter( Tourney.id == id ).first()
		if not tourney:
			raise ElementNotFoundException( id )

		q_matches = session.query( Match ).filter( Match.tourney_id == id )
		
		ret = env.get_template('tourney.html').render( tourney=tourney )
		session.close()
		return ret

	except Exception, m:
		return env.get_template('error.html').render(err_msg=str(m))

