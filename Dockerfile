# requires fbpcf/ubuntu as base image
# need to buld it from here:
# https://github.com/facebookresearch/fbpcf/
FROM fbpcf/ubuntu:latest as base

RUN mkdir /aggregation
WORKDIR /aggregation

RUN mkdir demographic_metrics
RUN mkdir demographic_metrics_app
RUN mkdir sitecheck

COPY ./mpc_games/demographic_metrics_app/ ./demographic_metrics_app/
COPY ./mpc_games/demographic_metrics/ ./demographic_metrics/
COPY ./mpc_games/CMakeLists.txt ./

RUN cmake . -DTHREADING=ON -DEMP_USE_RANDOM_DEVICE=ON -DCMAKE_CXX_FLAGS="-march=haswell" -DCMAKE_C_FLAGS="-march=haswell" -DCMAKE_BUILD_TYPE=Release && make -j4 demographicapp

CMD ["/bin/bash"]

FROM python:3.8-slim

COPY --from=base /aggregation/bin/demographicapp /bin/demographicapp
COPY --from=base /usr/lib/ /usr/lib/
RUN mkdir ./aggregation_server
RUN mkdir user_data
RUN mkdir aggregation_output
COPY aggregation_server/ ./aggregation_server/
COPY requirements.txt ./
COPY config_server.sh ./
RUN chmod +x config_server.sh

RUN pip install --upgrade -r requirements.txt 

EXPOSE 80
EXPOSE 10000-20000

ENTRYPOINT [ "./config_server.sh" ]
CMD [ "helper" ]