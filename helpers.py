import urllib.request
from urllib.parse import urlparse, urljoin

from flask import redirect, render_template, request, session, url_for
from functools import wraps

def login_required(f):
	"""
	Decorate routes to require login.

	http://flask.pocoo.org/docs/0.11/patterns/viewdecorators/
	"""
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if session.get("user_id") is None:
			return redirect(url_for("login", next=request.url))
		return f(*args, **kwargs)
	return decorated_function

def apology(top="", bottom=""):
	"""Renders message as an apology to user."""
	def escape(s):
		"""
		Escape special characters.

		https://github.com/jacebrowning/memegen#special-characters
		"""
		for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
			("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
			s = s.replace(old, new)
		return s
	return render_template("apology.html", top=escape(top), bottom=escape(bottom))

def is_safe_url(target):
	ref_url = urlparse(request.host_url)
	test_url = urlparse(urljoin(request.host_url, target))
	return test_url.scheme in ('http', 'https') and\
		ref_url.netloc == test_url.netloc

# FILTERS
def gender(code):
	genders = {"M": "Male", "F": "Female", "O": "Others"}
	return genders[code]