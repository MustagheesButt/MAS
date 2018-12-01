from flask import Flask, flash, redirect, request, render_template, session, url_for, abort, jsonify
from flask_session import Session
from tempfile import mkdtemp
from passlib.apps import custom_app_context as pwd_context
from datetime import datetime
import pathlib

from cs50 import SQL

from helpers import *
from constants import *

from api import *

app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
	@app.after_request
	def after_request(response):
		response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
		response.headers["Expires"] = 0
		response.headers["Pragma"] = "no-cache"
		return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# connect to MyAcademiaStudio database
db = SQL("mysql://" + DB_USERNAME + ":" + DB_PASSWORD + "@" + DB_SERVER + "/" + DB_DATABASE_MAS)

# Register Filters
app.jinja_env.filters["gender"] = gender

@app.route("/")
def index():
	return render_template("home.html")

@app.route("/receive_access_token", methods=['GET'])
def receive_access_token():
	return render_template("receive_access_token.html",
		access_token = request.args.get('access_token'),
		callback_status = request.args.get('callback')
		)

# either login or register
@app.route("/auth", methods=['POST'])
def auth():
	# forget any user_id
	session.clear()

	# validation
	if not request.form["username"]:
		return jsonify({"status": "error", "error": "Please provide a username"})
	if not request.form["id"]:
		return jsonify({"status": "error", "error": "Please provide a user id"})
	
	rows = db.execute("SELECT * FROM `accounts.users` WHERE `user_id` = :user_id", user_id = request.form["id"])

	# login
	if len(rows) > 0:
		# ensure username exists and password is correct
		if len(rows) != 1:
			return jsonify({"status": "error", "error": "Non-unique user_id passed."})

		# remember which user has logged in
		session["user_id"] = rows[0]["user_id"]
		session["full_name"] = rows[0]["full_name"]

		flash("You have been logged in! :)")
	# register
	else:
		# validate and hash password
		user_id = db.execute(
			# TODO: update schema
				"INSERT INTO `accounts.users` (user_id, email, full_name, profile_pic, registered_on) VALUES (:user_id, :email, :full_name, :profile_pic, :registered_on)",
					user_id = request.form["id"],
					email = request.form["email"],
					full_name = request.form["first_name"] + " " + request.form["last_name"],
					profile_pic = "\0",
					registered_on = str( datetime.now().strftime("%Y-%m-%d") )
				)

		session["user_id"] = user_id

		row = db.execute("SELECT `full_name` FROM `accounts.users` WHERE `user_id` = :user_id", user_id = user_id)[0]

		session["full_name"] = row["full_name"]

		# send an email
		#envelope = Envelope(
			# to_addr   = new_user['email'],
			# subject   = api.config['WELCOME_EMAIL_SUBJECT'],
			# text_body = render_template('emails/new_user.txt'),
			# html_body = render_template('emails/new_user.html'))
		# def sender():
		# 	envelopes.connstack.push_connection(conn)
		# 	smtp = envelopes.connstack.get_current_connection()
		# 	smtp.send(envelope)
		# 	envelopes.connstack.pop_connection()
		# gevent.spawn(sender)
		
		flash("You have been registered successfully! :)")

	next = request.form.get('next')
	# is_safe_url should check if the url is safe for redirects.
	# See http://flask.pocoo.org/snippets/62/ for an example.
	if not is_safe_url(next):
		return jsonify({"status": "error", "error": "`next` URL not safe"})

	# redirect user where they came from or to home page
	return jsonify({"status": "success", "redirect_to": next or url_for("dashboard")})

@app.route("/logout")
def logout():
	"""Log user out."""

	# forget any user_id etc
	session.clear()

	# redirect user to login form
	return redirect(url_for("index"))
		

@app.route("/dashboard")
@login_required
def dashboard():
	user_orgs = db.execute("SELECT * FROM `organizations` WHERE `owner_id` = :owner", owner = session["user_id"])
	return render_template("dashboard/dashboard_default.html", user_orgs = user_orgs)

@app.route("/dashboard/new_organization", methods=['POST', 'GET'])
@login_required
def dashboard_new_organization():
	if request.method == "POST":
		
		# validation
		if not request.form["handle"]:
			return apology("Please provide a handle")
		elif not request.form["title"]:
			return apology("Please provide an organization title")
		elif not request.form["phone"] or not request.form["email"] or not request.form["address"] or not request.form["city"] or not request.form["country"]:
			return apology("Please fill the form correctly", "Some required fields were missing")

		# TODO: correctly verify all above rushed fields

		# register new organization
		db.execute("INSERT INTO `organizations` (owner_id, handle, title, type, email, phone, address, city, country) VALUES (:owner_id, :handle, :title, :type, :email, :phone, :address, :city, :country)",
			owner_id = session["user_id"],
			handle = request.form["handle"],
			title = request.form["title"],
			type = request.form["type"],
			email = request.form["email"],
			phone = request.form["phone"],
			address = request.form["address"],
			city = request.form["city"],
			country = request.form["country"]
		)

		# make its folder
		pathlib.Path('organizations/{0}/'.format(request.form['handle'])).mkdir(parents=True, exist_ok=True)

		# Create required database tables
		# ORGANIZATION CONTACTS - for storing all phone numbers of students, parents, staff etc
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_contacts`
			(
			`id` BIGINT(20) unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`contact_type` VARCHAR(5) NOT NULL, # staff = STAFF, parents/guardians = PARNT, students = STDNT
			`contact_id` BIGINT(20) unsigned NOT NULL,
			`number` TEXT, # phone or mobile number
			UNIQUE KEY `unique_contact` (`contact_id`, `contact_type`, `number`)
			) DEFAULT CHARSET = utf8mb4
		""".format(request.form['handle']))

		# SUBJECTS
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_subjects`
			(
			`id` INT unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`name` TEXT NOT NULL
			) DEFAULT CHARSET = utf8mb4
		""".format(request.form['handle']))

		# CLASSES
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_classes`
			(
			`id` INT unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`name` VARCHAR(100) NOT NULL UNIQUE,
			`start_date` DATE,
			`end_date` DATE,
			`fee` INT NOT NULL,
			`timing_start` TIME,
			`timing_end` TIME
			) DEFAULT CHARSET = utf8mb4
		""".format(request.form['handle']))

		# CLASS_SUBJECTS
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_class_subjects`
			(
			`class_id` INT unsigned NOT NULL,
			`subject_id` INT unsigned NOT NULL,
			FOREIGN KEY `class_id__class_subjects` (`class_id`) REFERENCES {0}_classes(`id`),
			FOREIGN KEY `subject_id__class_subjects` (`subject_id`) REFERENCES {0}_subjects(`id`)
			) DEFAULT CHARSET = utf8mb4
		""".format(request.form['handle']))

		# STUDENTS
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_students`
			(
			`id` BIGINT(20) unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`first_name` TEXT NOT NULL,
			`middle_name` TEXT,
			`last_name` TEXT NOT NULL,
			`class_id` INT unsigned NOT NULL,
			`CNIC` TEXT,
			`DOB` DATE NOT NULL,
			`admitted_on` DATE NOT NULL,
			`gender` CHAR(1) NOT NULL,
			`address` TEXT NOT NULL,
			`country` VARCHAR(2) NOT NULL,
			`city` TEXT NOT NULL,
			`email` TEXT,
			`phone` TEXT,
			FOREIGN KEY `class_id__students` (`class_id`) REFERENCES {0}_classes(`id`)
			) DEFAULT CHARSET = utf8mb4
		""".format(request.form['handle']))

		# PARENTS
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_guardians`
			(
			`id` INT unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`student_id` BIGINT(20) unsigned NOT NULL,
			`first_name` TEXT NOT NULL,
			`middle_name` TEXT,
			`last_name` TEXT NOT NULL,
			`CNIC` TEXT NOT NULL,
			`relation` TEXT NOT NULL,
			`occupation` TEXT,
			`email` TEXT,
			`phone` TEXT,
			FOREIGN KEY `student_id__guradians` (`student_id`) REFERENCES {0}_students(`id`)
			) DEFAULT CHARSET = utf8mb4
		""".format(request.form['handle']))

		# SPECIAL INFO (Matric/Inter/SAT/Any-Entry-Test marks)

		# TESTS
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_tests`
			(
			`id` BIGINT(20) unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`class_id` INT unsigned NOT NULL,
			`subject_id` INT unsigned NOT NULL,
			`total` INT unsigned NOT NULL,
			`test_date` DATE NOT NULL,
			FOREIGN KEY `class_id__tests` (`class_id`) REFERENCES {0}_classes(`id`),
			FOREIGN KEY `subject_id__tests` (`subject_id`) REFERENCES {0}_subjects(`id`)
			) DEFAULT CHARSET = utf8mb4
		""".format(request.form['handle']))

		# TESTS_GIVEN
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_tests_given`
			(
			`test_id` BIGINT(20) unsigned NOT NULL,
			`student_id` BIGINT(20) unsigned NOT NULL,
			`obtained` INT unsigned NOT NULL,
			FOREIGN KEY `test_id__tests_given` (`test_id`) REFERENCES {0}_tests(`id`),
			FOREIGN KEY `student_id__tests_given` (`student_id`) REFERENCES {0}_students(`id`)
			) DEFAULT CHARSET = utf8mb4
		""".format(request.form['handle']))

		# FEES
		#db.execute("""CREATE TABLE IF NOT EXISTS `{0}_fees` ()""".format(request.form['handle']))

		# POSITIONS
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_positions`
			(
			`id` INT unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`title` VARCHAR(60) NOT NULL
			) DEFAULT CHARSET = utf8mb4
		""".format(request.form['handle']))
		# fill in positions
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Teacher')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Professor')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Assistant Professor')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Principal')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Vice Principal')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Guard')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Housekeeping Staff')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Director')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Accountant')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Manager')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Librarian')".format(request.form['handle']))
		db.execute("INSERT INTO {0}_positions (`title`) VALUES('Examiner')".format(request.form['handle']))

		# EMPLOYEES
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_employees`
			(
			`id` BIGINT(20) unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`first_name` TEXT NOT NULL,
			`middle_name` TEXT,
			`last_name` TEXT NOT NULL,
			`picture_url` TEXT NOT NULL,
			`phone_number_1` TEXT NOT NULL,
			`phone_number_2` TEXT,
			`address` TEXT NOT NULL,
			`cnic` TEXT,
			`joined_on` DATE NOT NULL,
			`position_id` INT unsigned NOT NULL,
			FOREIGN KEY `position_id__employees` (`position_id`) REFERENCES {0}_positions(`id`)
			) DEFAULT CHARSET = utf8mb4
		""".format(request.form['handle']))

		# EMPLOYEE_QUALIFICATIONS
		#db.execute("""CREATE TABLE IF NOT EXISTS `{0}_employee_qualifications` ()""".format(request.form['handle']))

		# TIME_TABLES

		# SALARIES

		# organization created successfully
		flash("New organization, titled '{}', was created successfully".format(request.form["title"]))
		return redirect(url_for('dashboard'))
	else:
		return render_template("dashboard/dashboard_new_organization.html")

@app.route("/dashboard/account", methods=['POST', 'GET'])
@login_required
def dashboard_account():
	if request.method == "POST":
		return "TODO: oh wait just wait"
	else:
		return render_template("dashboard/dashboard_account.html",
			user_orgs = db.execute("SELECT * FROM `organizations` WHERE `owner_id` = :owner",
			owner = session["user_id"])
			)

# organization dashboard
@app.route("/organization/<handle>")
@login_required
def organization(handle):
	return render_template("organization/dashboard.html",
		organization = db.execute("SELECT `title`, `handle` FROM `organizations` WHERE `handle` = :handle", handle = handle)[0],
		n_classes = len(db.execute("SELECT `id` FROM {}_classes".format(handle))),
		n_students = len(db.execute("SELECT `id` FROM {}_students".format(handle))),
		n_subjects = len(db.execute("SELECT `id` FROM {}_subjects".format(handle))),
		n_positions = len(db.execute("SELECT `id` FROM {}_positions".format(handle))),
		n_staff = len(db.execute("SELECT `id` FROM {}_employees".format(handle)))
		)

# organization classes
@app.route("/organization/<handle>/classes/<action>", methods=['POST', 'GET'])
@app.route("/organization/<handle>/classes/<action>/<class_id>", methods=['POST', 'GET'])
@login_required
def organization_classes(handle, action, class_id=None):
	if request.method == "POST":
		# create a new class
		if action == "new":
			if not request.form["name"] or not request.form["fee"]:
				return apology("Fill the form correctly")
			if len(db.execute("SELECT id FROM {}_classes WHERE name = :name".format(handle), name = request.form["name"])) > 0:
				return apology("Class Name already exists", ":(")

			class_id = db.execute("INSERT INTO {}_classes (name, start_date, end_date, fee, timing_start, timing_end) VALUES (:name, :start_date, :end_date, :fee, :timing_start, :timing_end)".format(handle),
				name = request.form["name"],
				start_date = request.form.get("start_date") or None,
				end_date = request.form.get("end_date") or None,
				fee = request.form.get("fee"),
				timing_start = request.form.get("timing_start") or None,
				timing_end = request.form.get("timing_end") or None
			)

			# insert subjects into `class_subjects` table
			subjects = request.form.getlist('subjects[]')
			for subject in subjects:
				db.execute("INSERT INTO {0}_class_subjects (`class_id`, `subject_id`) VALUES (:class_id, :subject_id)".format(handle),
					class_id = class_id,
					subject_id = subject
				)

			# create related timetable file
			# on class creation, create its timetable file
			pathlib.Path('organizations/{0}/timetables/'.format(handle)).mkdir(parents=True, exist_ok=True)
			timetable_file = open('organizations/{0}/timetables/{1}.csv'.format(handle, class_id), 'w+')
			timetable_file.close()

			flash("New Class, titled '{}', was created successfully with id: {}".format(request.form["name"], class_id))
			return redirect(url_for('organization', handle=handle))
		elif action == "modify":
			return "Do something..."
		else:
			return apology("Unknown action", ":(")
	else:
		if action == "new":
			return render_template("organization/classes_create_new.html",
				handle = handle,
				subjects = db.execute("SELECT * FROM {}_subjects".format(handle))
				)
		elif action == "modify":
			return render_template("organization/classes_modify.html")
		elif action == "view" and class_id:
			return render_template("organization/classes_view_class.html",
				handle = handle,
				_class = db.execute("SELECT * FROM {}_classes WHERE id = {}".format(handle, class_id))[0],
				students = db.execute("SELECT * FROM {}_students".format(handle))
				)
		elif action == "view":
			return render_template("organization/classes_view.html",
				handle = handle,
				classes = db.execute("SELECT * FROM {}_classes".format(handle)),
				nstudents = db.execute("SELECT `TABLE_ROWS` FROM information_schema.tables WHERE table_schema = '{}' AND `TABLE_NAME` = '{}_students'".format(DB_DATABASE_MAS, handle))[0]["TABLE_ROWS"]
				)
		else:
			return apology("Unknown action", ":(")

# organization students
@app.route("/organization/<handle>/students/<action>", methods=['POST', 'GET'])
@app.route("/organization/<handle>/students/<action>/<student_id>", methods=['POST', 'GET'])
@login_required
def organization_students(handle, action, student_id=None):
	if request.method == "POST":
		if action == "new":
			records = len(request.form.getlist("first_name[]"))

			for i in range(records):
				if not request.form.getlist("first_name[]")[i] or not request.form.getlist("last_name[]")[i] \
				or not request.form.getlist("class[]")[i] or not request.form.getlist("gender[]")[i] \
				or not request.form.getlist("cnic[]")[i] or not request.form.getlist("DOB[]")[i] \
				or not request.form.getlist("address[]")[i] or not request.form.getlist("country[]")[i] \
				or not request.form.getlist("city[]")[i] or not request.form.getlist("guardian_first_name[]")[i] \
				or not request.form.getlist("guardian_last_name[]")[i] or not request.form.getlist("guardian_cnic[]")[i] \
				or not request.form.getlist("guardian_relation[]")[i] or not request.form.getlist("guardian_phone[]")[i]:
					return "{}".format(i)

			for i in range(records):
				student_id = db.execute("INSERT INTO {}_students (first_name, middle_name, last_name, class_id, CNIC, DOB, admitted_on, gender, address, country, city, email, phone) VALUES (:first_name, :middle_name, :last_name, :class_id, :CNIC, :DOB, :admitted_on, :gender, :address, :country, :city, :email, :phone)".format(handle),
					first_name = request.form.getlist("first_name[]")[i],
					middle_name = request.form.getlist("middle_name[]")[i] or None,
					last_name = request.form.getlist("last_name[]")[i],
					class_id = request.form.getlist("class[]")[i],
					CNIC = request.form.getlist("cnic[]")[i] or None,
					DOB = request.form.getlist("DOB[]")[i] or None,
					admitted_on = request.form.getlist("admitted_on[]")[i] or None,
					gender = request.form.getlist("gender[]")[i],
					address = request.form.getlist("address[]")[i],
					country = request.form.getlist("country[]")[i],
					city = request.form.getlist("city[]")[i],
					email = request.form.getlist("email[]")[i] or None,
					phone = request.form.getlist("phone[]")[i] or None
				)

				db.execute("INSERT INTO {}_guardians (student_id, first_name, middle_name, last_name, CNIC, relation, occupation, email, phone) VALUES (:student_id, :first_name, :middle_name, :last_name, :CNIC, :relation, :occupation, :email, :phone)".format(handle),
					student_id = student_id,
					first_name = request.form.getlist("guardian_first_name[]")[i],
					middle_name = request.form.getlist("guardian_middle_name[]")[i] or None,
					last_name = request.form.getlist("guardian_last_name[]")[i],
					CNIC = request.form.getlist("guardian_cnic[]")[i],
					relation = request.form.getlist("guardian_relation[]")[i],
					occupation = request.form.getlist("guardian_occupation[]")[i],
					email = request.form.getlist("guardian_email[]")[i] or None,
					phone = request.form.getlist("guardian_phone[]")[i] or None
				)

			flash("{} new students were created successfully.".format(records))
			return redirect(url_for('organization', handle=handle))
		elif action == "modify":
			return "Do something..."
		else:
			return apology("Unknown action", ":(")
	else:
		if action == "new":
			return render_template("organization/students_create_new.html",
				handle = handle,
				classes = db.execute("SELECT `id`, `name` FROM {}_classes".format(handle)),
				now = datetime.utcnow().strftime("%Y-%m-%d")
				)
		elif action == "modify":
			return render_template("organization/students_modify.html")
		elif action == "view" and student_id:
			student = db.execute("SELECT `first_name`, `last_name`, `class_id`, `email` FROM {}_students WHERE `id` = {}".format(handle, student_id))[0]

			return render_template("organization/students_view_student.html",
				student = student,
				class_name = db.execute("SELECT `name` FROM {}_classes WHERE `id` = {}".format(handle, student["class_id"]))[0]["name"]
				)
		elif action == "view":
			return render_template("organization/students_view.html",
				handle = handle,
				students = db.execute("SELECT `id`, `first_name`, `last_name`, `class_id`, `email` FROM {}_students".format(handle)),
				classes = db.execute("SELECT `name` FROM {}_classes".format(handle))
				)
		else:
			return apology("Unknown action", ":(")

# organization subjects
@app.route("/organization/<handle>/subjects/<action>", methods=['POST', 'GET'])
@login_required
def organization_subjects(handle, action):
	if request.method == "POST":
		if action == "new":
			records = len(request.form.getlist("title[]"))

			for i in range(records):
				title = request.form.getlist("title[]")[i]
				if len(db.execute("SELECT `id` FROM `{}_subjects` WHERE `name` = :title".format(handle), title = title)) > 0:
					return apology("Subject '{}' already exists".format(title), ":(")

			for i in range(records):
				db.execute("INSERT INTO `{}_subjects` (name) VALUES (:title)".format(handle),
					title = request.form.getlist("title[]")[i]
				)

			flash("{} new subjects were added successfully.".format(records))
			return redirect(url_for('organization', handle=handle))
		elif action == "modify":
			return "Do something..."
		else:
			return apology("Unknown action", ":(")
	else:
		if action == "new":
			return render_template("organization/subjects_create_new.html", handle=handle)
		elif action == "modify":
			return render_template("organization/subjects_modify.html")
		elif action == "view":
			return render_template("organization/subjects_view.html",
				subjects = db.execute("SELECT `name` FROM {}_subjects".format(handle))
				)
		else:
			return apology("Unknown action", ":(")

# organization tests
@app.route("/organization/<handle>/tests/<action>", methods=['POST', 'GET'])
@app.route("/organization/<handle>/tests/<action>/<class_id>", methods=['POST', 'GET'])
@login_required
def organization_tests(handle, action, class_id=None):
	if request.method == "POST":
		if action == "new":
			records = len(request.form.getlist("id[]"))

			for i in range(records):
				db.execute("INSERT INTO {}_tests (`student_id`, `obtained`, `total`, `subject_id`, `test_date`) VALUES (:student_id, :obtained, :total, :subject_id, :test_date)".format(handle),
					student_id = request.form.getlist("id[]")[i],
					obtained = request.form.getlist("obtained[]")[i],
					total = request.form.getlist("total[]")[i],
					subject_id = request.form.getlist("subject[]")[i],
					test_date = request.form.getlist("test_date[]")[i]
				)

			flash("{} new tests were added successfully.".format(records))
			return redirect(url_for('organization', handle=handle))
		elif action == "modify":
			return "Do something..."
		else:
			return apology("Unknown action", ":(")
	else:
		if action == "new" and class_id or request.args.get("class_id"):
			return render_template("organization/tests_create_new.html",
				handle = handle,
				subjects = db.execute("SELECT * FROM {}_subjects".format(handle)),
				now = datetime.utcnow().strftime("%Y-%m-%d"),
				students = db.execute("SELECT `id`, `first_name`, `last_name` FROM {}_students WHERE `class_id` = {}".format(handle, class_id or request.args.get("class_id")))
				)
		elif action == "modify":
			return render_template("organization/tests_modify.html")
		elif action == "view":
			return render_template("organization/tests_view.html",
				tests = db.execute("SELECT `title` FROM {}_subjects".format(handle))
				)
		else:
			flash("Unknown action performed.")
			return redirect(url_for('organization', handle=handle))

# organization staff
# TODO
@app.route("/organization/<handle>/staff/<action>", methods=['POST', 'GET'])
@app.route("/organization/<handle>/staff/<action>/<class_id>", methods=['POST', 'GET'])
@login_required
def organization_staff(handle, action, class_id=None):
	if request.method == "POST":
		if action == "new":
			records = len(request.form.getlist("id[]"))

			for i in range(records):
				db.execute("INSERT INTO {}_staff (`student_id`, `obtained`, `total`, `subject_id`, `test_date`) VALUES (:student_id, :obtained, :total, :subject_id, :test_date)".format(handle),
					student_id = request.form.getlist("id[]")[i],
					obtained = request.form.getlist("obtained[]")[i],
					total = request.form.getlist("total[]")[i],
					subject_id = request.form.getlist("subject[]")[i],
					test_date = request.form.getlist("test_date[]")[i]
				)

			flash("{} new staff person(s) were added successfully.".format(records))
			return redirect(url_for('organization', handle=handle))
		elif action == "modify":
			return "<h2>Not Implemented</h2>"
		else:
			return apology("Unknown action", ":(")
	else:
		if action == "new":
			return render_template("organization/staff_create_new.html",
				handle = handle,
				positions = db.execute('SELECT * FROM {}_positions'.format(handle)),
				now = datetime.utcnow().strftime("%Y-%m-%d"),
				)
		elif action == "modify":
			return render_template("organization/staff_modify.html")
		elif action == "view":
			return render_template("organization/staff_view.html",
				tests = db.execute("SELECT `title` FROM {}_subjects".format(handle))
				)
		else:
			flash("Unknown action performed.")
			return redirect(url_for('organization', handle=handle))

# TimeTable Manager TODO
@app.route("/organization/<handle>/timetables/<action>", methods=['POST', 'GET'])
@app.route("/organization/<handle>/timetables/<action>/<class_id>", methods=['POST', 'GET'])
@login_required
def organization_timetables(handle, action, class_id=None):
	return "Yare yare daze"