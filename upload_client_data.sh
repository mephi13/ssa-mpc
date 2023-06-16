#bin/bash
python3 client/client.py client/data/testClient.csv http://200.168.0.3/upload http://200.168.0.2/upload aggregation_server/keys/key_pub_helper.crt aggregation_server/keys/key_pub_master.crt --noencrypt && 

curl http://200.168.0.3/collect -H "Content-type: application/json" --data '{"token":"some-secret-token-master","metric":"'$1'"}'  | jq