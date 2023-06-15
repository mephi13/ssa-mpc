#!/bin/bash

if [[ "$1" == "helper" || "$1" == "master" ]]; then
    source_file="./aggregation_server/config_helper.py"
    destination_file="./aggregation_server/config.py"

    if [ "$1" == "master" ]; then
        # Append '_copy' to the destination file name
        source_file="./aggregation_server/config_master.py"
    fi

    cp "$source_file" "$destination_file"
    echo "File copied successfully from $source_file to $destination_file."
else
    echo "First command-line argument should be 'helper' or 'master'."
    exit 1
fi

flask --app aggregation_server:app run --host=0.0.0.0 --port=80 --with-threads --debugger --reload
#gunicorn --bind 0.0.0.0:80 --log-level debug aggregation_server:app
