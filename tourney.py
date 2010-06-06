# -*- coding: utf-8 -*-
from bottle import route,request,send_file
from siteglobals import env, db, config
from utils import *
from backend import Match,Tourney
import os
from decorators import *

@route('/tourneys/:filename')
def tourney_js(filename):
	return send_file( filename, root=os.getcwd()+'/tourneys/' )

@saferoute('/tourney/:id', method='GET')
def output(session,id=1):
	tourney = session.query( Tourney ).filter( Tourney.id == id ).first()
	if not tourney:
		raise ElementNotFoundException( id )

	ret = env.get_template('tourney.html').render( tourney=tourney )
	return ret

