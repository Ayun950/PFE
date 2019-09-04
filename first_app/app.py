from flask import Flask, request, make_response, render_template
from flask_mysqldb import MySQL
from PIL import Image
from StringIO import StringIO
from datetime import datetime
import re
import os

app = Flask('__name__')

app.config['MYSQL_HOST'] = '10.112.83.118'
app.config['MYSQL_USER'] = 'user'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'freeradius'

mysql = MySQL(app)

@app.route("/")
def accueil():
   return render_template('accueil.html', titre="Bienvenue !")

@app.route("/ajout")
def ajout():
   return render_template('ajout.html', titre="Ajout")

@app.route("/rendu",methods = ['POST', 'GET'])
def rendu():
   if request.method == 'POST':
      rendu = request.form
      tenant= rendu['tenant']
      name = rendu['name']
      password = rendu['password']
      int_address=rendu['int_address']
      int_name=rendu['int_name']
      int_description=rendu['int_description']
      int_mask=rendu['int_mask']
      address_admin=rendu['address_admin']

# Generation de la configuration de l'interface LAN du nouvel equipement

      new_file_int_LAN = "/home/ark/Ansible/roles/InitLan/vars/host_vars/"+name+".yml"
      with open(new_file_int_LAN,'a+') as nf:
        nf.write("---\n")
        nf.write("interfaces:\n") 
        nf.write("   "+"- name: "+int_name+"\n") 
        nf.write("     "+"address:"+" "+int_address+"\n") 
        nf.write("     "+"mask:"+" "+int_mask+"\n") 
        nf.write("     "+"description:"+" "+int_description+"\n") 
        nf.close()

#Creation du fichier de configuration de l'interface LAN
        cmd="ansible-playbook /home/ark/Ansible/InitLan.yml -e hostname="+name+" -vvvv"
        retval=os.system(cmd)
        print(retval)

# Modification du fichier inventory pour Ansible
# Ajout d'une ligne correspondant au nouvel equipement

      inv_line = name+" ansible_host="+address_admin
      regex = re.compile(r'^\[Spokes]$')
      try:
         f = open("/home/ark/Ansible/inventory",'r')
         f.close()
      except IOError:
         print("File inventory not available")
	
      try:
         f2 = open('/home/ark/Ansible/inventory_dump','r')
         f2.close()
         os.remove("/home/ark/Ansible/inventory_dump")
      except IOError:
         print("Work in progress")

      with open("/home/ark/Ansible/inventory",'r') as fr:
         ch = fr.readlines()
         for line in ch:
            with open("/home/ark/Ansible/inventory_dump",'a+') as file2:
               result = regex.search(line)
               file2.write(line)
               if result:
                  file2.write(inv_line+"\n")

      os.remove("/home/ark/Ansible/inventory")
      os.rename("/home/ark/Ansible/inventory_dump", "/home/ark/Ansible/inventory")

# Via ansible configuration eem sur l'equipement distant 
      cmd="ansible-playbook -i /home/ark/Ansible/inventory -e target="+name+" /home/ark/Ansible/EEM.yml -c local -vvvv" 
      retval=os.system(cmd)
      print(retval)

# Ajout du nouvel equipement dans la base de donnees du serveur Radius

      key = 'ipsec:ikev2-password-remote='+rendu['key']
      cmd="ansible-playbook /home/ark/Ansible/AjoutSQL.yml -i /home/ark/Ansible/inventory  -e name="+name+" -e key="+key+" -e password="+password+" -e d=CURDATE\(\) -e local_route="+rendu['local_route']+" -e int_mask="+int_mask+" -vvvv"
      retval=os.system(cmd)
      print(retval)
      return render_template("rendu.html", rendu = rendu)

@app.route("/liste")
def liste():
   cur = mysql.connection.cursor()
   cur.execute("SELECT id,username FROM userinfo")
   users = cur.fetchall()
   cur.close()
   return render_template('liste.html', titre="Liste", users = users)

@app.route("/supp_user", methods =['POST','GET'])
def supp_user():
   if request.method == 'POST':
      rendu = request.form
      username = rendu['username']
      cur =mysql.connection.cursor()
      sql_Delete_query = """Delete from radusergroup where radusergroup.username = %s"""
      cur.execute(sql_Delete_query,(username,))
      print("Delete from radusergroup successfully.")
      sql_radcheck_del = """Delete from radcheck where radcheck.username = %s"""
      cur.execute(sql_radcheck_del,(username,))
      print("Delete from radcheck successfully.")
      sql_radreply_del = """Delete from radreply where radreply.username = %s"""
      cur.execute(sql_radreply_del,(username,))
      print("Delete from radreply successfully.")
      sql_userinfo_del = """Delete from userinfo where userinfo.username = %s"""
      cur.execute(sql_userinfo_del,(username,))
      print("Delete from userinfo successfully.")
      mysql.connection.commit()
      cur.close()

      #reset des interfaces gi3 tu100 et tu200  l'equipement via ansible
      cmd="ansible "+username+" -i /home/ark/Ansible/inventory -m ios_config -a \"src=/home/ark/Ansible/supprCE.yml\" -c local -vvvv"
      retval=os.system(cmd)
      print(retval)

      #suppression de la ligne concernee dans l'inventaire Ansible
      cmd="sed -i -e '/^"+username+"/ d' /home/ark/Ansible/inventory"
      retval=os.system(cmd)
      print(retval)
      
      #supression de tout les fichiers de variables concernant l'equipement a supprimer
      cmd="rm /home/ark/Ansible/roles/InitLan/vars/host_vars/*"+username+"*"
      retval=os.system(cmd)
      print(retval)

      #suppression du fichier de configuration configs/
      cmd="rm -f /home/ark/configs/*"+username+"*"
      retval=os.system(cmd)
      print(retval)

      #suppression du fichier de script sql
      cmd="rm -f /home/ark/Ansible/roles/CreateFile/vars/"+username+"*"
      retval=os.system(cmd)
      print(retval)

      return render_template('supp_user.html', titre="Supprimer un equipement", rendu=rendu)

@app.route("/modification", methods =['POST','GET'])
def modif():
      return render_template('modification.html', titre="Modification")


@app.route("/modification_choix", methods =['POST','GET'])
def modif_choix():
   if request.method == 'POST':
      rendu = request.form
      name= rendu['name']
      cmd="ansible-playbook /home/ark/Ansible/BackupConf.yml -i /home/ark/Ansible/inventory --limit="+name+" -e hostname="+name+" -vvvv"
      retval=os.system(cmd)
      return render_template('modification_choix.html', titre="Modification", rendu=rendu, name=name, check_values=check_values)

@app.route("/modification_filter", methods=['POST','GET'])
def modif_filter():
   if request.method == 'POST':
      rendu = request.form
      print(rendu)
   return render_template('modification_filter.html', rendu=rendu)
 
if __name__ == '__main__':
   app.debug = True
   app.run()

