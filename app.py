from flask import Flask, render_template, request, redirect, session
from flask_caching import Cache
import os
import pymongo
import hashlib

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["Noctora"]
clients = mydb['clients']
transaction = mydb['transactions']


@app.before_request
def before_request():
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)


def gen_hash(string, salt):
    return sha512((salt+string).encode()).hexdigest()


def salt():
    return ''.join(random.SystemRandom().choice(
        string.ascii_uppercase + string.digits) for _ in range(50))


def checkFields(form, conditions):
    for con in conditions:
        if not con in form:
            return False
    return True


@app.route('/', methods=["GET", "POST"])
@cache.cached()
def login():
    if request.method == "GET":
        if 'username' in session:
			return render_template('index.html')

		return render_template('login.html')
    else:
        data = dict(request.form)
        if data['username'] == 'lkgfbd@gmail.com' and data['password'] == 'hexMYlab':
            session['username'] = "lkgfbd"
            return render_template('index.html')
        else:
            return "<h1> Invalid Credentials !! </h1>"


@app.route('/search', methods=['GET'])
def search_client():
    if 'username' not in session:
        return redirect('/', code=403)

	keyword = dict(request.form)['search']
    keyword = keyword.lower()
    search_expr = re.compile(f".*{keyword}.*", re.I)

	# TODO: CHANGE SEARCH FIELDS FOR `search_request`
    search_request = {
        '$or': [
            {'email': {'$regex': search_expr}},
            {'name': {'$regex': search_expr}},
        ]
    }

    results = list(clients.find(search_request))

	#  TODO: serve to a template here


@app.route('/add', methods=['GET', 'POST'])
def add_client():
	if 'username' not in session:
		return redirect('/', code=403)
	if request.method == 'GET':
		return render_template('add_client.html')
	else:
		data = dict(request.form)
		if not checkFields(credentials, ['file', 'name', 'pan', 'remarks']):
        	return "Insufficient fields!"

		for field in data:
			data[field] = data[field].lower()

		# TODO: Check PAN Format here

		client = {'file': data['file'], 'name': data['name'],
		    'pan': data['pan'], 'remarks': data['remarks']}

		clients.insert_one(client)

		# TODO: Save image of client if present
		if 'image' in data:
			pass
		
		return redirect('/')


@app.route('/edit/<id>', methods=['GET', 'PATCH'])
def edit_client(id):
	if 'username' not in session:
		return redirect('/')
	
	if request.method == 'GET':
		#  TODO: Try using Add Client here
		return render_template('edit_client.html')
	
	


@app.route('/delete/<id>', methods=['DELETE'])
def delete_client():
	pass


@app.route('/profile', methods=['GET', 'POST'])
def show_profile():
	pass


@app.route('/add_record', methods=['POST'])
def add_transaction():
	pass


@app.route('/edit_transaction', methods=['PATCH'])
def edit_transaction():
	pass


@app.route('/delete_transaction', methods=['DELETE'])
def delete_transaction():
	pass


if __name__ == '__main__':
	app.secret_key = os.urandom(24)
    app.run(debug=True, port=5000)
	
