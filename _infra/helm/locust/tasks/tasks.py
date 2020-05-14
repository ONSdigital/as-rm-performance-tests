from locust import HttpLocust, TaskSet, task, events, between
import datetime
import sys
import os
import json
import requests
import logging
import csv
from functools import partial

survey_id = '02b9c366-7397-42f7-942a-76dc5876d86d'
form_type = '0001'
eq_id = '2'
period = '1806'
logger = logging.getLogger()

# Load data for tests
def load_data():
    auth = (os.getenv('SECURITY_USER_NAME'), os.getenv('SECURITY_USER_PASSWORD'))

    load_collection_exercises(auth)

    logger.info('Uploading eQ collection instrument', extra={'survey_id':survey_id, 'form_type':form_type})
    url = f"{os.getenv('COLLECTION_INSTRUMENT')}/collection-instrument-api/1.0.2/upload"

    classifiers = {
        "form_type": form_type,
        "eq_id": eq_id
    }

    params = {
        "classifiers": json.dumps(classifiers),
        "survey_id": survey_id
    }

    response = requests.post(url=url, auth=auth, params=params)

    logger.info('Executing collection exercise', extra={'survey_id':survey_id, 'period':period, 'ci_type':'eQ'})

# Collection exercise loading
def load_collection_exercises(auth):
    config = json.load(open("locust-tasks/collection-exercise-config.json"))
    input_files = config['inputFiles']
    column_mappings = config['columnMappings']
    url = f"{os.getenv('COLLECTION_EXERCISE')}/collectionexercises"

    row_handler = partial(post_collection_exercise, url=url, auth=auth)
    
    logger.info('Posting collection exercises')
    process_files(input_files, row_handler, column_mappings)

def post_collection_exercise(data, url, auth):
    response = requests.post(url, json=data, auth=auth, verify=False)

    status_code = response.status_code
    detail_text = response.text if status_code != 201 else ''

    logger.info("%s <= %s (%s)", status_code, data, detail_text)

def map_columns(column_mappings, row):
    new_row = dict()
    for key, value in row.items():
        try:
            if key and value:
                new_row[column_mappings[key] if column_mappings[key] else key] = value
        except KeyError:
           new_row[key] = value 
    return new_row

def process_file(filename, row_handler, column_mappings):
    with open(filename) as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            new_row = map_columns(column_mappings, row)

            if new_row:
                row_handler(data=new_row)

def process_files(file_list, row_handler, column_mappings):
    for filename in file_list:
        process_file(filename, row_handler, column_mappings)

# This will only be run on Master and should be used for loading test data
if '--master' in sys.argv:
  load_data()

class FrontstageTasks(TaskSet):
  @task(1)
  def status(self):
    response = self.client.get("/sign-in")

class FrontstageLocust(HttpLocust):
  task_set = FrontstageTasks
  wait_time = between(5, 15)
