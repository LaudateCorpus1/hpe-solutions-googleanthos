# (C) Copyright (2018,2021) Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
###

from subprocess import CalledProcessError
import shutil
import subprocess
import threading
from redfish_object import RedfishObject
from time import sleep
import requests
import os
import json
from datetime import datetime
from datetime import timedelta
from rhel_operations import *
from ilo_operations import *
from image_operations import *
from suse_operations import *
from rhel8_operations import *
from ubuntu_operations import *


def image_deployment(server, config):
    """Primary function that triggers OS deployment for each of the server hardware. 
    This function handles end to end operations and triggers functions necessary for OS deployment. 
    
    Arguments:
        servers {dictionary}       -- server details as per the input_file/server_details.json
        config {dictionary}        -- Config details as per the input_file/config.json

    Returns:
        Boolean -- returns True on successful OS deployment, returns False on failure of OS deployment
    """
    try:
        # Opening input files
        kickstart_files = {
        "rhel7"                     :   "kickstart_files/ks_rhel7.cfg",
        "rhel8"                     :   "kickstart_files/ks_rhel8.cfg",
        "sles15"                    :   "kickstart_files/autoinst.xml",
        "centos8"                   :   "kickstart_files/ks_rhel8.cfg",
        "ubuntu18"                  :   "kickstart_files/ks-ubuntu.cfg",
        "ubuntu20"                  :   "kickstart_files/ks-ubuntu.cfg"
        }
        server_serial_number = server['Server_serial_number']
        os_type = server["OS_type"]
        image_path = "".join([config["HTTP_server_base_url"],server["OS_image_name"]])
        # Check if iso image present or not in the given location
        iso_file_check = is_iso_file_present(image_path)
        if not iso_file_check:
            print("OS deployment failed for server with serial number {}.".format(server_serial_number))
            print("ISO image not preset in the specified location")
            return False

        # Check OS type
        if os_type not in kickstart_files.keys():
            print("OS deployment failed for server with serial number {}.".format(server_serial_number))
            print("Unsupported OS type. Supported OS types are rhel7, rhel8, sles15 and centos8")
        # Create a REDFISH object
        redfish_obj = create_redfish_object(server)
        if not redfish_obj:
            print("Error occured while creating redfish object for server {}".format(server_serial_number))
            return False

        # Get server model 
        server_model = get_server_model(redfish_obj)
        if not server_model:
            print("Failed to get server model")
            return False
        if "Gen10" not in server_model:
            print("Server with serial number {} is not supported for this solution".format(server['Server_serial_number']))
            return False

        base_kickstart_filepath = "".join([config['base_dir_path'],kickstart_files[os_type]])
        print(" base kickstart filepath", base_kickstart_filepath)
        # Create custom iso image with the given kickstart file
        if os_type == "rhel7":
            custom_iso_created = create_custom_iso_image_redhat(os_type, server, config, base_kickstart_filepath)
        elif os_type == "sles15":
            custom_iso_created = create_custom_iso_image_sles(os_type, server, config, base_kickstart_filepath)
        elif os_type in ["rhel8", "centos8"]:
            custom_iso_created = create_custom_iso_image_redhat8(os_type, server, config, base_kickstart_filepath)
        elif os_type in ["ubuntu18", "ubuntu20"]:
            custom_iso_created = create_custom_iso_image_ubuntu(os_type, server, config, base_kickstart_filepath)
        else:
            print("Unsupported OS type. Supported OS types are rhel7, rhel8, sles15 and centos8")
        print("Starting OS installation for server: {}".format(server_serial_number))

        # Get custom image path
        print("getting custom image path")
        custom_image_path = get_custom_image_path(config["HTTP_file_path"], os_type, server_serial_number)
        # Get custom image url
        print("custom image path", custom_image_path)
        custom_image_url = get_custom_image_url(config["HTTP_server_base_url"], os_type, server_serial_number)
        # Get custom kickstart file path
        custom_kickstart_path = get_custom_kickstart_path(config["HTTP_file_path"], os_type, server_serial_number)
        print("custom kickstart path", custom_kickstart_path)

        custom_iso_present = is_iso_file_present(custom_image_url)
        print("custom_is_crated", custom_iso_created)
        print("custom_iso_present", custom_iso_present)
        print("custom_image_url", custom_image_url)
        if(custom_iso_created and custom_iso_present):
            # Unmount the previous ISO and mount the custom ISO image
            print("custom iso crated and present")
            unmount_virtual_media_iso(redfish_obj)
            print("unmounted virtual medai")
            mount_virtual_media_iso(redfish_obj, custom_image_url, True)
            print("mounted virtual media")
            power_staus = get_post_state(redfish_obj)
            if power_staus == "PowerOff":
                change_server_power_state(redfish_obj, server_serial_number, power_state="On")
            else:
                change_server_power_state(redfish_obj, server_serial_number, power_state="ForceRestart")

            is_complete = wait_for_os_deployment_to_complete(redfish_obj, server['Server_serial_number'])
            print("waited for os deployment")
            #unmount ISO once OS deployment is complete
            unmount_virtual_media_iso(redfish_obj)
            
            # Delete custom ISO image and Kickstart files
            print("Deleting custom image for server {}".format(server_serial_number))
            delete_file(custom_image_path)    
            print("Deleting custom kickstart file for server {}".format(server_serial_number))            
            delete_file(custom_kickstart_path)


            # Logout of iLO 
            print("Logging out of iLO for server {}".format(server_serial_number))
            redfish_obj.redfish_client.logout()

            if is_complete:
                print("OS installation is complete for server {}".format(server_serial_number))
                return True
            else:
                print("OS installation failed on server {}".format(server_serial_number))
                return False
        else:
            print("Error in fetching custom image for server {}".format(server_serial_number))
            return False
    except Exception as e:
        print("Failure: Error occurred while deploying image on server {}".format(e))
        return False

def unmount_virtual_media(server):
    """This function is to call unmount_virtual_media_iso function
    
    Arguments:
        servers {dict} -- server details
    """
    try:
        # Creating redfish object
        redfish_obj = create_redfish_object(server)        
        unmount_virtual_media_iso(redfish_obj)
    except Exception as e:
        print("Failure: Failed to unmount virtual media {}".format(e))


def wait_for_os_deployment(server):
    """This function is to call wait_for_os_deployment function
    
    Arguments:
        servers {dict} -- server details
    """
    try:
        # Creating redfish object
        redfish_obj = create_redfish_object(server)
        wait_for_os_deployment_to_complete(redfish_obj, server['Server_serial_number'])
    except Exception as e:
        print("Failure: Image deployment failed {}".format(e))


