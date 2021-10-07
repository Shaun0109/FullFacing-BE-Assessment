# # # # # # # # # # # #
# AUTHOR: Shaun Dumas #
# # # # # # # # # # # #

from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

import json
import pymongo
import re

# MongoDB instance
MONGO_CLIENT = "mongodb://localhost:27017/"
# Database and table name
MONGO_DATABASE = "todo_app"
TABLE_NAME = "tasks"

# HTTP opened port to run on
HTTP_PORT = 8001

# Default date formats
# System/API dates
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
# Date for tasks only
TASK_DATE = "%Y-%m-%d"

# Messages API responds with if no number to show
return_msg = {"200": {"Result": "successful"},
              "400": {"Result": "fail"}}


class _RequestHandler(BaseHTTPRequestHandler):

    ####################################################################################
    # Handles the basic API calls. If the endpoint is not found, NOT_FOUND is returned #
    ####################################################################################

    def do_GET(self):
        if re.search("/api/tasks", self.path):
            self.handle_get()
        else:
            self._set_headers(HTTPStatus.NOT_FOUND.real)

    def do_POST(self):
        if re.search("/api/tasks/task", self.path):
            self.handle_create(self._get_body())
        else:
            self._set_headers(HTTPStatus.NOT_FOUND.real)

    def do_PATCH(self):
        if re.search("/api/tasks/", self.path):
            self.handle_patch(self._get_body())
        else:
            self._set_headers(HTTPStatus.NOT_FOUND.real)

    def do_DELETE(self):
        if re.search("/api/tasks/", self.path):
            self.handle_delete()
        else:
            self._set_headers(HTTPStatus.NOT_FOUND.real)

    # Sets the headers and allows Last-Modified to be entered
    def _set_headers(self, header, **kwargs):
        self.send_response(header)
        etag = datetime.today().strftime(DATE_FORMAT)
        self.send_header("Content-Type", "json")
        self.send_header("ETag", etag)
        self.send_header("Last-Modified", kwargs.get("l_mod"))
        self.end_headers()

    # Gets the request body. Returns empty if None found
    def _get_body(self):
        try:
            body = self.rfile.read(int(self.headers.get("Content-Length")))
            return json.loads(body.decode("utf-8"))
        except json.decoder.JSONDecodeError:
            return {}

    # Tests if body_list has all of required_ist items
    def _all_list(self, body_list, required_list):
        return all(_params in body_list for _params in required_list)

    # Tests if body_list has any of required_ist items
    def _any_list(self, body_list, required_list):
        return any(_params in body_list for _params in required_list)

    # Handles all the create tasks
    def handle_create(self, body: dict):
        # Required parameters
        required_list = ["task_name", "description", "priority"]
        # Default property values
        default_properties = {"created": datetime.now().isoformat(), "last-modified": ""}

        if self._all_list(list(body.keys()), required_list):
            # Assign task_id, add properties to body and insert into table
            task = {"task_id": table.estimated_document_count() + 1}
            body.update({"properties": default_properties})
            task.update(body)
            insert = table.insert_one(task)

            # Return success headers
            self._set_headers(HTTPStatus.OK.real)
            self.wfile.write(json.dumps({"success": str(insert.inserted_id)}).encode("utf-8"))
        else:
            # If any pars missing return bad request
            self._set_headers(HTTPStatus.BAD_REQUEST.real)
            self.wfile.write(json.dumps(return_msg[str(HTTPStatus.BAD_REQUEST.real)]).encode("utf-8"))

    # Handles all the patch tasks
    def handle_patch(self, body: dict):
        try:
            task_id = int(self.path.split("/")[-1])
        except ValueError:
            task_id = -1
        # Columns that are able to be changed
        required_list = ["due_date", "priority"]

        if self._any_list(body, required_list) and task_id > 0:
            is_valid = True
            # Calculate current time of assumed new modification
            modified = datetime.now()
            # Get the currently last-modified time
            last_modified = table.find_one({"task_id": task_id})

            if last_modified is not None:
                last_modified = table.find_one({"task_id": task_id})["properties"]["last-modified"]

            # Ignore unmodified, validate last-modified value
            if last_modified != '' and last_modified is not None:
                last_modified = datetime.strptime(last_modified, DATE_FORMAT).isoformat()
                # Test if the last_modified time is more than assumed modify time
                # Prevent modification if true
                if last_modified > modified:
                    is_valid = False

            if is_valid:
                modified = modified.isoformat()
                updates = 0
                for par in required_list:
                    if body.get(par) is not None:
                        updates += table.update_many({"task_id": task_id},
                                                     {"$set": {
                                                         par: body[par],
                                                         "properties.last-modified": modified}}).modified_count
                # Update Last-Modified header
                # Return success header
                self._set_headers(HTTPStatus.OK.real, l_mod=modified)
                self.wfile.write(json.dumps({"updates": updates}).encode("utf-8"))
            else:
                # Return fail header
                self._set_headers(HTTPStatus.BAD_REQUEST.real)
                self.wfile.write(json.dumps(return_msg[str(HTTPStatus.BAD_REQUEST.real)]).encode("utf-8"))
        else:
            # Return fail header
            self._set_headers(HTTPStatus.BAD_REQUEST.real)
            self.wfile.write(json.dumps(return_msg[str(HTTPStatus.BAD_REQUEST.real)]).encode("utf-8"))

    # Handles all the get tasks
    def handle_get(self):
        # Get any specific task(s) searched for, handle different values received
        try:
            task_id = self.path.split("/")[-1]
            if "?" in task_id:
                task_id = task_id.split("?")[0]
                get = {"task_id": int(task_id)} if task_id != "tasks" else {}
            elif task_id != "tasks":
                get = {"task_id": int(task_id)}
            else:
                get = {}

            valid = True
        except ValueError:
            valid = False
            get = {}

        # sort_cols: Stores columns allowed to be sorted by
        # include: Specific fields to be included in query
        # sort: Stores the sort column and direction
        # page: Stores the pagination data
        # status: Stores if the tasks are valid or expired
        config = {"sort_cols": ["priority", "due_date"],
                  "include": {}, "sort": {},
                  "page": {"limit": 0, "offset": 0},
                  "status": -1}

        # Whether a sort function must happen
        is_sorted = False

        # Sort through the parameters and ensure they are valid
        if len(self.path.split("?")) > 1:
            # Get parameters and remove spaces/quotes characters
            params = [item.replace("%22", "").replace("%20", " ") for item in self.path.split("?")[1].split("&")]

            # Handle each different parameter
            for parm in params:
                key, value = parm.split("=")
                if key == "sort" and value in config["sort_cols"]:
                    config["sort"]["sort"] = value
                    is_sorted = True
                elif key == "order":
                    config["sort"]["order"] = (1 if value == "asc" else -1)
                elif key == "fields":
                    fields = value.split(",")
                    config["include"] = {key: 1 for key in fields}
                    if "_id" not in fields:
                        config["include"].update({"_id": 0})
                elif key == "limit":
                    config["page"]["limit"] = int(value)
                elif key == "offset":
                    config["page"]["offset"] = int(value)
                elif key == "status":
                    if value == "valid":
                        config["status"] = 1
                    elif value == "expired":
                        config["status"] = 0
                else:
                    # Invalid parameter detected return bad request
                    valid = False

        # Stores the found content
        content = []

        # If there are no invalid parameters found return the found tasks
        if valid:
            # Perform the find depending on criteria
            if len(config["sort"].keys()) == 2 and is_sorted:
                # Limited fields sorted
                if len(config["include"].keys()) != 0:
                    results = table.find(get, config["include"]).sort(config["sort"]["sort"], config["sort"]["order"])
                # All the fields sorted
                else:
                    results = table.find(get).sort(config["sort"]["sort"], config["sort"]["order"])
            else:
                # Limited fields unsorted
                if len(config["include"].keys()) != 0:
                    results = table.find(get, config["include"])
                # All fields unsorted
                else:
                    results = table.find(get)

            # Implement pagination and loop through items
            # READ: batch_size()
            for key in results.skip(config["page"]["offset"]).limit(config["page"]["limit"]):
                # Convert ObjectID to String
                do_add = True
                if config["include"].get("_id") != 0:
                    key["_id"] = str(key["_id"])

                # Add if due_date matches status
                if config["status"] > -1:
                    if key["due_date"] != '':
                        today = datetime.strptime(key["due_date"], TASK_DATE)
                        # if valid
                        if config["status"] == 1:
                            # if expired don't add
                            if today < datetime.today():
                                print("VALID")
                                do_add = False
                        # if expired
                        if config["status"] == 0:
                            # if expired don't add
                            if today > datetime.today():
                                print("EXPIRED")
                                do_add = False
                    # Add empty due_dates to valid list
                    else:
                        if config["status"] != 1:
                            do_add = False
                # Add to content
                if do_add:
                    content.append(key)

            self._set_headers(HTTPStatus.OK.real)
            self.wfile.write(json.dumps(content).encode("utf-8"))
        else:
            self._set_headers(HTTPStatus.BAD_REQUEST.real)
            self.wfile.write(json.dumps(return_msg[str(HTTPStatus.BAD_REQUEST.real)]).encode("utf-8"))

    # Handles all the delete tasks
    def handle_delete(self):
        # Delete the task
        try:
            task_id = int(self.path.split("/")[-1])
            deleted = table.delete_one({"task_id": task_id}).deleted_count
        except ValueError:
            deleted = 0
        self._set_headers(HTTPStatus.OK.real)
        self.wfile.write(json.dumps({"deleted": deleted}).encode("utf-8"))


# Create and run the http server and api
def run_server():
    # Server settings
    server_address = ('localhost', HTTP_PORT)
    httpd = HTTPServer(server_address, _RequestHandler)

    # Notify where running
    print('serving at http://%s:%d' % server_address)

    # Make it quit nicely
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Terminating Server")


# Create and connect to mongodb, returns the table
def create_db():
    # Connect to mongodb client
    mongo_client = pymongo.MongoClient(MONGO_CLIENT)
    # Create database
    client_database = mongo_client[MONGO_DATABASE]

    # Get the list of databases and required table
    db_list = client_database.list_collection_names()
    tbl = client_database[TABLE_NAME]

    # TO SKIP DATABASE POPULATION COMMENT FROM HERE #
    # Create the table if it does not exist and return the table
    if _gen_sample():
        if TABLE_NAME not in db_list:
            # Add the demo data to the database
            data = json.load(open("sample_data.json", "r"))
            data = [value for key, value in data.items()]
            tbl.insert_many(data)
        else:
            print("Database already exists")
    # UNTIL HERE. DATABASE POPULATION WILL BE SKIPPED #
    return tbl


# Get user input to determine if database must be created
def _gen_sample():
    _answer = input("Would you like to create sample data (y/n)")
    if _answer.upper() == "Y":
        return True
    elif _answer.upper() == "N":
        return False
    else:
        return _gen_sample()


if __name__ == '__main__':
    # Stores the table we will be editing
    table = create_db()
    # Prints table details
    print(table)
    run_server()
