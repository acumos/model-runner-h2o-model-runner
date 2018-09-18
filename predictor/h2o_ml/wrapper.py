#!/usr/bin/env python3
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
from enum import Enum, auto
from shutil import copyfile
from zipfile import BadZipFile

import logging
import os
import subprocess
import tempfile
import zipfile

logger = logging.getLogger(__name__)


# TODO (pk9069):
# DANGER DANGER DANGER: here are the implementation notes and limitations:
# the size limitations set on the JVM are currently fixed; more investigation is needed into making them configurable.
# The model is currently compiled on-demand every single time, which means this can be optimized by caching the build.
# The PredictCSV.java currently requires files as input arguments, so there's some file overhead that might be optimized
# away.


class ModelFormat(Enum):
    MOJO = auto()
    POJO = auto()
    MOJO_WORD2VEC = auto()


class H2OException(Exception):
    pass


class H2OWrapper():

    # Placeholders for files generated inside of temporary directory
    INPUT_FILE_NAME = 'input.csv'
    OUTPUT_FILE_NAME = 'output.csv'
    MODEL_FILE_NAME = 'model.zip'
    BUILD_TARGET_DIR = 'target'
    PREDICT_WRAPPER_TEMPLATE = 'PredictCsv.java'
    WORD2VEC_TEMPLATE = 'Word2VecMain.java'

    def __init__(self):
        pass

    def _extract_model(self, model_zip_path, extract_dir):
        logger.debug(f"model_zip_path: {model_zip_path}")
        with zipfile.ZipFile(model_zip_path, "r") as zip_ref:
            logger.debug(f"Extracting file to directory {extract_dir}")
            try:
                zip_ref.extractall(extract_dir)
            except BadZipFile:
                raise H2OException("Model selected must be a zip file.")
            dirfiles = os.listdir(extract_dir)
            model_format = None
            model_file = None
            jar_file = None
            for dirfile in dirfiles:
                if dirfile.endswith('.zip'):
                    model_file = dirfile
                    if 'word2vec' in dirfile.lower():
                        model_format = ModelFormat.MOJO_WORD2VEC
                    else:
                        model_format = ModelFormat.MOJO
                elif model_format is None and dirfile.endswith('.java'):
                    model_file = dirfile
                    model_format = ModelFormat.POJO
                elif dirfile.endswith('.jar'):
                    jar_file = dirfile
            if jar_file is None:
                raise H2OException("Jar file (h2o-genmodel.jar) is required as part of extracted zip model file")
            if model_format is None:
                raise H2OException(
                    "Either POJO Java file or MOJO zipped file is required as part of extracted zip model file"
                )
            return model_file, jar_file, model_format

    def _run_command(self, command, working_dir):
        cwd = working_dir
        logger.debug('cwd: %s', cwd)
        logger.debug('command: %s', command)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        stdout, stderr = process.communicate()
        stdout = stdout.decode()
        logger.debug(f'stdout: {stdout}')
        if process.returncode != 0:
            raise H2OException(stderr.decode())
        return stdout

    # TODO (pk9069): make size configurable
    def _compile_model(self, java_file, jar_file, working_dir):
        command = ['javac', '-cp', jar_file, '-J-Xmx2g', java_file]
        self._run_command(command, working_dir)

    def _run_predict_csv(self, java_file, jar_file, input_path, output_path, working_dir):
        model_name = java_file.split('.java')[0]
        classpath_arg = '.:./' + jar_file
        command = [
            'java', '-ea', '-cp', classpath_arg, '-Xmx4g', '-XX:ReservedCodeCacheSize=512m',
            'hex.genmodel.tools.PredictCsv', '--header', '--decimal', '--pojo', model_name, '--input', input_path,
            '--output', output_path
        ]
        self._run_command(command, working_dir)

    # TODO (pk9069): combine these predictor methods later
    def _run_predict_pojo_csv(self, java_file, jar_file, input_path, output_path, working_dir):
        model_name = java_file.split('.java')[0]
        classpath_arg = '.:./' + jar_file
        command = [
            'java', '-ea', '-cp', classpath_arg, '-Xmx4g', '-XX:ReservedCodeCacheSize=512m',
            'hex.genmodel.tools.PredictCsv', '--header', '--decimal', '--pojo', model_name, '--input', input_path,
            '--output', output_path
        ]
        self._run_command(command, working_dir)

    def _run_predict_mojo_csv(self, zip_name, jar_file, input_path, output_path, working_dir):
        classpath_arg = '.:./' + jar_file
        command = [
            'java', '-ea', '-cp', classpath_arg, '-Xmx4g', '-XX:ReservedCodeCacheSize=512m',
            'hex.genmodel.tools.PredictCsv', '--header', '--decimal', '--mojo', zip_name, '--input', input_path,
            '--output', output_path
        ]
        self._run_command(command, working_dir)

    def _run_predict_mojo_word2vec_csv(self, zip_name, jar_file, input_path, output_path, working_dir):
        classpath_arg = '.:./' + jar_file
        command = [
            'java', '-ea', '-cp', classpath_arg, '-Xmx4g', '-XX:ReservedCodeCacheSize=512m', 'Word2VecMain', zip_name,
            input_path, output_path
        ]
        self._run_command(command, working_dir)

    def run_prediction(self, model_contents, dataset_contents, properties_path):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, H2OWrapper.MODEL_FILE_NAME)
            with open(model_path, 'wb') as model_file:
                model_file.write(model_contents)
            extract_dir = os.path.join(tmpdir, H2OWrapper.BUILD_TARGET_DIR)
            if not os.path.exists(extract_dir):
                os.makedirs(extract_dir)
            model_file, jar_file, model_format = self._extract_model(model_path, extract_dir)

            if model_format == ModelFormat.POJO:
                # TODO (pk9069): optimize compilation to compile only during the first execution
                self._compile_model(model_file, jar_file, extract_dir)
            elif model_format == ModelFormat.MOJO_WORD2VEC:
                template_file = os.path.join(properties_path, H2OWrapper.WORD2VEC_TEMPLATE)
                destination_file = os.path.join(extract_dir, H2OWrapper.WORD2VEC_TEMPLATE)
                copyfile(template_file, destination_file)
                self._compile_model(H2OWrapper.WORD2VEC_TEMPLATE, jar_file, extract_dir)

            input_path = os.path.join(extract_dir, H2OWrapper.INPUT_FILE_NAME)
            output_path = os.path.join(extract_dir, H2OWrapper.OUTPUT_FILE_NAME)
            logger.debug(f'input_path {input_path}')
            logger.debug(f'output_path {output_path}')
            with open(input_path, 'w') as dataset_file:
                dataset_file.write(dataset_contents)
            if model_format == ModelFormat.POJO:
                self._run_predict_pojo_csv(model_file, jar_file, input_path, output_path, extract_dir)
            elif model_format == ModelFormat.MOJO:
                self._run_predict_mojo_csv(model_file, jar_file, input_path, output_path, extract_dir)
            elif model_format == ModelFormat.MOJO_WORD2VEC:
                self._run_predict_mojo_word2vec_csv(model_file, jar_file, input_path, output_path, extract_dir)
            with open(output_path) as results:
                return results.read()
