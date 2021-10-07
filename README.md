# Tasks TODO API

## About Program:

Author: Shaun Dumas

Language: Python

Database: MongoDB

## What I learnt while completing this project:
- How an API works in the real world and why it is useful
- About REST standards
- Usefulness of headers (ETag, Last-Modified, Content-Type)
- Installing, configuring, reading and writing to/from MongoDB
- Navigating and using Postman
- New Terminology

## Implemented Functionality:
1. A user must be able to create a new to-do with a description, a priority and an optional deadline
2. A user must be able to update an existing to-do
3. A user must be able to delete an existing to-do
4. A user must be able to retrieve all to-dos
5. A user must be able to sort to-dos by priority or by deadline, both ascending and descending
6. A user must be able to limit the fields returned
7. A user must be able to paginate to-dos
8. A user must be able to query to-dos by status

## Satisfied Requirements:
1. The API must conform to the standards and constraints of REST as closely as possible
2. The API must use JSON for requests and responses
3. The API should implement optimistic concurrency control (uses last-modified header and stores in db)
4. Frameworks are not allowed

## Missing Requirements:
1. The API must be asynchronous and non-blocking

## Using the API:
| FUNCTION | USAGE | DESCRIPTION |
|----------|-------|-------------|
|POST|/api/tasks/task|Creates a new task in database. Fetches values from body|
|GET|/api/tasks/<task_id>|Fetches a specific task|
|GET|/api/tasks|Fetches all the tasks in the database|
|PATCH|/api/tasks/<task_id>|Patches the selected task|
|DELETE|/api/tasks/<task_id>|Deletes the selected task|

|FUNCTION|KEYS|USAGE|
|--------|----|------|
|GET|fields|field1,field2,...|
|GET|status|valid/expired|
|GET|limit|(n) documents|
|GET|offset|(n) skipped documents|
|GET|sort&order|[priority/due_date]&[asc/...]|

|FUNCTION|VALID BODY EXAMPLE|
|--------|------------------|
|POST|{"task_name":"Buy chocolate","description":"You need to go to the shop and buy chocolate","priority":1,"due_date":"2021-11-06"}|
|PATCH|{"priority":3}|
|PATCH|{"due_date":3}|

[^1]: POST - due_date optional, format: YYYY-MM-DD

[^1]: PATCH - due_date format: YYYY-MM-DD

---