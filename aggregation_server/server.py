from flask import Flask, request, jsonify
from uuid import uuid4 
from subprocess import Popen, PIPE
from requests import post
from os import path, walk, listdir
from multiprocessing import Lock, Manager
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

app = Flask(__name__)
app.config.from_pyfile('config.py')
lock = Lock()
manager = Manager()

print(app.config["PRIVATE_ENC_KEY"], "rb")
with open(app.config["PRIVATE_ENC_KEY"], "rb") as key_file:
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=None,
        backend=default_backend()
    )

unconfirmed_uploads = manager.dict()
current_batch = manager.list()
current_file = None

@app.route('/')
def hello():
    return 'Hello'

def check_file(file):
    if file is None:
        return False
    with lock:
        with open(current_file, "r") as f:
            num_lines = sum(1 for _ in f)
    # +1 for the header
    if num_lines > app.config["MAX_FILE_SIZE"]:
        return False
    return True

def new_file():
    global current_file
    _, _, files = next(walk(app.config["OUTPUT_FILE_PATH"]))
    index = len(files) - 1

    current_file = path.join(app.config["OUTPUT_FILE_PATH"], 
                            app.config["OUTPUT_FILE_PREFIX"] + str(index) + ".csv")
    
    if path.exists(current_file):
        if check_file(current_file):
            return
    index = len(files)
    current_file = path.join(app.config["OUTPUT_FILE_PATH"], 
                            app.config["OUTPUT_FILE_PREFIX"] + str(index) + ".csv")
    if not path.exists(current_file):
        with lock:
            with open(current_file, "a") as f:
                f.write("id_," + ",".join(app.config["DATASTORE_FIELD_NAMES"]) + "\n")
        

@app.route('/confirmupload', methods=['POST'])
def handle_confirm_upload():
    expected_keys = ["id", "token"]

    for key in expected_keys:
        if not key in request.json.keys():
            return jsonify({"error": f'no "{key}" field in request'}), 400
        
    if request.json["token"] != app.config["COLLECTION_TOKEN"]:
        return jsonify({"error": "invalid token"}), 402
    
    if not request.json["id"] in unconfirmed_uploads.keys():
        return jsonify({"error": "Unknown id"}), 404

    if request.json["id"] in unconfirmed_uploads.keys():
        write_upload(request.json["id"])
        return jsonify({"id":request.json["id"]}), 200
    
    return jsonify({"error": "Unknown error"}), 500

def write_upload(id):
    print(f"Writing id {id}...")
    upload = unconfirmed_uploads.pop(id)
    upload_list = []
    # decrypt upload
    if app.config["ENCRYPT"]:
        for key in app.config["DATASTORE_FIELD_NAMES"]:
            enc = bytes.fromhex(str(upload[key]))
            try:
                int_measurement = int(private_key.decrypt(
                    enc,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None)
                ).decode())
                assert int_measurement >= 0 and int_measurement.bit_length() <= 32
                upload_list.append(str(int_measurement))
            except Exception as e:
                print(e)
                return
    else:
        for key in app.config["DATASTORE_FIELD_NAMES"]:
            try:
                int_measurement = int(upload[key])
                assert int_measurement >= 0 and int_measurement.bit_length() <= 32
                upload_list.append(str(int_measurement))
            except Exception as e:
                print(e)
                return
    current_batch.append(id + "," + ",".join(upload_list) + "\n")

def write_batch():
    global current_batch
    current_batch.sort()
    for upload in current_batch:
        if not check_file(current_file):
            new_file()
        with lock:
            with open(current_file, "a") as f:
                f.write(upload)
    for i in current_batch:
        current_batch.remove(i)

@app.route('/upload', methods=['POST'])
def handle_upload():
    expected_keys = ["measurements"]

    for key in expected_keys:
        if not key in request.json.keys():
            return jsonify({"error": f'no "{key}" field in request'}), 400

    if not isinstance(request.json["measurements"], dict):
        return jsonify({"error": f'measurements must be a dict'}), 400

    for key in app.config["DATASTORE_FIELD_NAMES"]:
        if not key in request.json["measurements"].keys():
            return jsonify({"error": f'Expected measurement "{key}" not in request'}), 400
    
    measurements_parsed = {}
    for measurement in request.json["measurements"].keys():
        try:
            enc_measurement = request.json["measurements"][measurement]
            # decrypt measurement
            dec_measurerment = enc_measurement
            # # assert its a correct 32 bit int
            # int_measurement = (dec_measurerment)
            # assert int_measurement >= 0 and int_measurement.bit_length() <= 32

            measurements_parsed[measurement] = dec_measurerment
        except:
            return jsonify({"error": f'Invalid measurement "{dec_measurerment}"'}), 400
    # if there is no id, we are the master server
    # this means we need to wait for confirmation request 
    # from helper server that they got the upload as well
    if not "id" in request.json.keys():
        id = str(uuid4())
        unconfirmed_uploads[id] = measurements_parsed
        return jsonify({"id": id}), 200
    else:
        id = request.json["id"]
        # we dont wait for confirmation so we can close the connection
        # with client as soon as possible
        unconfirmed_uploads[id] = measurements_parsed
        res = post(f'http://{app.config["PARTNER_SERVER_IP"]}:{app.config["PARTNER_SERVER_PORT"]}/confirmupload', json={"id": id, "token": app.config["HELPER_SERVER_TOKEN"]})
        if res.status_code == 200:
            write_upload(id)
        return jsonify({"id": id}), 200

@app.route('/collecthelper', methods=['POST'])
def handle_start_helper():
    expected_keys = ["token", "metric"]

    for key in expected_keys:
        if not key in request.json.keys():
            return jsonify({"error": f'no "{key}" field in request'}), 400
        
    if request.json["token"] != app.config["COLLECTION_TOKEN"]:
        return jsonify({"error": "invalid token"}), 402
    
    possible_metrics = app.config["METRIC_NAMES"]
    if not request.json["metric"] in possible_metrics:
        return jsonify({"error": f'invalid metric "{request.json["metric"]}"'})
    
    write_batch()
    print(f"starting metric {request.json['metric']}...")

    files = [filename for filename in listdir(app.config["OUTPUT_FILE_PATH"]) 
             if path.isfile(path.join(app.config["OUTPUT_FILE_PATH"], filename))]

    if files == []:
        return jsonify({"error": "no files to collect"}), 404

    output_files = ["output_" + str(i) for i in range(len(files))]

    proc = Popen(["demographicapp", "-server_ip", f'{app.config["PARTNER_SERVER_IP"]}',
           "-port", '10000', "-party", "2", "-concurrency", "64",
           "-input_directory", app.config["OUTPUT_FILE_PATH"],
           "-input_filenames", f'{",".join(files)}', 
           "-output_directory", "aggregation_output",
           "-output_filenames", f'{",".join(output_files)}',
           f'-{request.json["metric"]}'])
    
    #proc.wait(timeout=10)

    return "Aggregation job started"

@app.route('/collect', methods=['POST'])
def handle_collection():
    expected_keys = ["token", "metric"]

    for key in expected_keys:
        if not key in request.json.keys():
            return jsonify({"error": f'no "{key}" field in request'}), 400
        
    if request.json["token"] != app.config["COLLECTION_TOKEN"]:
        return jsonify({"error": "invalid token"}), 402
    
    possible_metrics = app.config["METRIC_NAMES"]
    if not request.json["metric"] in possible_metrics:
        return jsonify({"error": f'invalid metric "{request.json["metric"]}"'})
    
    write_batch()

    files = [filename for filename in listdir(app.config["OUTPUT_FILE_PATH"]) 
             if path.isfile(path.join(app.config["OUTPUT_FILE_PATH"], filename))]

    if files == []:
        return jsonify({"error": "no files to collect"}), 404

    # start helper
    helper_json = {"metric": request.json["metric"], "token": app.config["HELPER_SERVER_TOKEN"]}
    res = post(f'http://{app.config["PARTNER_SERVER_IP"]}:{app.config["PARTNER_SERVER_PORT"]}/collecthelper', json=helper_json)   
    
    if res.status_code != 200:
        print(res.json)
        return jsonify({"error": "error starting helper"}), 500
    print(f"starting metric {request.json['metric']}...")

    output_files = ["output_" + str(i) for i in range(len(files))]

    proc = Popen(["demographicapp", "-server_ip", f'127.0.0.1',
           "-port", '10000', "-party", "1", "-concurrency", "64",
           "-input_directory", app.config["OUTPUT_FILE_PATH"],
           "-input_filenames", f'{",".join(files)}', 
           "-output_directory", "aggregation_output",
           "-output_filenames", f'{",".join(output_files)}',
           f'-{request.json["metric"]}'])

    proc.wait()

    output = {}
    for filename in output_files:
        filepath = path.join("aggregation_output", filename)
        output[filename] = {}
        with open(filepath, "r") as f:
            for line in f:
                key, value = line.split(":")
                key = key.strip()
                value = value.strip()
                output[filename][key] = value
    return jsonify(output), 200

if __name__=="__main__":
    app.run()