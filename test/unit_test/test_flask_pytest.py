#
# ===============LICENSE_START=======================================================
# Acumos
# ===================================================================================
# Copyright (C) 2018 AT&T Intellectual Property. All rights reserved.
# ===================================================================================
# This Acumos software file is distributed by AT&T
# under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# This file is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============LICENSE_END=========================================================
import pytest
import json
import os
import zipfile
import h2o

from h2o.estimators.gbm import H2OGradientBoostingEstimator
from microservice_flask import app, initialize_app

model_cache_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'model_cache_dir_test')
os.environ['model_cache_dir'] = model_cache_dir
BASE_URL = 'http://127.0.0.1:8061/v2/'


@pytest.fixture(scope='session')
def test_client():
    testing_client = app.test_client()
    initialize_app(testing_client)
    testing_client.testing = True

    # This code generates a h2o model to be used for running predictions
    #   against the iris dataset
    h2o.init()
    training_frame = h2o.import_file(os.path.join(model_cache_dir, 'iris.csv'))

    estimator = H2OGradientBoostingEstimator()
    estimator.train(training_frame=training_frame,
                    x=['sepal_length', 'sepal_width', 'petal_length', 'petal_width'],
                    y='species')

    model_file = estimator.download_mojo(path=model_cache_dir, get_genmodel_jar=True,
                                         genmodel_name='h2o-genmodel.jar')

    model_dir = os.path.join(model_cache_dir, '1_0')

    with zipfile.ZipFile(os.path.join(model_dir, 'h2o'), 'w') as zip:
        zip.write(model_file, os.path.basename(model_file))
        zip.write(os.path.join(model_cache_dir, 'h2o-genmodel.jar'), 'h2o-genmodel.jar')

    return testing_client


# @api.route('/statuses/<string:statusKey>')
def test_get_status(test_client):
    response = test_client.get(BASE_URL + 'statuses/' + 'dummyStatusKey')
    assert response.status_code == 501
    assert json.loads(response.get_data())['message'] == 'Method not yet implemented'


# @api.route('/asyncPredictions')
def test_get_asyncPredictions(test_client):

    body = {
        'readDatasetKey': 'm092XX_1530026027076_855258959068650452',
        'writeDatasetKey': 'm092XX_1530026122667_683407214566211287'
    }

    request_headers = {
        'content-type': 'application/json',
        'accept': 'application/json',
        'ACUMOS-ModelVersion': '1_0',
        'ACUMOS-ModelKey': 'h2o',
        'ACUMOS-MessageId': 'rh1832_callback_id1',
        'ACUMOS-ReturnURL': 'http://localhost:8123/v2/callback'
    }

    response = test_client.post(BASE_URL + 'asyncPredictions', data=json.dumps(body), headers=request_headers)
    assert response.status_code == 501
    assert json.loads(response.get_data())['message'] == 'Method not yet implemented'


# @api.route('/syncPredictions')
def test_get_syncPredictions(test_client):

    body = '''
        Id,Sepal_Length,Sepal_Width,Petal_Length,Petal_Width
        record-001,7.0,3.2,4.7,1.4
        record-002,7.0,3.0,5.0,1.0
        record-003,6.0,3.2,4.7,1.4
        '''

    request_headers = {
        'content-type': 'text/csv',
        'accept': 'text/csv',
        'ACUMOS-ModelVersion': '1_0',
        'ACUMOS-ModelKey': 'h2o'
    }

    response = test_client.post(BASE_URL + 'syncPredictions', data=body, headers=request_headers)
    assert response.status_code == 200
    assert len(response.get_data()) > 5
