#!/usr/bin/python
import sys
import getopt
import ldap
import re

issueFound = False

def Usage(name):
    print "Usage: " + name + '''
    -h hostname [default: 127.0.0.1]
    -p port [default: 11711]
    -u userDN [default: CN=administrator,CN=users,DC=vsphere,DC=local]
    -w password [default: ""]
    NOTE: password is not checked unless you want to remove problem members.'''

def GetServicePrincipals(ld):
    baseDN = 'CN=ServicePrincipals,DC=vsphere,DC=local'
    searchScope = ldap.SCOPE_SUBTREE
    retrieveAttributes = None 
    searchFilter = "CN=*"

    try:
        ldap_result_id = ld.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        SPs = []
        while 1:
            result_type, result_data = ld.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    SPs.append(result_data[0][0])
    except ldap.LDAPError, e:
        print 'GetServicePrincipals failed:' + str(e)
    return SPs	

def GetBuiltinUsers(ld):
    baseDN = 'CN=Builtin,DC=vsphere,DC=local'
    searchScope = ldap.SCOPE_SUBTREE
    retrieveAttributes = None 
    searchFilter = "CN=*"

    try:
        ldap_result_id = ld.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        BUs = []
        while 1:
            result_type, result_data = ld.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    BUs.append(result_data[0][0])
    except ldap.LDAPError, e:
        print 'GetBuiltinUsers failed:' + str(e)
    return BUs	

def GetAttributes(ld, baseDN):
    searchScope = ldap.SCOPE_SUBTREE
    retrieveAttributes = None 
    searchFilter = "CN=*"

    try:
        ldap_result_id = ld.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        bu_attr = []
        while 1:
            result_type, result_data = ld.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    #print result_data[0][1]
                    bu_attr.append(result_data[0][1])
    except ldap.LDAPError, e:
        print 'GetBuiltInUserAttributes failed:' + str(e)
    return bu_attr

def GetAllReplicationServers(ld):
    baseDN = 'CN=Configuration,DC=vsphere,DC=local'
    searchScope = ldap.SCOPE_SUBTREE
    retrieveAttributes = None 
    searchFilter = "cn=Replication Agreements"
    Servers = []
    try:
        ldap_result_id = ld.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        Conf = []
        while 1:
            result_type, result_data = ld.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    Conf.append(result_data[0][0])
    except ldap.LDAPError, e:
        print 'GetAllReplicationServers failed:' + str(e)
    for member in Conf:
       member = member.split(",")[1].split("=")[1]
       Servers.append(member)
    return list(set(Servers))

def ServicePrincipalsFilter(string):
    if re.search('CN=ServicePrincipals', string, re.IGNORECASE) > 0:
        return True
    else:
        return False
 
def GetMembers(ld, baseDN, spFilter):
    searchScope = ldap.SCOPE_BASE
    retrieveAttributes = ['member']
    searchFilter = "CN=*"
    try:
        ldap_result_id = ld.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        while 1:
            result_type, result_data = ld.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    try:
                        return filter(spFilter, result_data[0][1]['member'])
                    except KeyError:
                        print "GetMembers " + baseDN + " has no member."
                        return []
    except ldap.LDAPError, e:
        print ("GetMembers(%s) failed: %s" % baseDN, str(e))

def CheckConsistent(refFrom, refTo):
    invalidRefs = []
    for ref in refFrom:
        if ref in refTo:
            continue
        invalidRefs.append(ref)
    return invalidRefs
    
def diff_serviceprincipal_across_nodes(Servers,port,username,password):
   bu_attr_list = {}
   for server in Servers:
      bu_attr_list[server] = []
      l = ConnectLdap(server,port,username,password)
      servicePrincipals = GetServicePrincipals(l)
      servicePrincipals.pop(0)
      for s in servicePrincipals:
         attr = GetAttributes(l, s)
         bu_attr_list[server].append(attr)
   for i in range(len(Servers)):
      for j in range(len( bu_attr_list[Servers[i]])):
         if i == (len(Servers)-1):
            break
         for k,v in bu_attr_list[Servers[i]][j][0].iteritems():
            bu_attr_list[Servers[i]][j][0][k].sort()
         for k,v in bu_attr_list[Servers[i+1]][j][0].iteritems():
            bu_attr_list[Servers[i+1]][j][0][k].sort()
         result = cmp(bu_attr_list[Servers[i]][j][0], bu_attr_list[Servers[i+1]][j][0])
         #print "\n Comparing:"   + Servers[i] + " and  " + Servers[i+1]
         if result != 0:
            print "\n Issues found while comparing:"   + Servers[i] + " and  " + Servers[i+1]
            print "\n Result :-" 
            print result  
            print bu_attr_list[Servers[i]][j][0]
            print "\n"
            print bu_attr_list[Servers[i+1]][j][0]
   return []

def diff_builtinusers_across_nodes(Servers,port,username,password):
   bu_attr_list = {}
   for server in Servers:
      bu_attr_list[server] = []
      l = ConnectLdap(server,port,username,password)
      bu = GetBuiltinUsers(l)
      bu.pop(0)
      for s in bu:
         attr = GetAttributes(l, s)
         bu_attr_list[server].append(attr)
   for i in range(len(Servers)):
      for j in range(len( bu_attr_list[Servers[i]])):
         if i == (len(Servers)-1):
            break
         for k,v in bu_attr_list[Servers[i]][j][0].iteritems():
            bu_attr_list[Servers[i]][j][0][k].sort()
         for k,v in bu_attr_list[Servers[i+1]][j][0].iteritems():
            bu_attr_list[Servers[i+1]][j][0][k].sort()
         result = cmp(bu_attr_list[Servers[i]][j][0], bu_attr_list[Servers[i+1]][j][0])
         if result != 0:
            print "\n Issues found while comparing:"   + Servers[i] + " and  " + Servers[i+1]
            print "\n Result :-" 
            print result  
            print bu_attr_list[Servers[i]][j][0]
            print "\n"
            print bu_attr_list[Servers[i+1]][j][0]
   return []

def DeleteMembers(ld, dn, members):
    try:
        modlist = []
        for m in members:
            modlist.append((ldap.MOD_DELETE, "member", m))
        print " -- removing " + str(modlist)
        ld.modify_s(dn, modlist)
        print "Removed."
    except ldap.LDAPError, e:
        print "DeleteMembers failed: " + str(e)

def CheckAndFix(ld, checkDN, sps):
    global issueFound 
    issueFound = False
    solutionUsersMemebers = GetMembers(ld, checkDN, ServicePrincipalsFilter)
    if (len(solutionUsersMemebers) == 0):
       print "\n No Solution User Members Found !!!"
       issueFound = True
       return True 
    return 
    invalidRefs = CheckConsistent(solutionUsersMemebers, sps)
    if invalidRefs:
        issueFound = True
        print ("\"%s\" has following members which are referencing non-existing SolutionUsers:") % checkDN
        print invalidRefs
        answer = raw_input("Do you want to remove them (better backup before removing)? yes/no: [no]")
        if answer.lower() == "yes":
            DeleteMembers(ld, checkDN, invalidRefs)
			
def ConnectLdap (hostname, port, username, password):
    try:
        l = ldap.open(hostname, int(port))
        l.protocol_version = ldap.VERSION3
        l.simple_bind(username, password)
    except ldap.LDAPError, e:
        print 'ldap open failed:' + str(e)
    print "Connected to Ldap Server " + hostname + " at port " + port + " Successfully !!! \n"
    return l

def main():
    hostname = '127.0.0.1'
    port = '11711'
    username = 'CN=administrator,CN=users,DC=vsphere,DC=local'
    password = ""
    issues_found = {}
    try:
        opts, args = getopt.getopt(sys.argv[1:],"h:p:u:w:",["hostname=","port=", "userDN=", "password="])
    except getopt.GetoptError:
        Usage(sys.argv[0])
        sys.exit(2)

    if not opts:
        Usage(sys.argv[0])
        sys.exit()

    for opt, arg in opts:
      if opt in ("-h", "--hostname"):
        hostname = arg
      elif opt in ("-p", "--port"):
        port = arg
      elif opt in ("-u", "--userDN"):
        username = arg
      elif opt in ("-w", "--password"):
        password = arg
      else:
        Usage(sys.argv[0])
        sys.exit()
    l = ConnectLdap(hostname,port,username,password)
    Servers = GetAllReplicationServers(l) 
    diff_serviceprincipal_across_nodes(Servers,port,username,password)
    diff_builtinusers_across_nodes(Servers,port,username,password)

    for server in Servers:
       l = ConnectLdap(server,port,username,password)
       servicePrincipals = GetServicePrincipals(l)
       CheckAndFix(l, "CN=SolutionUsers,DC=vsphere,DC=local", servicePrincipals)
       CheckAndFix(l, "CN=Users,CN=Builtin,DC=vsphere,DC=local", servicePrincipals)
       CheckAndFix(l, "CN=Administrators,CN=Builtin,DC=vsphere,DC=local", servicePrincipals)
       l.unbind()
       issues_found[server] = issueFound
 
    for k,v in issues_found.iteritems():
       print "\n Server: %s  Issue Found: %r" % (k, v)
	   
if __name__ == "__main__":
    main()