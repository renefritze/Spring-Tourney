# -*- coding: utf-8 -*-
from bottle import request,send_file
from siteglobals import env
from utils import *
from backend import Player,Tourney
from decorators import saferoute

@saferoute('/', method='GET')
def output(session):
	ret = env.get_template('index.html').render( )
	return ret

