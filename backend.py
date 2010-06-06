# -*- coding: utf-8 -*-
from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *
import datetime, os, math,random, pydot

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

class JSONnode(object):
	def __init__(s,root_match,matches):
		print root_match
		s.id		= 'Match #%d'%root_match.id
		s.name		= s.id
		s.data		= MatchData(root_match)
		s.children	= []
		
		if root_match.prev_matchA_id:
			m = matches[root_match.prev_matchA_id]
			s.children.append( JSONnode( m, matches ) )
		if root_match.prev_matchB_id:
			m = matches[root_match.prev_matchB_id]
			s.children.append( JSONnode( m, matches ) )
		
		
class MatchData(object):
	def __init__(self,match):
		self.lineA = '%s | %d'%(match.teamA.nick,match.scoreA) if match.teamA_id else 'Winner match %d'%match.prev_matchA_id
		self.lineB = '%s | %d'%(match.teamB.nick,match.scoreB) if match.teamB_id else 'Winner match %d'%match.prev_matchB_id
		self.id = match.id
		self.prevA = match.prev_matchA_id
		self.prevB = match.prev_matchB_id
		if match.teamA_id:
			self.html = '''<div class="node"><table>
				<tr>
					<td class="node-left-col">%s</td>
					<td align="right" class="node-right-col">%d</td>
				</tr>
				<tr>
					<td class="node-left-col">%s</td>
					<td align="right" class="node-right-col">%d</td>
				</tr>			
			</table></div>'''%(match.teamA.nick,match.scoreA,match.teamB.nick,match.scoreB )
		else:
			self.html = '''<div class="node"><table>
				<tr>
					<td>%s</td>
				</tr>
				<tr>
					<td>%s</td>
				</tr>			
			</table></div>'''%(self.lineA,self.lineB)
		
	
class Tourney(Base):
	__tablename__ 	= 'tourneys'
	id 				= Column( Integer, primary_key=True )
	description		= Column( Text )

	def build(self,db,teams_,description):
		session = db.sessionmaker()
		self.teams = teams_
		random.shuffle(self.teams)
		self.description = description
		actual_team_num = len(teams_)
		padded_team_num = int( math.pow( 2, math.ceil( math.log( actual_team_num, 2 ) )  ) )
		print 'got %d teams, padded to %d teams'%(actual_team_num,padded_team_num)
		for i in range( actual_team_num, padded_team_num ):
			self.teams.append( db.nullTeam )
		rounds = int( math.log( padded_team_num, 2 ) + 1 )
		print 'doing %d rounds'%rounds
		
		matches = []
		#first round
		for i in range( int(padded_team_num / 2 ) ):
			m = Match(self)
			m.tourney_id = self.id
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
				m.tourney_id = self.id
				m.prev_matchA_id = matches[2*i].id
				m.prev_matchB_id = matches[2*i+1].id
				next_matches.append( m )
			session.add_all( next_matches )
			session.commit()
			matches = next_matches #next round consists of  pairs of this round's matches
		session.close()
		self.saveJSONdata()
				
	def generateGraph(self, fn ):
		graph = pydot.Dot(graph_type='digraph')
		nodes = dict()
		match_q = object_session(self).query( Match ).filter( Match.tourney_id == self.id )
		for m in match_q:
			if m.teamA_id:
				n = pydot.Node( 'Match %d'%m.id,label='"Match %d:\\n%s vs\\n %s"'%(m.id,m.teamA.nick,m.teamB.nick), shape="box" )
			else:
				n = pydot.Node( 'Match %d'%m.id,label='"Match %d:\\n Winner Match %d\\n vs  Winner Match %d"'%(m.id,m.prev_matchA_id,m.prev_matchB_id), shape='box' )
			nodes[m.id] = n
			graph.add_node( n )

		for m in match_q:
			if m.next:
				e = pydot.Edge( nodes[m.id], nodes[m.next.id] )
				graph.add_edge( e )
		graph.write_png( fn )
	
	def saveJSONdata(self):
		matches = dict()
		match_q = object_session(self).query( Match ).filter( Match.tourney_id == self.id )
		for m in match_q:
			matches[m.id] = m
			if not m.next:
				final = m
		#print final
		tree = JSONnode( final, matches )
		import jsonpickle
		jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
		with open('tourneys/%s.js'%self.id,'w') as tourney_js:
			tourney_js.write( 'var tree = %s;\n' % jsonpickle.encode( tree , unpicklable=False ) )
			#tourney_js.write( 'var edges = %s;\n' % jsonpickle.encode( edges , unpicklable=False ) )
			tourney_js.write( 'var final_id = %s;\n' % jsonpickle.encode( final.id , unpicklable=False ) )
	
	
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
	scoreA			= Column( Integer, default=0 )
	scoreB			= Column( Integer, default=0 )
	
	teamA = relation('Team', primaryjoin= (teamA_id == Team.id) )
	teamB = relation('Team', primaryjoin= (teamB_id == Team.id) )
	
	prev_matchA = relation('Match', primaryjoin= (prev_matchA_id == id) )
	prev_matchB = relation('Match', primaryjoin= (prev_matchB_id == id) )
	
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
		for i in range(2054):
			players.append( Player(nick='dummy_%d'%i ) )
		session.add_all( players )
		session.commit()
		for i in range(80):
			t = Team(nick='Team_%d'%i )
			teams.append( t )
			for j in range(random.randint(1,7)):
				t.players.append( players[i*j] )
			session.add( t )
			session.commit()
		
		to = Tourney()
		session.add( to )
		session.commit()
		to.build( self, teams[0:7], 'descr tourney' )
		to2 = Tourney()
		session.add( to2 )
		session.commit()
		to2.build( self, teams[7:32], 'descr tourney' )
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
	