from flask import Flask, flash, redirect, request, render_template, session, url_for, abort
from flask_session import Session
from tempfile import mkdtemp
from passlib.apps import custom_app_context as pwd_context
from datetime import datetime

from cs50 import SQL

from helpers import *
from constants import *

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

# connect to user accounts database
users_db = SQL("mysql://" + DB_USERNAME + ":" + DB_PASSWORD + "@" + DB_SERVER + "/" + DB_DATABASE_USERS)

@app.route("/")
def index():
	return render_template("home.html")

@app.route("/login", methods=['POST', 'GET'])
def login():
	# forget any user_id
	session.clear()

	# if user got here via POST (form submission)
	if request.method == "POST":
		if not request.form["username"]:
			return apology("Please provide a username")

		rows = users_db.execute("SELECT * FROM users WHERE username = :username", username = request.form["username"])
			
		# ensure username exists and password is correct
		if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["password"]):
			return apology("invalid username and/or password")

		# remember which user has logged in
		session["user_id"] = rows[0]["id"]
		session["full_name"] = rows[0]["full_name"]

		flash("You have been logged in! :)")

		next = request.args.get('next')
		# is_safe_url should check if the url is safe for redirects.
		# See http://flask.pocoo.org/snippets/62/ for an example.
		if not is_safe_url(next):
			return abort(400)

		# redirect user where they came from or to home page
		return redirect(next or url_for("dashboard"))

	# else if user got here via a GET
	else:
		return render_template("login.html")

@app.route("/logout")
def logout():
	"""Log user out."""

	# forget any user_id etc
	session.clear()

	# redirect user to login form
	return redirect(url_for("login"))

@app.route("/register", methods=['POST', 'GET'])
def register():
	# if user got here via POST (form submission)
	if request.method == "POST":

		# username validation
		if not request.form["username"]:
			return apology("Please provide a username")

		# validate email address

		# check password length

		row = users_db.execute("SELECT * FROM users WHERE username = :username", username = request.form["username"])
		if len(row) > 0:
			return "oops! there is already someone with that username."

		# validate and hash password
		if not request.form["password"] == request.form["password_confirm"]:
			return apology("Password confirmation failed!")

		hash = pwd_context.hash(request.form["password"])
		user_id = users_db.execute(
				"INSERT INTO users (username, email, password, full_name, registered_with, profile_pic, registered_on, about_me) VALUES (:username, :email, :password, :full_name, :registered_with, :profile_pic, :registered_on, :about_me)",
					username = request.form["username"],
					email = request.form["email"],
					password = hash,
					full_name = request.form["full-name"],
					registered_with = "NN",
					profile_pic = "\0",
					registered_on = str( datetime.now().strftime("%Y-%m-%d") ),
					about_me = "About myself..."
				)

		session["user_id"] = user_id

		row = users_db.execute("SELECT full_name FROM users WHERE id = :id", id = user_id)

		session["full_name"] = row["full_name"]
		
		flash("You have been registered successfully! :)")
		return redirect(url_for("dashboard"))
	
	# else if user got here via a GET
	else:	
		return render_template("register.html")

@app.route("/dashboard")
@login_required
def dashboard():
	user_orgs = db.execute("SELECT * FROM organizations WHERE owner_id = :owner", owner = session["user_id"])
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
		db.execute("INSERT INTO organizations (owner_id, handle, title, type, email, phone, address, city, country) VALUES (:owner_id, :handle, :title, :type, :email, :phone, :address, :city, :country)",
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

		# Create required database tables
		# CLASSES
		db.execute("""CREATE TABLE IF NOT EXISTS `{}_classes`
			(
			`id` INT unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`name` VARCHAR(100) NOT NULL UNIQUE,
			`start_date` DATE,
			`end_date` DATE,
			`fee` INT NOT NULL,
			`timing_start` TIME,
			`timing_end` TIME
			) DEFAULT CHARSET = utf8
		""".format(request.form["handle"]))

		# SUBJECTS
		db.execute("""CREATE TABLE IF NOT EXISTS `{}_subjects`
			(
			`id` INT unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`name` TEXT NOT NULL
			) DEFAULT CHARSET = utf8
		""".format(request.form["handle"]))

		# STUDENTS
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_students`
			(
			`id` INT unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
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
			FOREIGN KEY (`class_id`) REFERENCES {0}_classes(`id`)
			) DEFAULT CHARSET = utf8
		""".format(request.form["handle"]))

		# PARENTS
		db.execute("""CREATE TABLE IF NOT EXISTS `{0}_guardians`
			(
			`id` INT unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
			`student_id` INT unsigned NOT NULL,
			`first_name` TEXT NOT NULL,
			`middle_name` TEXT,
			`last_name` TEXT NOT NULL,
			`CNIC` TEXT NOT NULL,
			`relation` TEXT NOT NULL,
			`occupation` TEXT,
			`email` TEXT,
			`phone` TEXT,
			FOREIGN KEY (`student_id`) REFERENCES {0}_students(`id`)
			) DEFAULT CHARSET = utf8
		""".format(request.form["handle"]))

		# SUBJECTS

		# MATRIC_MARKS

		# INTER_MARKS

		# TESTS

		# FEES

		# EMPLOYEES

		# SALARIES

		# POSITIONS

		# POSITION_EMPLOYEE

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
			user_orgs = db.execute("SELECT * FROM organizations WHERE owner_id = :owner",
			owner = session["user_id"])
			)

# organization dashboard
@app.route("/organization/<handle>")
@login_required
def organization(handle):
	return render_template("organization/dashboard.html",
		organization = db.execute("SELECT title FROM organizations WHERE handle = :handle", handle = handle)[0],
		n_classes = len(db.execute("SELECT id FROM {}_classes".format(handle))),
		n_students = len(db.execute("SELECT id FROM {}_students".format(handle))),
		n_subjects = 0
		)

# organization classes
@app.route("/organization/<handle>/classes/<action>", methods=['POST', 'GET'])
@app.route("/organization/<handle>/classes/<action>/<_class>", methods=['POST', 'GET'])
@login_required
def organization_classes(handle, action, _class=None):
	if request.method == "POST":
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

			flash("New Class, titled '{}', was created successfully with id: {}".format(request.form["name"], class_id))
			return redirect(url_for('organization', handle=handle))
		elif action == "modify":
			return "Do something..."
		else:
			return apology("Unknown action", ":(")
	else:
		if action == "new":
			return render_template("organization/classes_create_new.html", handle=handle)
		elif action == "modify":
			return render_template("organization/classes_modify.html")
		elif action == "view":
			return render_template("organization/classes_view.html",
				classes = db.execute("SELECT * FROM {}_classes".format(handle)),
				nstudents = db.execute("SELECT `TABLE_ROWS` FROM information_schema.tables WHERE table_schema = '{}' AND `TABLE_NAME` = '{}_students'".format(DB_DATABASE_MAS, handle))[0]["TABLE_ROWS"]
				)
		else:
			return apology("Unknown action", ":(")

# organization students
@app.route("/organization/<handle>/students/<action>", methods=['POST', 'GET'])
@app.route("/organization/<handle>/students/<action>/<class_id>", methods=['POST', 'GET'])
@login_required
def organization_students(handle, action, student=None):
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
				classes = db.execute("SELECT id, name FROM {}_classes".format(handle)),
				now = datetime.utcnow().strftime("%Y-%m-%d")
				)
		elif action == "modify":
			return render_template("organization/students_modify.html")
		elif action == "view":
			return render_template("organization/students_view.html",
				students = db.execute("SELECT first_name, last_name, class_id, email FROM {}_students".format(handle))
				)
		else:
			return apology("Unknown action", ":(")