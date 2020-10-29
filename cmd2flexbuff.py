#!/usr/bin/python
#
# Python script to send individual commands to FILA10G & return result to FS log
#


import os
import sys
import socket

# Infos
def usage_exit():
	print 'Usage: stopfila10g.py [-u|--udp] <ip_address> <ip_port>'
	sys.exit(-1)

# Return a socket:  conn=(ip,port,use_tcp)
def getSocket(conn):
	try:
		if conn['isTCP']:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((conn['ip'],conn['port']))
		else:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.settimeout(1.0)
		conn['socket'] = s
	except:
		print 'Connection to %s:%u failed' % (conn['ip'],conn['port'])
		return None
	return conn

# Send a command, wait for reply
def sendRcv(conn,cmdstr):
	buffer_size = 2048
	cmdstr = '\n' + cmdstr.strip() + '\n'
	if conn['isTCP']:
		conn['socket'].send(cmdstr)
	else:
		conn['socket'].sendto(cmdstr, (conn['ip'],conn['port']))
	reply = ''
	try:
		while True:
			data = conn['socket'].recv(buffer_size)
			reply = reply + data
	except:
		return reply


# Prepare and send commands to FILA10G
def main(argv):
	global _cmds
        IP = os.environ['FLEXIP']
        PORT = int(os.environ['FLEXPORT'])
	conn_TCP = True
	conn_IPaddr = IP
	conn_IPport = PORT

	conn = {'ip':conn_IPaddr, 'port':conn_IPport, 'isTCP':conn_TCP, 'socket':None}
	conn = getSocket(conn)
	if (conn==None):
	        os.system("inject_snap \'\"Error opening connection to flexbuff\'")
		sys.exit(-1)

        # First stop sending data
	# Append data source command(s)
	reply=sendRcv(conn, " ".join(argv[1:]) + '\r\n')
	lines=reply.strip('\r\n').splitlines()
	for line in lines:
		print "Flexbuff: "+line
#	reply.strip('\r\n')
#        os.system("inject_snap \'\"command sent\'")
	sys.exit(0)	

if __name__ == "__main__":
    main(sys.argv)

