import csv
import requests
import argparse
from os import urandom
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def read_csv_with_header(file_path):
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header line
        data = []
        for row in reader:
            d = dict(zip(header, row))
            del d["id_"]
            data.append(d)
            # Process the data for each row
    return data

def upload_single(data: dict, url: str):
    response = requests.post(url, json=data)
    if response.status_code != 200:
        print(f"Error uploading data: {response.json()['error']}")
        return None
    return response.json()["id"]

def upload_all(share1: list, share2: list, url_master: str, url_helper: str):
    ids = []
    for i in range(len(share1)):
        json = {"measurements": share1[i]}
        id = upload_single(json, url_master)
        if id is None:
            return ids
        json = {"measurements": share2[i], "id": id}
        new_id = upload_single(json, url_helper)
        if new_id is None:
            return ids
        ids.append(id)
    return ids

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('data_filepath', type=str, help='Path to the data file')
    parser.add_argument('master_url', type=str, help='Master URL')
    parser.add_argument('helper_url', type=str, help='Helper URL')
    parser.add_argument('pk_helper', type=str, help='Helper public encryption key')
    parser.add_argument('pk_master', type=str, help='Master public encryption key')
    parser.add_argument('--noencrypt', action=argparse.BooleanOptionalAction, help='don\'t use encryption for shares', default=False)
    return parser.parse_args()

def secret_sharing(data: list):
    out1 = []
    out2 = []
    for d in data:
        out1.append({})
        out2.append({})
        for k,v in d.items():
            share1 = int.from_bytes(urandom(4)) # 32 bit number
            share2 = (int(v) - share1) % 2**32
            if encryption:
                out1[-1][k] = encrypt(public_key_master, str(share1)).hex()
                out2[-1][k] = encrypt(public_key_helper, str(share2)).hex()
            else:
                out1[-1][k] = str(share1)
                out2[-1][k] = str(share2)

    return out1, out2

def encrypt(pk, data):
    return pk.encrypt(
        data.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        ))

public_key_master = None
public_key_helper = None
encryption = True

if __name__ == "__main__":

    args = parse_arguments()
    filepath = args.data_filepath
    master_url = args.master_url
    helper_url = args.helper_url
    encryption = not args.noencrypt
    print(encryption, args.noencrypt)
    print(args.pk_master)
    print(args.pk_helper)
    with open(args.pk_master, "rb") as key_file:
        public_key_master = serialization.load_pem_public_key(
        key_file.read(),
        backend=default_backend()
    )

    with open(args.pk_helper, "rb") as key_file:
        public_key_helper = serialization.load_pem_public_key(
        key_file.read(),
        backend=default_backend()
    )  

    print(f"Filepath: {filepath}")
    print(f"Master URL: {master_url}")
    print(f"Helper URL: {helper_url}")

    data = read_csv_with_header(filepath)
    share1, share2 = secret_sharing(data)
    ids = upload_all(share1, share2, master_url, helper_url)

    print(f"Uploaded {len(ids)} entries")