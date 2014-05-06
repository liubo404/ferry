#!/bin/bash

# Make sure we get the env variables in place. 
source /etc/profile

if [ $1 == "master" ]; then
    if [[ ! -f /tmp/spark_services.log ]]; then
	su ferry -c '$SPARK_HOME/sbin/start-master.sh'
	su ferry -c '$SPARK_HOME/sbin/start-slaves.sh'
    fi

    # Record the Spark service. 
    echo $1 > /tmp/spark_services.log
fi
