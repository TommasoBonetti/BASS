import logging
import socket
import os
import subprocess
from threading import Timer
import tempfile
import datetime
import shutil
import errno

from flask import Flask, request, jsonify, make_response, send_file

PREFIX = "/home"
LOGS_DIR = "/logs"
BINDIFF_DIRECTORY = "/opt/zynamics/BinDiff"
FILE_EXTENSIONS_TO_CLEAN = ['id0', 'id1', 'id2', 'idb', 'i64', 'nam', 'til']

logging.basicConfig(level='INFO', format='%(asctime)s [%(levelname)s] %(message)s',
                    filename='%s/%s-ida-service.log' % (LOGS_DIR, socket.gethostname()),
                    filemode='a')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

def sanitize_filename(filename):
    return filename.replace("/", "_").replace(":", "_")

def check_call(cmd, cwd = os.getcwd(), timeout = None, env = os.environ):
    proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, env = env, cwd = cwd)
    if timeout:
        timer = Timer(timeout, proc.kill)
        timer.start()
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise OSError(proc.returncode, "Subprocess returned error code")

@app.route('/bindiff/export', methods = ['POST'])
def bindiff_export():
    """
    Run the IDA Pro autoanalysis on the input file and export a BinExport database.
    :param input: The input file
    :return: Status code 200 and a JSON object containing the output database
        name in key 'output', or status code 422 on invalid parameters, 408 on
        timeout or 500 on other errors.
    """
    logger.info("bindiff_export called")

    directory = None
    try:
        directory = tempfile.mkdtemp()
        if len(request.files) != 1:
            return make_response(jsonify(error = "Missing file parameter"), 422)

        filename, file_ = request.files.items()[0]
        input_ = os.path.join(directory, sanitize_filename(filename))
        file_.save(input_)

        output = os.path.join(directory, "output.BinExport")

        timeout = request.form.get('timeout', None)
        is_64_bit = request.form.get('is_64_bit', True)
        cmd = ["/ida/idal64" if is_64_bit else "/ida/idal", "-S%s/packages/bindiff/ida/export_bindiff.py \"%s\"" % (PREFIX, output), "-B", input_]
        env = os.environ.copy()
        env["TVHEADLESS"] = "true"
        env["IDALOG"] = os.path.join(LOGS_DIR, datetime.datetime.strftime(datetime.datetime.now(), "ida_%Y-%m-%d_%H-%M-%S.%f.log"))
        logger.info("Executing command %s, log output is in '%s'", "".join("'%s'" % x for x in cmd), env["IDALOG"])
        try:
            check_call(cmd, timeout = timeout, env = env)
        except OSError as err:
            if err.errno == -9:
                return jsonify(error = "Program execution timed out"), 408
            else:
                return jsonify(error = "Program execution failed with error %d" % err.errno), 500

        logger.info("Command completed successfully")
        return send_file(open(output, "rb"), as_attachment = True, attachment_filename = "%s.BinExport" % filename, mimetype = "application/binary")
    finally:
        if directory is not None:
            shutil.rmtree(directory)

@app.route('/bindiff_pickle/export', methods = ['POST'])
def bindiff_pickle_export():
    """
    Run the IDA Pro autoanalysis on the input file and export a BinExport database.
    :param input: The input file
    :return: Status code 200 and a JSON object containing the output database
        name in key 'output', or status code 422 on invalid parameters, 408 on
        timeout or 500 on other errors.
    """
    logger.info("bindiff_pickle_export called")

    directory = None
    try:
        directory = tempfile.mkdtemp()
        if len(request.files) != 1:
            return make_response(jsonify(error = "Missing file parameter"), 422)

        filename, file_ = request.files.items()[0]
        input_ = os.path.join(directory, sanitize_filename(filename))
        file_.save(input_)

        output_binexport = os.path.join(directory, "output.BinExport")
        output_pickle = os.path.join(directory, "output.pickle")

        timeout = request.form.get('timeout', None)
        is_64_bit = request.form.get('is_64_bit', True)
        cmd = ["/ida/idal64" if is_64_bit else "/ida/idal", "-S%s/packages/bindiff/ida/export_bindiff_pickle.py \"%s\" \"%s\"" % (PREFIX, output_binexport, output_pickle), "-B", input_]
        env = os.environ.copy()
        env["TVHEADLESS"] = "true"
        env["IDALOG"] = os.path.join(LOGS_DIR, datetime.datetime.strftime(datetime.datetime.now(), "ida_%Y-%m-%d_%H-%M-%S.%f.log"))
        logger.info("Executing command %s, log output is in '%s'", "".join("'%s'" % x for x in cmd), env["IDALOG"])
        try:
            check_call(cmd, timeout = timeout, env = env)
        except OSError as err:
            if err.errno == -9:
                return jsonify(error = "Program execution timed out"), 408
            else:
                return jsonify(error = "Program execution failed with error %d" % err.errno), 500

        logger.info("Command completed successfully")
        output_tar = os.path.join(directory, "output.tar.gz")
        subprocess.check_call(["tar", "czf", output_tar, os.path.relpath(output_binexport, directory), os.path.relpath(output_pickle, directory)], cwd = directory)
        return send_file(open(output_tar, "rb"), as_attachment = True, attachment_filename = "%s.tar.gz" % filename, mimetype = "application/gzip")
    finally:
        if directory is not None:
            shutil.rmtree(directory)

@app.route('/pickle/export', methods = ['POST'])
def pickle_export():
    """
    Run the IDA Pro autoanalysis on the input file and export a BinExport database.
    :param input: The input file
    :return: Status code 200 and a JSON object containing the output database
        name in key 'output', or status code 422 on invalid parameters, 408 on
        timeout or 500 on other errors.
    """
    logger.info("bindiff_export called")

    directory = None
    try:
        directory = tempfile.mkdtemp()
        if len(request.files) != 1:
            return make_response(jsonify(error = "Missing file parameter"), 422)

        filename, file_ = request.files.items()[0]
        input_ = os.path.join(directory, sanitize_filename(filename))
        file_.save(input_)

        output = os.path.join(directory, "output.pickle")

        timeout = request.form.get('timeout', None)
        is_64_bit = request.form.get('is_64_bit', False)
        cmd = ["/ida/idal64" if is_64_bit else "/ida/idal", "-S%s/packages/bindiff/ida/export_pickle.py \"%s\"" % (PREFIX, output), "-B", input_]
        env = os.environ.copy()
        env["TVHEADLESS"] = "true"
        env["IDALOG"] = os.path.join(LOGS_DIR, datetime.datetime.strftime(datetime.datetime.now(), "ida_%Y-%m-%d_%H-%M-%S.%f.log"))
        logger.info("Executing command %s, log output is in '%s'", "".join("'%s'" % x for x in cmd), env["IDALOG"])
        try:
            check_call(cmd, timeout = timeout, env = env)
        except OSError as err:
            if err.errno == -9:
                return jsonify(error = "Program execution timed out"), 408
            else:
                return jsonify(error = "Program execution failed with error %d" % err.errno), 500

        logger.info("Command completed successfully")
        return send_file(open(output, "rb"), as_attachment = True, attachment_filename = "%s.pickle" % filename, mimetype = "application/binary")
    finally:
        if directory is not None:
            shutil.rmtree(directory)
        
@app.route('/bindiff/compare', methods = ['GET', 'POST'])
def bindiff_compare():
    logger.info("bindiff_compare called")

    input_dir = tempfile.mkdtemp()
    output_dir = tempfile.mkdtemp()
    try:
        primary = os.path.join(input_dir, "primary")
        secondary = os.path.join(input_dir, "secondary")
        try:
            request.files["primary"].save(primary)
            request.files["secondary"].save(secondary)
        except KeyError:
            return make_response(jsonify(error="Missing parameter 'primary' or 'secondary'"), 422)

        timeout = request.form.get('timeout', None)

        cmd = [os.path.join(BINDIFF_DIRECTORY, "bin/differ"), "--primary", primary, "--secondary", secondary, "--output_dir", output_dir]
        logger.info("Executing %s", " ".join("'%s'" % x for x in cmd))
        check_call(cmd, cwd = output_dir, timeout = timeout)
        db_path = [os.path.join(output_dir, x) for x in os.listdir(output_dir)]
        if len(db_path) != 1:
            return make_response(jsonify(error = "BinDiff generated 0 or several output files"), 500)
        return send_file(open(db_path[0], "rb"), as_attachment = True, attachment_filename = "BinDiff.sqlite3", mimetype = "application/binary")
    except OSError as err:
        if err.errno == -9:
            return make_response(jsonify(error = "Program execution timed out"), 408)
        else:
            return make_response(jsonify(error = "Program execution failed with error %d" % err.errno), 500)
    finally:
        shutil.rmtree(input_dir)
        shutil.rmtree(output_dir)

if __name__ == '__main__':
    app.config['DEBUG'] = True
    app.run()
