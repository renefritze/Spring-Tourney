# -*- coding: utf-8 -*-
from bottle import route
from siteglobals import is_debug, db,env
class saferoute(object):
	def __init__( self, path=None, method='GET' ):
		self.path = path
		self.method = method
		
	def __call__(self, f):
			@route( self.path, self.method )
			def wrapper(*args, **kargs):
				print 'koko'
				global is_debug
				session = None
				if is_debug:
					session = db.sessionmaker()
					ret = f(session,*args, **kargs)
				else:
					try:
						session = db.sessionmaker()
						ret = f(session,*args,**kargs)
					except Exception, m:
						if session:
							session.close()
						return env.get_template('error.html').render(err_msg=str(m))
				if session:
					session.close()
				return ret		
			return wrapper
