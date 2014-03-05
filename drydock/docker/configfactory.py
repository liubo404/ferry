# Copyright 2014 OpenCore LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import gevent
from gevent import monkey;  monkey.patch_all()
import os
import logging
from pymongo import MongoClient
from drydock.docker.docker              import DockerInstance
from drydock.docker.fabric              import DockerFabric
from drydock.config.glusterconfig       import *
from drydock.config.hadoopconfig        import *
from drydock.config.hadoopclientconfig  import *
from drydock.config.metastore           import *
from drydock.config.cassandraconfig     import *
from drydock.config.mpiconfig           import *
from drydock.config.mpiclientconfig     import *
from drydock.config.titanconfig         import *
from drydock.config.cassandraclientconfig   import *

class ConfigFactory(object):
    def __init__(self):
        # Storage configuration tools
        self.gluster = GlusterInitializer()
        self.hadoop = HadoopInitializer()
        self.yarn = HadoopInitializer()
        self.hive = MetaStoreInitializer()
        self.cassandra = CassandraInitializer()
        self.titan = TitanInitializer()
        self.cass_client = CassandraClientInitializer()
        self.mpi = OpenMPIInitializer()
        self.mpi_client = OpenMPIClientInitializer()
        self.hadoop_client = HadoopClientInitializer()

        # Get the Drydock home to find the templates.
        template_dir = os.path.dirname(os.path.dirname(__file__)) + '/templates'
        self.hadoop.template_dir =        template_dir + '/hadoop/'
        self.yarn.template_dir =          template_dir + '/hadoop/'
        self.hadoop_client.template_dir = template_dir + '/hadoop/'
        self.hive.template_dir =          template_dir + '/hive-metastore/'
        self.gluster.template_dir =       template_dir + '/gluster/'
        self.cassandra.template_dir =     template_dir + '/cassandra/'
        self.titan.template_dir =         template_dir + '/titan/'
        self.cass_client.template_dir =   template_dir + '/cassandra/'
        self.mpi.template_dir =           template_dir + '/openmpi/'
        self.mpi_client.template_dir =    template_dir + '/openmpi/'

    """
    Helper method to generate and copy over the configuration. 
    """
    def _generate_configuration(self, uuid, container_info, config_factory):
        config = config_factory.generate(len(container_info))
        config.uuid = uuid
        return config_factory.apply(config, container_info)

    """
    Generagte a compute-specific configuration. This configuration
    lives in its own directory that gets copied in each container. 
    """
    def generate_compute_configuration(self, 
                                       uuid,
                                       containers,
                                       service,
                                       args, 
                                       storage_info):
        container_info = []
        for c in containers:
            s = {'data_dev':'eth0', 
                 'data_ip':c.internal_ip, 
                 'manage_ip':c.internal_ip,
                 'host_name':c.host_name,
                 'type':c.service_type}
            s['container'] = c
            s['storage'] = storage_info
            s['args'] = args

            container_info.append(s)

        return self._generate_configuration(uuid, 
                                                container_info, 
                                            service)

    """
    Generagte a storage-specific configuration. This configuration
    lives in its own directory that gets copied in each container. 
    """
    def generate_storage_configuration(self, 
                                       uuid,
                                       containers,
                                       service, 
                                       args=None):
        container_info = []
        for c in containers:
            s = {'data_dev':'eth0', 
                 'data_ip':c.internal_ip, 
                 'manage_ip':c.internal_ip,
                 'host_name':c.host_name,
                 'type':c.service_type}
            s['container'] = c
            s['args'] = args

            # Specify the data volume. There should only be one. 
            for v in c.volumes.keys():
                s['ebs_block'] = c.volumes[v]

            container_info.append(s)
        return self._generate_configuration(uuid, container_info, service) 
    """
    Generate a connector specific configuration. 
    """
    def generate_connector_configuration(self, 
                                         uuid,
                                         containers,
                                         service, 
                                         storage_info=None,
                                         compute_info=None,
                                         args=None):
        container_info = []
        for c in containers:
            s = {'data_dev':'eth0', 
                 'data_ip':c.internal_ip, 
                 'manage_ip':c.internal_ip,
                 'host_name':c.host_name}
            s['container'] = c
            s['args'] = args

            # Specify the entry point
            s['storage'] = storage_info
            s['compute'] = compute_info
            container_info.append(s)
        return self._generate_configuration(uuid, container_info, service) 

    """
    Helper method to generate some environment variables. 
    """
    def _generate_key_value(self,
                            json_data,
                            base_key):
        env = {}
        if type(json_data) is list:
            for j in json_data:
                values = self._generate_key_value(j, base_key)
                env = dict(env.items() + values.items())
        else:
            for k in json_data.keys():
                if type(json_data[k]) is unicode:
                    key = "%s_%s" % (base_key, k.upper())
                    value = json_data[k]
                    env[key] = value
                elif type(json_data[k]) is dict:
                    values = self._generate_key_value(json_data[k],
                                                      base_key + "_LAYER")
                    env = dict(env.items() + values.items())
        return env

    """
    Generate some environment variables for the connectors. 
    These variables help the connectors query the backend. 
    """
    def generate_env_vars(self,
                          storage_info=None,
                          compute_info=None):
        storage_values = {}
        compute_values = {}
        if storage_info:
            storage_values = self._generate_key_value(storage_info[0],
                                              "BACKEND_STORAGE")
        if compute_info:
            compute_values = self._generate_key_value(compute_info[0],
                                              "BACKEND_COMPUTE")
        return dict(storage_values.items() + compute_values.items())
