#bin/bash
python3 client/client.py client/data/testClient.csv http://200.168.0.2/upload http://200.168.0.3/upload && 

curl http://200.168.0.3/collect -H "Content-type: application/json" --data '{"token":"some-secret-token-master","metric":"'$1'"}'  | jq