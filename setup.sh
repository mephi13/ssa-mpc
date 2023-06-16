# clone repository with games
git clone https://github.com/mephi13/mpc_games &&

# build docker images
docker build -t mpc/aggregation_server ./ &&

# run dockers
docker-compose up 