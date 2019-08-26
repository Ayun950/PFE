#!/usr/bin/env bash

mysql -u user -ppassword freeradius <<EOF
INSERT INTO radcheck (username,attribute,op,value) VALUES ('PFE_Spoke2','Cleartext-Password',':=','cisco');
INSERT INTO radusergroup (username,groupname,priority) VALUES ('PFE_Spoke2','ipsec',1);
INSERT INTO radreply (username, attribute,op,value) VALUES ('PFE_Spoke2','Cisco-AVPair','+=','ipsec:ikev2-password-remote=CleSpoke');
INSERT INTO userinfo (username,creationdate,creationby) VALUES ('PFE_Spoke2',CURDATE(),'administrator')
EOF
