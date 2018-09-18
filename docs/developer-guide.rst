.. ===============LICENSE_START=======================================================
.. Acumos CC-BY-4.0
.. ===================================================================================
.. Copyright (C) 2017-2018 AT&T Intellectual Property. All rights reserved.
.. ===================================================================================
.. This Acumos documentation file is distributed by AT&T
.. under the Creative Commons Attribution 4.0 International License (the "License");
.. you may not use this file except in compliance with the License.
.. You may obtain a copy of the License at
..
..      http://creativecommons.org/licenses/by/4.0
..
.. This file is distributed on an "AS IS" BASIS,
.. WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. See the License for the specific language governing permissions and
.. limitations under the License.
.. ===============LICENSE_END=========================================================

============================================
Acumos H2O Model Runner Python Developer Guide
============================================

This predictor will run predictions for H2O POJO (Non compiled Java code) as well as MOJO (Compiled jars) models.  This service has a dependency to model-management to download the models.  AsyncPredictions and status methods are yet to be implemented in this version.  All the model runners follow a similar design pattern in that the expose the 3 endpoints asyncpredictions, syncpredictions and status.

Running this predictor in Windows requires changing the classpath argument as follows however it is assumed to be running on a *nix machine.

h2opredictordevelopment/predictor/h2o/wrapper.py

From
    classpath_arg = '.;./' + jar_file

To
        classpath_arg = '' + jar_file

The main class to start this service is /h2o-model-runner/microservice_flask.py

The command line interface gives options to run the application.   Type help for a list of available options.   
> python microservice_flask.py  help
usage: microservice_flask.py [-h] [--host HOST] [--settings SETTINGS]  [--port PORT]

By default without adding arguments the swagger interface should be available at: http://localhost:8061/v2/

 

Sample model creation
=====================

This is the R Script can generate both H2O and POJO models.   The below sample uses the iris dataset that may be found anywhere online or use the one that is built into R.

.. code:: bash

    $ library(h2o)
    $ h2o.init()
    $ 
    $ iris.hex <- h2o.importFile("iris.csv")
    $ iris.gbm <- h2o.gbm(y="species", training_frame=iris.hex, model_id="irisgbm")
    $ h2o.download_pojo(model = iris.gbm, path="/home/project/h2o",  get_jar = TRUE)
    $ h2o.download_mojo(model=iris.gbm, path="/home/project/h2o", get_genmodel_jar=TRUE)


Testing
=======

The only prerequisite for running testing is installing python and tox.   It is recommended to use a virtual environment for running any python application.  If using a virtual environment make sure to run “pip install tox” to install it

We use a combination of ``tox``, ``pytest``, and ``flake8`` to test
``h20-model-runner``. Code which is not PEP8 compliant (aside from E501) will be
considered a failing test. You can use tools like ``autopep8`` to
“clean” your code as follows:

.. code:: bash

    $ pip install autopep8
    $ cd h2o-model-runner
    $ autopep8 -r --in-place --ignore E501 acumo_h2o-model-runner/ test/

Run tox directly:

.. code:: bash

    $ cd h2o-model-runner
    $ tox

You can also specify certain tox environments to test:

.. code:: bash

    $ tox -e py34  # only test against Python 3.4
    $ tox -e flake8  # only lint code

And finally, you can run pytest directly in your environment *(recommended starting place)*:

.. code:: bash

    $ pytest
    $ pytest -s   # verbose output
