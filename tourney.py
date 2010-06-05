# -*- coding: utf-8 -*-
from bottle import route,request
from siteglobals import env, db, config
from utils import *
from backend import Match,Tourney
import jsonpickle

@route('/tourneys/:filename')
def tourney_js(filename):
	return send_file( filename, root=os.getcwd()+'/tourneys	/' )


@route('/details', method='GET')
def output():
	#try:
	session = db.sessionmaker()
	id = getSingleField( 'id', request )
	if not id:
		raise ElementNotFoundException( id )
	tourney = session.query( Tourney ).filter( Tourney.id == id ).first()
	if not tourney:
		raise ElementNotFoundException( id )

	q_matches = session.query( Match ).filter( Match.tourney_id == id )
	for m in q_matches.all():
		last = m
		print m,m.next
	
	with open('tourneys/%s.js'%id,'wb') as tourney_js:
		tourney_js.write( 'var matches = ' + jsonpickle.encode( q_matches.all() , unpicklable=False ) )

	
	ret = env.get_template('tourney.html').render( tourney=tourney )
	session.close()
	return ret

	#except Exception, m:
		#return env.get_template('error.html').render(err_msg=str(m))

