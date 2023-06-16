import csv
import requests
import argparse
from os import urandom


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
            out1[-1][k] = share1
            out2[-1][k] = share2

    return out1, out2

if __name__ == "__main__":

    args = parse_arguments()
    filepath = args.data_filepath
    master_url = args.master_url
    helper_url = args.helper_url

    print(f"Filepath: {filepath}")
    print(f"Master URL: {master_url}")
    print(f"Helper URL: {helper_url}")

    data = read_csv_with_header(filepath)
    share1, share2 = secret_sharing(data)
    ids = upload_all(share1, share2, master_url, helper_url)

    print(f"Uploaded {len(ids)} entries")