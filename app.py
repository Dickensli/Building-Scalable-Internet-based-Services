import sys,re
from urlparse import urlparse
from datetime import datetime
from random import randint
from flask import render_template,session,Flask,jsonify,request,redirect,send_from_directory,escape,url_for
from bs4 import BeautifulSoup
import json
import urllib2
import MySQLdb
import redis
from PIL import Image,ImageOps
import sendgrid
import os
from werkzeug.utils import secure_filename
from sendgrid.helpers.mail import *
import ast

from celery import Celery
def make_celery(app):
	celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
	celery.conf.update(app.config)
	TaskBase = celery.Task
	
	class ContextTask(TaskBase):
		abstract = True
		def __call__(self, *args, **kwargs):
			with app.app_context():
				return TaskBase.__call__(self, *args, **kwargs)
	celery.Task = ContextTask
	return celery

UPLOAD_FOLDER = '/home/ubuntu/static/images'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config.update(
	CELERY_BROKER_URL='amqp://guest@localhost',
	CELERY_RESULT_BACKEND='redis://localhost:6379'
)
celery = make_celery(app)

@celery.task()
def update_friend(username,friend_name):
	db = MySQLdb.connect('localhost','root','root','ierg4080')
	cursor = db.cursor()
	sql1 = 'SELECT id FROM login WHERE username = "%s"'%username
	cursor.execute(sql1)
	user_id = cursor.fetchone()
	user_id = str(user_id[0])

	sql2 = 'SELECT id FROM login WHERE username = "%s"'%friend_name
	cursor.execute(sql2)
	friend_id = cursor.fetchone()
	friend_id = str(friend_id[0])

	sql3 = 'INSERT INTO friends (user_id,friend_id) VALUES ("%s","%s")'%(user_id,friend_id)
	try:
		cursor.execute(sql3)
		db.commit()
	except:
		db.rollback()
	db.close()

@app.route('/app/friend_search',methods=['GET','POST'])
def friend_search():
 	if 'username' not in session:
                return redirect("http://54.186.189.42/html/index.html")
	
	username = session['username']
	flag = 0
	friend_name = '0'
	if request.method == 'POST':
		friend_name = request.form.get('friend_name',default = '')
		
		db = MySQLdb.connect('localhost','root','root','ierg4080')
		cursor = db.cursor()
		sql1 = 'SELECT username FROM login WHERE username = "%s"'%friend_name
		cursor.execute(sql1)
		friend_name = cursor.fetchone()
		if friend_name == None:
			flag = 1
		else:
			flag = 2
			friend_name = friend_name[0]
			update_friend.delay(username,friend_name)
	return render_template('pages-friend-search.html',flag=flag,friend_name=friend_name)	

@app.route('/app/friend_portfolio')
def show_friend_portfolio():
 	if 'username' not in session:
                return redirect("http://54.186.189.42/html/index.html")
	
	username = session['username']
	f = {}
	#return username
	
	db = MySQLdb.connect('localhost','root','root','ierg4080')
	cursor = db.cursor()
        sq2 = 'SELECT id FROM login WHERE username = "%s"'%username
        cursor.execute(sq2)
        user_id = cursor.fetchone()
        user_id = str(user_id[0])

	sq3 = 'SELECT friend_id FROM friends WHERE user_id = "%s"'%user_id
	cursor.execute(sq3)
	friends_id = cursor.fetchall()
	for f_id in friends_id:
		friend_id = str(f_id[0])
		cursor.execute('SELECT username FROM login WHERE id = "%s"'%friend_id) 
		friend_name = cursor.fetchone()
		friend_name = friend_name[0]
		f[friend_name] = {}	
	
	redis_db = redis.StrictRedis(host='localhost',port=6379,db=0)
	for friend_name in f:
		imgs = {}
		redis_data = redis_db.get(friend_name)
        	if (redis_data):
        		imgs = ast.literal_eval(redis_data)
		else:
			db = MySQLdb.connect('localhost','root','root','ierg4080')
			cursor = db.cursor()
                	sql1 = 'SELECT id FROM login WHERE username = "%s"'%friend_name
                	cursor.execute(sql1)
                	friend_id = cursor.fetchone()
                	friend_id = str(friend_id[0])
			sql2 = 'SELECT id,img_name,title,description FROM portfolio WHERE user_id = "%s" ORDER BY submited_at DESC'%friend_id
			cursor.execute(sql2)
			imgdatas = cursor.fetchall()
			db.close()
			
			for imgdata in imgdatas:
				img_id = imgdata[0]
				imgs[img_id] = {}
				imgs[img_id]['img_name'] = imgdata[1]
				imgs[img_id]['title'] = imgdata[2]
				imgs[img_id]['description'] = imgdata[3]
			#return jsonify(imgs)
		f[friend_name] = imgs
	return render_template('pages-friend-portfolio.html',f = f)


@app.route('/html/<path:fname>')
def static_html(fname):
	return send_from_directory('html/HTML',fname)

@app.route('/templates/<path:fname>')
def static_templates(fname):
	return send_from_directory('templates',fname)

@app.route('/home/ubuntu/static/<path:fname>')
def static_images(fname):
	return send_from_directory('static',fname)

@app.route('/')
def index():
	if 'username' in session:
		return redirect("http://54.186.189.42/app/portfolio")
	return redirect("http://54.186.189.42/html/index.html")

@app.route('/app/sign_up',methods=['GET','POST'])
def sign_up():
	if request.method == 'POST':
		username = request.form.get('username',default='')
		password = request.form.get('password',default='')
		firstname = request.form.get('firstname',default='')
		lastname = request.form.get('lastname',default='')
		confirm_password = request.form.get('confirm_password',default='')
	
		if confirm_password != password:
			return redirect("http://54.186.189.42/html/pages-re-sign-up.html")
		db = MySQLdb.connect('localhost','root','root','ierg4080')
		cursor = db.cursor()
		sql1 = 'SELECT username from login WHERE username = "%s"'%username
		cursor.execute(sql1)
		row = cursor.fetchone()
		if row != None:
			return redirect("http://54.186.189.42/html/pages-re-sign-up.html")	  
		
		sql2 = 'INSERT INTO login (username,password,firstname,lastname) VALUES ("%s","%s","%s","%s")'%(username,password,firstname,lastname)
		try:
			cursor.execute(sql2)
			db.commit()
		except:
			db.rollback()
        	db.close()
		
		return redirect("http://54.186.189.42/app/login")
	return redirect("http://54.186.189.42/html/pages-sign-up.html")	  

@app.route('/app/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form.get('username',default='')
		password = request.form.get('password',default='')
		db = MySQLdb.connect('localhost','root','root','ierg4080')
		cursor = db.cursor()
		sql1 = 'SELECT username FROM login WHERE (username,password) = ("%s","%s")'%(username,password)
		cursor.execute(sql1)
		row = cursor.fetchone()
		db.close()
		if row == None:
			return redirect("http://54.186.189.42/html/pages-re-login.html")

		session['username'] = username   	
		return redirect('http://54.186.189.42/')
	return redirect("http://54.186.189.42/html/pages-login.html")	  

@app.route('/app/logout')
def logout():
    	# remove the username from the session if it's there
    	session.pop('username', None)
    	return redirect('http://54.186.189.42/html/index.html')

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

@app.route('/app/portfolio')
def show_portfolio():
 	if 'username' not in session:
                return redirect("http://54.186.189.42/html/index.html")
	
	username = session['username']
	#return username
	imgs = {}
	redis_db = redis.StrictRedis(host='localhost',port=6379,db=0)
	redis_data = redis_db.get(username)
        if (redis_data):
        	imgs = ast.literal_eval(redis_data)
	else:
		db = MySQLdb.connect('localhost','root','root','ierg4080')
		cursor = db.cursor()
                sql1 = 'SELECT id FROM login WHERE username = "%s"'%session['username']
                cursor.execute(sql1)
                user_id = cursor.fetchone()
                user_id = str(user_id[0])
	
		if user_id == None:
                        return redirect("http://54.186.189.42/html/index.html")
		sql2 = 'SELECT id,img_name,title,description FROM portfolio WHERE user_id = "%s" ORDER BY submited_at DESC'%user_id
		cursor.execute(sql2)
		imgdatas = cursor.fetchall()
		db.close()

		for imgdata in imgdatas:
			img_id = imgdata[0]
			imgs[img_id] = {}
			imgs[img_id]['img_name'] = imgdata[1]
			imgs[img_id]['title'] = imgdata[2]
			imgs[img_id]['description'] = imgdata[3]
		#return jsonify(imgs)
	return render_template('pages-portfolio.html',imgs = imgs)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
		
@app.route('/app/upload', methods=['GET','POST'])
def upload():
 	if 'username' not in session:
                return redirect("http://54.186.189.42/html/index.html")
	
	username = session['username']
	if request.method == 'POST':
		fil = request.files['image']
		file_name = datetime.utcnow().strftime("%Y%m%d") + '-' + datetime.utcnow().strftime("%H%M%S") + '-' + str(randint(10000,99999)) + '.jpg'
		file_path = ' ' 
		if fil and allowed_file(fil.filename):
			file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
			fil.save(file_path)
		title = request.form.get('title',default='')
		description = request.form.get('description',default='')
		d = dict()
        	for key in re.sub(r'[^\w]', ' ', title).split():
            		key = key.lower()
            		if key in d:
                		d[key] += 1
            		else:
                		d[key] = 1
		
		db = MySQLdb.connect('localhost','root','root','ierg4080')
        	cursor = db.cursor()
		sql1 = 'SELECT id FROM login WHERE username = "%s"'%username
		cursor.execute(sql1)
		user_id = cursor.fetchone()
		user_id = str(user_id[0])
		if user_id == None:
			return  redirect("http://54.186.189.42/html/index.html")		
		
		sql2 = 'INSERT INTO portfolio (user_id,img_name,title,description,submited_at) VALUES ("%s","%s","%s","%s","%s")'%(user_id,file_path,title,description,datetime.now())
		try:
        	        cursor.execute(sql2)
        	        db.commit()
        	except:
        	        db.rollback()
			return  redirect("http://54.186.189.42/app/portfolio")		
        	        
		sql3 = 'SELECT id from portfolio where img_name = "%s"'%file_path
		cursor.execute(sql3)
		img_id = cursor.fetchone()
		img_id = str(img_id[0])
		try:
			for key in d:
				cursor.execute('INSERT INTO img_title_index (keyword,img_id,user_id) VALUES ("%s","%s","%s")'%(key, img_id,user_id))
			db.commit()
		except:
			db.rollback()
			return  redirect("http://54.186.189.42/app/portfolio")		
		
		sql4 = 'SELECT id,img_name,title,description FROM portfolio WHERE user_id = "%s" ORDER BY submited_at DESC'%user_id
        	cursor.execute(sql4)
        	imgdatas = cursor.fetchall()
		db.close()
			
		imgs = {}
        	for imgdata in imgdatas:
			img_id = str(imgdata[0])
        	        imgs[img_id] = {}
               		imgs[img_id]['img_name'] = imgdata[1]
                	imgs[img_id]['title'] = imgdata[2]
                	imgs[img_id]['description'] = imgdata[3]
		#return jsonify(imgs)
		redis_db = redis.StrictRedis(host='localhost',port=6379,db=0)
		redis_db.set(username,imgs)
		return  redirect("http://54.186.189.42/app/portfolio")		
	return redirect("http://54.186.189.42/html/pages-upload.html")

@app.route('/app/search', methods=['GET','POST'])
def search():
 	if 'username' not in session:
                return redirect("http://54.186.189.42/html/index.html")
	
	username = session['username']
	di = list()
	if request.method == 'POST':
		keyword = request.form.get('keyword',default='').lower()
		record = dict()
		
		db = MySQLdb.connect('localhost','root','root','ierg4080')
		cursor = db.cursor()
		sql1 = 'SELECT id FROM login WHERE username = "%s"'%session['username']
		cursor.execute(sql1)
		user_id = cursor.fetchone()
		user_id = str(user_id[0])
		if user_id == None:
			return redirect("http://54.186.189.42/html/index.html")
		
		sql2 = 'SELECT keyword FROM img_title_index WHERE user_id = "%s"'%user_id
		cursor.execute(sql2)
		data = cursor.fetchall()
		for row in data:
			if row[0] == keyword:
				if keyword in record:
       		    			record[keyword] += 1
				else:
       		    			record[keyword] = 1
		#return jsonify(record)	
		for re in record:
			cursor.execute('SELECT portfolio.img_name, portfolio.title, portfolio.description FROM portfolio,img_title_index WHERE img_title_index.keyword = "%s" AND img_title_index.img_id = portfolio.id AND img_title_index.user_id = "%s"'%(re,user_id))
		data2 = cursor.fetchall()
		for row2 in data2:
			di.append({'img_name':row2[0],'title':row2[1],'description':row2[2]})
	return render_template('pages-search.html',di = di)

@app.route('/app/delete',methods=['GET','POST'])
def delete():
 	if 'username' not in session:
                return redirect("http://54.186.189.42/html/index.html")
	
	if request.method == 'GET':
		username = session['username']
		file_path = request.args.get('img',default='')
		
		db = MySQLdb.connect('localhost','root','root','ierg4080')
        	cursor = db.cursor()
		sql1 = 'SELECT id FROM login WHERE username = "%s"'%session['username']
		cursor.execute(sql1)
		user_id = cursor.fetchone()
		user_id = str(user_id[0])
		if user_id == None:
			return redirect("http://54.186.189.42/html/index.html")
				
        	sql2 = 'SELECT id FROM portfolio WHERE img_name = "%s"'%file_path
		cursor.execute(sql2)
		img_id = cursor.fetchone()
        	img_id = str(img_id[0])
		
		sql3 = 'DELETE FROM portfolio WHERE img_name = "%s"'%file_path
		try:
        		cursor.execute(sql3)
                	db.commit()
        	except:
                	db.rollback()
			return redirect("http://54.186.189.42/app/portfolio")
        
		sql4 = 'DELETE FROM img_title_index WHERE img_id = "%s"'%img_id
		try:
        		cursor.execute(sql4)
                	db.commit()
       		except:
                	db.rollback()
			return redirect("http://54.186.189.42/app/portfolio")
		
		if os.path.exists(file_path):
			os.remove(file_path)	
		
		sql5 = 'SELECT id,img_name,title,description FROM portfolio WHERE user_id = "%s" ORDER BY submited_at DESC'%user_id
        	cursor.execute(sql5)
        	imgdatas = cursor.fetchall()
		db.close()
		
		imgs = {}
        	for imgdata in imgdatas:
                	img_id = str(imgdata[0])
                	imgs[img_id] = {}
                	imgs[img_id]['img_name'] = imgdata[1]
                	imgs[img_id]['title'] = imgdata[2]
                	imgs[img_id]['description'] = imgdata[3]
		#return jsonify(imgs)
		redis_db = redis.StrictRedis(host='localhost',port=6379,db=0)
		redis_data = redis_db.get(username)
        	if (redis_data):
			redis_db.delete(username)
		redis_db.set(username,imgs)
	return  redirect("http://54.186.189.42/app/portfolio")		

@app.route('/app/delete_friend',methods=['POST','GET'])
def delete_friend():
 	if 'username' not in session:
                return redirect("http://54.186.189.42/html/index.html")

	username = session['username']
	if request.method == 'POST':
		friend_name = request.args.get('friend_name',default = '')
		
		db = MySQLdb.connect('localhost','root','root','ierg4080')
		cursor = db.cursor()
		sql1 = 'SELECT id FROM login WHERE username = "%s"'%username
		cursor.execute(sql1)
		user_id = cursor.fetchone()
		user_id = str(user_id[0])
		
		sql3 = 'SELECT id FROM login WHERE username = "%s"'%friend_name
		cursor.execute(sql3)
		friend_id = cursor.fetchone()
		friend_id = str(friend_id[0])
		
		sql3 = 'DELETE FROM friends WHERE user_id = "%s" AND friend_id = "%s"'%(user_id,friend_id)
		try:
			cursor.execute(sql3)
			db.commit()
		except:
			db.rollback()
	return redirect("http://54.186.189.42/app/friend_portfolio")

if __name__ == '__main__':
	app.run(host='0.0.0.0')
