# -*- coding: utf-8 -*-
from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *
import datetime, os, math,random

current_db_rev = 1
Base = declarative_base()

class Roles:
	"""need to be strongly ordered integers"""
	GlobalBanned= -1 #special role mapped in Bans class, not Player
	Banned 		= 0 #special role mapped in Bans class, not Player
	Unknown		= 1
	User		= 2
	Verified	= 3
	LadderAdmin	= 4 #special role mapped in ladderoptions, not Player class
	GlobalAdmin	= 5
	Owner		= 42

players_team = Table('players_team', Base.metadata,
	Column('team_id', Integer, ForeignKey('teams.id')),
	Column('player_id', Integer, ForeignKey('players.id'))
)

class Tourney(Base):
	__tablename__ 	= 'tourneys'
	id 				= Column( Integer, primary_key=True )
	description		= Column( Text )

	def __init__(self,db,teams_,description):
		session = db.sessionmaker()
		self.teams = teams_
		#random.shuffle(self.teams)
		self.description = description
		actual_team_num = len(teams_)
		padded_team_num = int( math.pow( 2, math.ceil( math.log( actual_team_num ) ) + 1 ) )
		print 'got %d teams, padded to %d teams'%(actual_team_num,padded_team_num)
		for i in range( actual_team_num, padded_team_num ):
			self.teams.append( db.nullTeam )
		rounds = int( math.log( padded_team_num ) + 1 )
		print 'doing %d rounds'%rounds
		
		matches = []
		#first round
		for i in range( int(padded_team_num / 2 ) ):
			m = Match(self)
			#take teams from opposite end avoids null-null Matches
			m.teamA_id = self.teams[i].id
			m.teamB_id = self.teams[-(1+i)].id
			matches.append( m )
		session.add_all( matches )
		session.commit()
		
		#next rounds are combinations of matches
		for r in range( 1, rounds ):
			next_matches = []
			for i in range( int(len(matches) / 2 ) ):
				m = Match(self)
				m.prev_matchA_id = matches[2*i].id
				m.prev_matchB_id = matches[2*i+1].id
				next_matches.append( m )
			session.add_all( next_matches )
			session.commit()
			matches = next_matches #next round consists of  pairs of this round's matches
		session.close()
				
	
class Player(Base):
	__tablename__ 	= 'players'
	id 				= Column( Integer, primary_key=True )
	nick 			= Column( String(50),index=True, unique=True )
	pwhash 			= Column( String(180) )
	email 			= Column( String(180) )
	role			= Column( Integer )
	do_hide_results = Column( Boolean )

	def __init__(self, nick='noname', role=Roles.User, pw=''):
		self.nick 		= nick
		self.role 		= role
		do_hide_results = False

	def __str__(self):
		return "Player(id:%d) %s "%(self.id, self.nick)
	
class Team(Base):
	__tablename__ 	= 'teams'
	id 				= Column( Integer, primary_key=True )
	nick 			= Column( String(100),index=True )
	#tourney_id		= Column( Integer, ForeignKey( Tourney.id ) )

	players = relationship('Player', secondary=players_team, backref='teams')
	
	def __init__(self, nick='noname' ):
		self.nick 		= nick

	def __str__(self):
		#return "Team(id:%d) %s "%(self.id, ', '.join(self.players) )
		return "Team %s(id:%d) %d player"%(self.nick,self.id, len(self.players) )

class Match(Base):
	__tablename__ 	= 'matches'
	id 				= Column( Integer, primary_key=True )
	tourney_id		= Column( Integer, ForeignKey( Tourney.id ) )
	teamA_id		= Column( Integer, ForeignKey( Team.id ) )
	teamB_id		= Column( Integer, ForeignKey( Team.id ) )
	prev_matchA_id	= Column( Integer, ForeignKey( 'matches.id' ), nullable=True )
	prev_matchB_id	= Column( Integer, ForeignKey( 'matches.id' ), nullable=True )
	
	teamA = relation('Team', primaryjoin= (teamA_id == Team.id) )
	teamB = relation('Team', primaryjoin= (teamB_id == Team.id) )
	
	prev_matchA = relation('Match', primaryjoin= (prev_matchA_id == id) )
	prev_matchB = relation('Match', primaryjoin= (prev_matchB_id == id) )
	
	#next_match = relation('Match', primaryjoin= or_(prev_matchB_id == id, prev_matchA_id == id) )
	def _next(self):
		return object_session(self).query(Match).filter( or_(Match.prev_matchB_id == self.id, Match.prev_matchA_id == self.id ) ).first()
	next = property(_next)
	
	def __init__(self,tourney):
		self.tourney_id 	= tourney.id
	
	def __str__(s):
		if s.prev_matchB_id:
			return 'Match: id - preA - preB: %d - %d - %d'%(s.id,s.prev_matchA_id,s.prev_matchB_id)
		elif s.teamA_id and s.teamB_id:
			return 'Match: id - T_A - T_B : %d - %d - %d'%(s.id,s.teamA_id,s.teamB_id)
		else:
			return 'Match: id - %d'%(s.id)
		
#mapper(Match, matches, properties={
    #'next_match': relation(Node, backref=backref('parent', remote_side=[nodes.c.id]))
#})

class DbConfig(Base):
	__tablename__	= 'config'
	dbrevision		= Column( Integer, primary_key=True )

	def __init__(self):
		self.dbrevision = 1

class ElementExistsException( Exception ):
	def __init__(self, element):
		self.element = element

	def __str__(self):
		return "Element %s already exists in db"%(self.element)

class ElementNotFoundException( Exception ):
	def __init__(self, element):
		self.element = element

	def __str__(self):
		return "Element %s not found in db"%(self.element)

class DbConnectionLostException( Exception ):
	def __init__( self, trace ):
		self.trace = trace
	def __str__(self):
		return "Database connection temporarily lost during query"
	def getTrace(self):
		return self.trace

class Backend:
	def Connect(self):
		self.engine = create_engine(self.alchemy_uri, echo=self.verbose, pool_size=20, pool_recycle=300)
		self.metadata = Base.metadata
		self.metadata.bind = self.engine
		self.metadata.create_all(self.engine)
		self.sessionmaker = sessionmaker( bind=self.engine )

	def __init__(self,alchemy_uri,verbose=False):
		global current_db_rev
		self.alchemy_uri = alchemy_uri
		self.verbose = verbose
		self.Connect()
		oldrev = self.GetDBRevision()
		self.UpdateDBScheme( oldrev, current_db_rev )
		self.SetDBRevision( current_db_rev )
		self.addDefaultData()

	def addDefaultData(self):
		session = self.sessionmaker()
		self.nullPlayer = Player(nick='nullPlayer')
		session.add( self.nullPlayer )
		self.nullTeam = Team( 'nullTeam' )
		self.nullTeam.players.append( self.nullPlayer )
		session.add( self.nullTeam )
		session.commit()
		players = []
		teams = []
		for i in range(254):
			players.append( Player(nick='dummy_%d'%i ) )
		session.add_all( players )
		session.commit()
		for i in range(6):
			t = Team(nick='Team_%d'%i )
			teams.append( t )
			for j in range(random.randint(1,7)):
				t.players.append( players[i*j] )
			session.add( t )
			session.commit()
			print t
		
		to = Tourney( self, teams, 'descr tourney' )
		session.close()
		
	def UpdateDBScheme( self, oldrev, current_db_rev ):
		pass

	def GetDBRevision(self):
		session = self.sessionmaker()
		rev = session.query( DbConfig.dbrevision ).order_by( DbConfig.dbrevision.desc() ).first()
		if not rev:
			#default value
			rev = -1
		else:
			rev = rev[0]
		session.close()
		return rev

	def SetDBRevision(self,rev):
		session = self.sessionmaker()
		conf = session.query( DbConfig ).first()
		if not conf:
			#default value
			conf = DbConfig()
		conf.dbrevision = rev
		session.add( conf )
		session.commit()
		session.close()
		
	def dbEncode (Self, string):
		try:
			return (string.encode('utf8'))
		except:
			return ('ufc error')
	