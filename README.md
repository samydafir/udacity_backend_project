# Project: Aircraft Catalog

### What does the app do?
This app is lets serves as a collection of aircraft-manufacturers and -types.
It includes following features:
+ Create, Delete, Modify and Update manufacturers as well as aircraft types
+ User authentication and authorisation using Google accounts (OAuth2)
+ Manufacturer information includes name only at this time
+ Aircraft information contains: type(name), description, price, range, as well
  as a photo (URL) of the aircraft. This list can of course be expanded to include
  more details.
+ Viewing of manufacturers and aircraft requires no authentication and can
  thus be viewed by anyone.
+ A JSON representation of manufacturers and aircraft is also accessible without
  authentication.
+ Creation of new manufacturers and/or aircraft requires a logged in user.
+ At creation of a new entry the user_id of the generating user is logged in the
  corresponding table.
+ Aircraft or Manufacturers may only be edited or deleted by the user who created
  them

### Technical Requirements and used Components
+ Python3
+ SQLite3
+ SQLAlchemy
+ Flask
+ Bootstrap

### Running the application
+ Run `python database_setup.py` to set up the database
+ Start the server by executing project.py: `python project.py`
+ project.py listens to incoming connections on port 8000


### Disclaimer
+ The login part (route "/login") was taken directly from the code previously
  implemented in the OAuth lesson of this course.
+ Images are only saved as URLs. Currently all aircraft images are taken from
  wikimedia commons.
