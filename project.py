#!/usr/bin/python3

from flask import Flask, render_template, request, redirect, jsonify, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Manufacturer, Aircraft, User
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import random
import string
from flask import make_response
import requests

app = Flask(__name__)

# Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(
    open('secret.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Aircraft Catalog"


@app.route('/login', methods=['GET', 'POST'])
def login():
    """This method handles the login procedure using OAuth2 enabling login
    using a google account. If the function is called via a GET request a
    session token is generated and the login page renderedself.
    The POST part of this function handles logging in using OAuth as well as
    setting session information such as username, user_id,....
    """
    if request.method == 'GET':
        token = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['token'] = token
        return render_template('login.html', pageTitle="Login", TOKEN=token)
    else:
        # Validate state token
        if request.args.get('token') != login_session['token']:
            response = make_response(
                json.dumps('Invalid state parameter.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response
        # Obtain authorization code
        code = request.data

        try:
            # Upgrade the authorization code into a credentials object
            oauth_flow = flow_from_clientsecrets('secret.json', scope='')
            oauth_flow.redirect_uri = 'postmessage'
            credentials = oauth_flow.step2_exchange(code)
        except FlowExchangeError:
            response = make_response(
                json.dumps('Failed to upgrade the authorization code.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response

        # Check that the access token is valid.
        access_token = credentials.access_token
        url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
               % access_token)
        h = httplib2.Http()
        result = json.loads(h.request(url, 'GET')[1])
        # If there was an error in the access token info, abort.
        if result.get('error') is not None:
            response = make_response(json.dumps(result.get('error')), 500)
            response.headers['Content-Type'] = 'application/json'
            return response

        # Verify that the access token is used for the intended user.
        gplus_id = credentials.id_token['sub']
        if result['user_id'] != gplus_id:
            response = make_response(
                json.dumps("Token's user ID doesn't match given user ID."),
                401)
            response.headers['Content-Type'] = 'application/json'
            return response

        # Verify that the access token is valid for this app.
        if result['issued_to'] != CLIENT_ID:
            response = make_response(
                json.dumps("Token's client ID does not match app's."), 401)
            print "Token's client ID does not match app's."
            response.headers['Content-Type'] = 'application/json'
            return response

        stored_access_token = login_session.get('access_token')
        stored_gplus_id = login_session.get('gplus_id')
        if stored_access_token is not None and gplus_id == stored_gplus_id:
            response = make_response(
                json.dumps('Current user is already connected.'), 200)
            response.headers['Content-Type'] = 'application/json'
            return response

        # Store the access token in the session for later use.
        login_session['access_token'] = credentials.access_token
        login_session['gplus_id'] = gplus_id

        # Get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        params = {'access_token': credentials.access_token, 'alt': 'json'}
        answer = requests.get(userinfo_url, params=params)

        data = answer.json()

        login_session['username'] = data['given_name']
        login_session['picture'] = data['picture']
        login_session['email'] = data['email']

        # check if user in db, if not add
        user_id = getUserID(login_session['email'])
        if user_id is None:
            createUser(login_session)

        login_session['user_id'] = user_id

        # print(login_session)
        output = ''
        output += '<h1>Welcome, '
        output += login_session['username']
        output += '!</h1>'
        output += '<img src="'
        output += login_session['picture']
        output += ' " style = "width: 150px; height: 150px;border-radius: 50%;'
        output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;">'
        return output


@app.route('/logout')
def logout():
    """This function can only be called using GET. It handles the
    logout procedure revokingthe OAuth authorisation token and deleting all
    saved user-session-information.
    """
    credentials = login_session.get('access_token')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = login_session.get('access_token')
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']

        return render_template('logout.html')
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
@app.route('/manufacturers')
def showManufacturers():
    """Default function showing the startpage which is also the page listing
    all manufacturers. Simply queries all manufacturers and passes data to the
    template engine to be processed. No authentication required.
    """
    manufacturers = session.query(Manufacturer).all()
    return render_template(
        'show_manufacturers.html',
        manufacturers=manufacturers, pageTitle="Aircraft Manufacturers")


@app.route('/manufacturers/new', methods=['GET', 'POST'])
def newManufacturer():
    """Creation of a new manufacturer. Returns a page with a form to create
    a new manufacturer if requested using GET. The POST branchcreates a new
    manufacturer and inserts it into the database. Authentication but no
    special authorisation required:
    Only logged in users can create new manufacturers.
    """
    if "user_id" in login_session:
        if request.method == "GET":
            return render_template(
                'new_manufacturer.html', pageTitle="Create new Manufacturer",
                TOKEN=login_session['token'])
        else:
            if request.form['name'] and \
                    request.form['token'] == login_session['token']:
                newMan = Manufacturer(
                    name=request.form['name'],
                    user_id=login_session['user_id'])
                session.add(newMan)
                session.commit()
                return redirect(url_for('showManufacturers'))

    return redirect(url_for('login'))


@app.route('/manufacturers/<int:man_id>/edit', methods=['GET', 'POST'])
def editManufacturer(man_id):
    """When requested using GET this function returns a form containing all
    editable information a manufacturer might have: in this case their name.
    POST requests are required to have the "name" attribute set. The name will
    then be changed and the manufacturer tuple inside the database updated.
    Requires authentication as well as authorisation: Only the user who created
    a manufacturer may edit it.
    """
    manufacturer = session.query(Manufacturer).filter_by(id=man_id).first()
    if "user_id" in login_session:
        if login_session['user_id'] == manufacturer.user_id:
            if request.method == "GET":
                return render_template(
                    'edit_manufacturer.html', pageTitle="Edit Manufacturer",
                    manufacturer=manufacturer,
                    TOKEN=login_session['token'])
            else:
                if request.form['name'] and \
                        request.form['token'] == login_session['token']:
                    manufacturer.name = request.form['name']
                    session.add(manufacturer)
                    session.commit()
                    return redirect(url_for('showManufacturers'))

    return redirect(url_for('login'))


@app.route('/manufacturers/<int:man_id>/delete', methods=['GET', 'POST'])
def deleteManufacturer(man_id):
    """Returns a confirmation page when requested using GET.
    The POST branch checks if the "delete" operation was confirmed and deletes
    the manufacturer from the database.
    Requires authentication as well as authorisation: Only the user who created
    a manufacturer may delete it.
    """
    manufacturer = session.query(Manufacturer).filter_by(id=man_id).first()
    if "user_id" in login_session:
        if login_session['user_id'] == manufacturer.user_id:
            if request.method == "GET":
                manufacturer = session.query(Manufacturer).filter_by(
                    id=man_id).first()
                return render_template(
                    'delete_manufacturer.html',
                    pageTitle="Delete Manufacturer", manufacturer=manufacturer,
                    TOKEN=login_session['token'])
            else:
                if "confirmed" in request.form and \
                        request.form['token'] == login_session['token']:
                    session.delete(manufacturer)
                    session.commit()
                    return redirect(url_for('showManufacturers'))
                return redirect(url_for('deleteManufacturer', man_id=man_id))

    return redirect(url_for('login'))


@app.route('/manufacturers/<int:man_id>')
def showAircraft(man_id):
    """Only listens to GET requests. Returns all aircraft in the database
    manufactured ba the manufacturer with the given ID.
    Requires no authentication. Aircraft may be viewed by anyone.
    """
    aircraft = session.query(Aircraft).filter_by(
        manufacturer_id=man_id).all()
    manufacturer = session.query(Manufacturer).filter_by(id=man_id).first()
    return render_template(
        'show_aircraft.html', aircraft=aircraft,
        pageTitle="All aircraft produced by " + manufacturer.name,
        man_id=man_id)


@app.route(
    '/manufacturers/<int:man_id>/<int:aircraft_id>/edit',
    methods=['GET', 'POST'])
def editAircraft(man_id, aircraft_id):
    """Edit an aircraft identified by its own id as well as the manufacturer's
    id. Responds to GET requests by returning a form containing the aircraft's
    editable information.
    POST requests contain all information which should be updated. Only updates
    attributes of an aircraft entry contained in the request, all others are
    left at their previous values. The user is not required to fill out all
    form fields.
    Requires authentication as well as authorisation: Only the creator of an
    aircraft entry may edit it.
    """
    aircraft = session.query(Aircraft).filter_by(
        id=aircraft_id,
        manufacturer_id=man_id).first()
    if "user_id" in login_session:
        if login_session['user_id'] == aircraft.user_id:
            if request.method == "GET":
                return render_template(
                    'edit_aircraft.html',
                    pageTitle="Edit Aircraft: " + aircraft.name,
                    aircraft=aircraft, TOKEN=login_session['token'])
            elif request.form['token'] == login_session['token']:
                if request.form['name']:
                    aircraft.name = request.form['name']
                if request.form['desc']:
                    aircraft.description = request.form['desc']
                if request.form['price']:
                    aircraft.price = request.form['price']
                if request.form['picture']:
                    aircraft.picture = request.form['picture']
                if request.form['range']:
                    aircraft.range = request.form['range']

                session.add(aircraft)
                session.commit()
                return redirect(url_for('showAircraft', man_id=man_id))

    return redirect(url_for('login'))


@app.route(
    '/manufacturers/<int:man_id>/<int:aircraft_id>/delete',
    methods=['GET', 'POST'])
def deleteAircraft(man_id, aircraft_id):
    """Responds to GET requests by returning a page containing a prompt to
    confirm the "delete" operation.
    POST requests contain a field specifying if the "confirm" checkbox was
    checked by the user. If this is the case, the entry is deleted from the
    database. Requires authentication as well as authorisation: Only the
    creator of an aircraft entry may delete it.
    """
    aircraft = session.query(Aircraft).filter_by(
        id=aircraft_id,
        manufacturer_id=man_id).first()
    if "user_id" in login_session:
        if login_session['user_id'] == aircraft.user_id:
            if request.method == "GET":
                return render_template(
                    'delete_aircraft.html',
                    pageTitle="Delete Aircraft: " + aircraft.name,
                    aircraft=aircraft, TOKEN=login_session['token'])
            else:
                if "confirmed" in request.form and \
                        request.form['token'] == login_session['token']:
                    aircraft = session.query(Aircraft).filter_by(
                        id=aircraft_id).first()
                    session.delete(aircraft)
                    session.commit()
                    return redirect(url_for('showAircraft', man_id=man_id))
                return redirect(url_for(
                    'deleteAircraft', man_id=man_id, aircraft_id=aircraft_id))

    return redirect(url_for('login'))


@app.route('/manufacturers/<int:man_id>/new', methods=['GET', 'POST'])
def newAircraft(man_id):
    """Responds to GET requests by returning a form enabling the user to set
    the new aircraft's data.
    POST requests are processed by taking the form data sent by the client,
    creating a new "Aircraft" object and setting its attributes. This object
    is then inserted into the database.
    Authentication, but no special authorisation is required: Any logged in
    user may create a newaircraft.
    """
    if "user_id" in login_session:
        if request.method == "GET":
            return render_template(
                'new_aircraft.html', pageTitle="Create new Aircraft",
                man_id=man_id, TOKEN=login_session['token'])
        else:
            if request.form['name'] and \
                    request.form['token'] == login_session['token']:
                manufacturer = session.query(Manufacturer).filter_by(
                    id=man_id).first()
                newAc = Aircraft(
                        name=request.form['name'],
                        description=request.form['description'],
                        price=request.form['price'],
                        range=request.form['range'],
                        picture=request.form['picture'],
                        manufacturer_id=man_id,
                        user_id=login_session['user_id'],
                        manufacturer=manufacturer)

                session.add(newAc)
                session.commit()
                return redirect(url_for('showAircraft', man_id=man_id))

    else:
        return redirect(url_for('login'))


@app.route('/manufacturers/json')
def manufacturersJson():
    """Returns a json representation of all manufacturers in the database
    using jsonify.
    No authentication or authorisation.
    """
    manufacturers = session.query(Manufacturer).all()
    return jsonify(Manufacturers=[i.serialize for i in manufacturers])


@app.route('/manufacturers/<int:man_id>/json')
def allAircraftJson(man_id):
    """Returns a json representation of all aircraft built by a certain
    manufacturer.
    No authentication or authorisation.
    """
    aircraft = session.query(Aircraft).filter_by(manufacturer_id=man_id).all()
    return jsonify(Aircraft=[i.serialize for i in aircraft])


@app.route('/manufacturers/<int:man_id>/<int:aircraft_id>/json')
def oneAircraftJson(man_id, aircraft_id):
    """Returns a json representation of one aircraft built by a certain
    manufacturer.
    No authentication or authorisation.
    """
    aircraft = session.query(Aircraft).filter_by(
        manufacturer_id=man_id, id=aircraft_id).first()
    return jsonify(Aircraft=aircraft.serialize)


# USER OPERATIONS #
def createUser(login_session):
    """Creates a new user entry and inserts it into the database. Returns the
    user's id.
    """
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).first()
    return user.id


def getUserInfo(user_id):
    """Returns a user object for a given user id"""
    user = session.query(User).filter_by(id=user_id).first()
    return user


def getUserID(email):
    """returns the id belonging to the same user as the given email address"""
    user = session.query(User).filter_by(email=email).first()
    if user is not None:
        return user.id
    return None
# END USER OPERATIONS #


if __name__ == '__main__':
    app.secret_key = '5D6822E04D9D8A809CF2D20C444C5F2C21C064DB741E5D6C79C702C6'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
