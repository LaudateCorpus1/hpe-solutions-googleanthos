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

from ilo_operations import *
from image_operations import *

import pdb

def run_cmd_on_shell(cmd):
    """
    This function executes command on command prompt.
    It will provide stdout, std err.
    Return: It will return stdout and stderr of input cmd command for this function.
    """

    try:
        # print("cwd: {0}".format(os.getcwd()))
        # This will form executing command based on stdout and stderr & will execute on shell
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        # This will execute the command/script on shell
        out, err = p.communicate()

        # Converting "bytes" type to "str" type
        out1, err1 = str(out,'utf-8'), str(err, 'utf-8')
    except Exception as run_except:
        print("The exception '{}' occurred during execution of the command '{}'".format(run_except, cmd))

    return out1, err1


def create_custom_iso_image_ubuntu(os_type, server, config, kickstart_file):
    """This is the primary function is to create a custom Red Hat Enterprise Linux ISO image for each of the server. 
    It triggers the functions to create custom kickstart files, mounts the RHEL OS image to the installer machine, 
    copies the contents, updates the custom kickstart file location and rebundles it into a custom RHEL image for each of the server. 
    
    Arguments:
        os_type {string}                      -- Type of operating system (currently supports rhel7)
        server {string}                       -- Custom configurations for a particular server as per the input_files/server_details.json
        config {string}                       -- OneView, web server and OS details as per the input_files/config.json
        kickstart_file {string}               -- Path of the base kickstart file for ESXi operating system

    Returns:
        Boolean -- returns True upon successful creation of custom os image, return False on failure of creation of custom os image
    """

    if os_type in ["ubuntu18", "ubuntu20"]:
        ubuntu_iso_filename = server["OS_image_name"]
        if not os.path.isfile(kickstart_file):
            print("Kickstart file is not present for {} installation".format(os_type))
            #print("Kickstart file is not present for RHEL installation")
            return False   	
    else:
        print("Installation OS type {} is not supported".format(os_type))
        return False
    destination_folder = config["HTTP_file_path"]

    print("Creating modified installation file for RHEL Installation")
    image_url = config["HTTP_server_base_url"] + ubuntu_iso_filename
    file_presence = is_iso_file_present(image_url)
    if not file_presence:
        print("ISO file is not present in the given http location. Please check the http location and then try again.")
        return False

    val = is_iso_image(ubuntu_iso_filename)
    if val:
        #pdb.set_trace()
        if os_type in ["ubuntu18", "ubuntu20"]:
            base_iso_image_path = config["HTTP_file_path"]
            filepath = base_iso_image_path + ubuntu_iso_filename
            server_serial_number = server["Server_serial_number"]

            temppath = "/tmp/" + "redhatmount_" + server_serial_number + "/"
            mount_path = "/tmp/" + "redhatorig_" + server_serial_number

            create_dir_exist(temppath)

            kickstart_filepath = temppath + "/preseed/ks-ubuntu.cfg"

            mount_proc_id = mount_iso_image(filepath, mount_path)
            if mount_proc_id == 0:
                print("Successfully mounted the image {}".format(ubuntu_iso_filename))
                #run_cmd_on_shell("rm -f")
            else:
                print("Attempting to unmount the previously mounted image")
                umount_id = unmount_iso_image(mount_path)
                mount_proc_id = mount_iso_image(filepath, mount_path)
                if mount_proc_id == 0:
                    print("Successfully unmounted the previously mounted image")
                    # Removing recursive ubuntu directory
                    #run_cmd_on_shell("rm -f {}/ubuntu".format(mount_path))
                else:
                    print("Failed to mount the image {}".format(ubuntu_iso_filename))
                    return False

            # Create dot files
            run_cmd_on_shell("shopt -s dotglob")

            #copy_iso_contents(mount_path, temppath)
            run_cmd_on_shell("cp -avRf {}/* {}".format(mount_path, temppath))
            run_cmd_on_shell("cp -avRf {}/.disk {}".format(mount_path, temppath))

            # Confirm the LABEL of the DVD iso
            run_cmd_on_shell("blkid {}".format(filepath))

            kickstart_status  = create_kickstart_file_for_ubuntu(kickstart_filepath, kickstart_file, server)
            
            if(kickstart_status and os.path.isfile(kickstart_filepath)):
                redhat_label = update_grub_file_for_efi_boot(temppath, os_type)
                run_cmd_on_shell("cp {}/preseed/ubuntu-server.seed {}/preseed/ubuntu-custom.seed".format(temppath, temppath))
                configure_isolinux_file_to_ubuntu(temppath, os_type)
                update_ubuntu_seed_file(temppath)
                
                destination_filename = get_custom_image_name(os_type, server_serial_number) 

                out, err = rebuild_iso_redhat_image(temppath, destination_folder, destination_filename, redhat_label, os_type)
                if out == '':
                    print("Successfully re-created the iso image for server {} after modifying the content".format(server_serial_number))
                    status = True
                else:
                    print("Error in recreating the iso image for server {} after modifying the content".format(server_serial_number))
                    status = False
                                
                umount_proc_id = unmount_iso_image(mount_path)
                if umount_proc_id == 0:
                    print("Successfully unmounted the iso image")
                else:
                    print("Error in umounting the iso image")                

                delete_temp_folder(temppath)
                return status
            else:
                print("Error in fetching custom kickstart file {}".format(kickstart_file))
                return status
        else:
            print("Not supporting installing '{}' OS".format(os_type))
            return False
    else:
        print("File type is not supported")
        return False
    return True


def create_kickstart_file_for_ubuntu(kickstart_filepath, kickstart_file, server_data):
    """This function is to create custom kickstart file for Red Hat Enterprise Linux nodes
    
    Arguments:
        filepath {string}        -- custom kickstart file path
        kickstart_file {string}  -- base kickstart file path
        server_data {dictionary} -- Custom configurations for a particular server as per the input_files/server_details.json
    """
    try:
        ks_text = ""
        run_cmd_on_shell("cp {} {}".format(kickstart_file, kickstart_filepath))
        with open(kickstart_filepath, 'r') as fp:
            for line in fp.readlines():
                if "Host_IP" in line:
                    line = line.replace("Host_IP", server_data["Host_IP"]) 
                    line = line.replace("Host_DNS", server_data["Host_DNS"])
                    line = line.replace("Host_Gateway", server_data["Host_Gateway"])
                    line = line.replace("Host_Netmask", server_data["Host_Netmask"])
                    line = line.replace("Bonding_Interface1", server_data["Bonding_Interface1"])
                    line = line.replace("Bonding_Interface2", server_data["Bonding_Interface2"])
                elif "Host_Username" in line:
                    line = line.replace("Host_Username", server_data["Host_Username"]) 
                    line = line.replace("Host_Password", server_data["Host_Password"])
                elif "Host_Password" in line:
                    line = line.replace("Host_Password", server_data["Host_Password"])
                elif "Hostname" in line:
                    line = line.replace("Hostname", server_data["Hostname"])
                else:
                    pass

                # Gathering modifying kickstart file information
                ks_text += line


        # Update kickstart file with user input values
        with open(kickstart_filepath, 'w') as fp:
            fp.write(ks_text)

        print("Successfully created kickstart file for server {} ".format(server_data["Server_serial_number"]) )
        return True
    except IOError as ioer:
        print("I/O error occurred while creating custom kickstart file {}".format(ioer))
        return False
    except Exception as er:
        print("Error occurred in creating custom kickstart file {}".format(er))
        return False

def update_grub_file_for_efi_boot(efi_file_path, os_type):
    #pdb.set_trace()
    efi_cfg_text = ""
    flag = False
    #efi_grub_file = efi_file_path + "EFI/BOOT/grub.cfg"
    efi_grub_file = efi_file_path + "boot/grub/grub.cfg"

    with open(efi_grub_file, 'r') as fp:
        search_str = "quiet"
        add_ks_str = search_str + " ks=cdrom:/preseed/ks-ubuntu.cfg"
        for line in fp.readlines():
            if (search_str in line):
                line = line.replace(search_str, add_ks_str)

            if ("timeout") in line:
                line = line.replace("30", "6")

            efi_cfg_text += line

    with open(efi_grub_file, 'w') as fp:
        fp.write(efi_cfg_text)


def update_ubuntu_seed_file(new_path):
    preseed_file_path = new_path + "/preseed/ubuntu-custom.seed"
    with open(preseed_file_path, 'a') as fp:
        fp.write("#Package selection")
        fp.write("\ntasksel tasksel/first multiset lamp-server\n")


def configure_isolinux_file_to_ubuntu(new_path, os_type):
    #pdb.set_trace()
    iso_cfg_text = ""
    append_cnt = 0
    iso_conf_file = new_path + "/isolinux/txt.cfg"
    with open(iso_conf_file, 'r') as fp:
        for line in fp.readlines():
            if ("append" in line):
                append_cnt += 1

            if (append_cnt == 1):
                line += "\n" + "label myownoption" + "\n"
                line += "  menu label ^Install Custom Ubuntu Server" + "\n"
                line += "  kernel /install/vmlinuz" + "\n"
                line += "  append  file=/cdrom/preseed/ubuntu-custom.seed initrd=/install/initrd.gz quiet ks=cdrom:/preseed/ks-ubuntu.cfg --" + "\n"
                append_cnt += 1

            iso_cfg_text += line

    with open(iso_conf_file, 'w') as fp:
        fp.write(iso_cfg_text)




'''
def update_ks_file_location_redhat_iso_efi(temppath):
    """This function is to update the kickstart file location in the /EFI/BOOT/grub.cfg file within the RHEL OS ISO file.
    
    Arguments:
        temppath {string}             -- Path to the custom ISO image file
        server_serial_number {string} -- server serial number
        http_url {string}             -- HTTP server base URL
    """
    boot_filename = temppath + "grub.cfg"
    new_data = ""
    redhat_label = ""
    try:
        with open(boot_filename, "r") as file_read:
            for line in file_read.readlines():
                if "linuxefi" in line:
                    str = line[line.index("LABEL=")+6:]
                    redhat_label = str[:str.index(" ")]
                    line = line.replace("/images/pxeboot/vmlinuz", "/images/pxeboot/vmlinuz inst.ks=cdrom:/ks.cfg")
                if "default=" in line:
                    line = line.replace("1", "0")
                if "set timeout" in line:
                    line = line.replace("60", "6")
                new_data = new_data + line
        file_read.close()
        with open(boot_filename, "w") as file_write:
            file_write.write(new_data)
        file_write.close()
        return redhat_label
    except IOError as ioer:
        print("I/O error occurred while modifying the iso img file {}".format(ioer))
    except Exception as er:
        print("Error occurred in modifying the image {}".format(er))
'''

def update_ks_file_location_redhat_iso_legacy(temppath):
    """This function is to update the kickstart file location in the /isolinux/isolinux.cfg file within the RHEL OS ISO file.
    
    Arguments:
        temppath {string}             -- Path to the custom ISO image file
        server_serial_number {string} -- Server serial number
        http_url {string}             -- HTTP server base URL
        os_type {string}              -- Type of the OS
    """
    boot_filename = temppath + "isolinux.cfg"
    new_data = ""
    
    try:
        with open(boot_filename, "r") as file_read:
            for line in file_read.readlines():
                if "initrd=initrd.img" in line:
                    line = line.replace("append initrd=initrd.img", "append initrd=initrd.img inst.ks=cdrom:/ks.cfg")
                if "default vesamenu.c32" in line:
                    line = line.replace("default vesamenu.c32", "default linux")
                new_data = new_data + line
        file_read.close()
        with open(boot_filename, "w") as file_write:
            file_write.write(new_data)
        file_write.close()
    except IOError as ioer:
        print("I/O error occurred while modifying the iso img file: {}".format(ioer))
    except Exception as er:
        print("Error occurred in modifying the image {}".format(er))

def rebuild_iso_redhat_image(temppath, custom_iso_path, iso_filename, redhat_label, os_type):
    """
    This function is to rebuild an ISO image after customization

    Arguments:
        temppath {string}           -- Path to the custom ISO image contents which needs to rebuilt
        custom_iso_path {string}    -- Path to store the resultant ISO image
        iso_filename {string}       -- Name for the resultant ISO image
    """
    try:
        #pdb.set_trace()

        create_dir_exist(custom_iso_path)

        custom_iso = custom_iso_path + iso_filename

        os.chdir(temppath)
        #run_cmd_on_shell("mkisofs -o {} -b isolinux/isolinux.bin -J -R -l -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot -e images/efiboot.img -no-emul-boot -graft-points -V {} . ".format(custom_iso, custom_iso_verbose))
        #custom_iso_creation_cmd = "mkisofs -o {} -b isolinux/isolinux.bin -J -R -l -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot -e images/efiboot.img -no-emul-boot -graft-points -V {} . ".format(custom_iso, custom_iso_verbose)
        custom_iso_creation_cmd = " mkisofs -o {} -b isolinux/isolinux.bin -J -R -l -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot -e boot/grub/efi.img -no-emul-boot -graft-points .".format(custom_iso)

        run_cmd_on_shell(custom_iso_creation_cmd)

        # Configure proper EFI boot
        out, err = run_cmd_on_shell("isohybrid --uefi {}".format(custom_iso))

        return out, err
        '''
        args = ["mkisofs", "-o", custom_iso, "-b", "isolinux/isolinux.bin", "-J" , "-R", "-l", "-c", "isolinux/boot.cat", "-no-emul-boot", "-boot-load-size", "4",
                "-boot-info-table", "-eltorito-alt-boot", "-e", "images/efiboot.img", "-no-emul-boot","-graft-points", "-V" , redhat_label , temppath]
        execute_linux_command(args)
        args = ["isohybrid","--uefi",custom_iso]
        proc = execute_linux_command(args)
        args = ["implantisomd5", custom_iso]
        proc = execute_linux_command(args)
        return proc
        '''
    except CalledProcessError as subprcer:
        print("Subprocess error occurred while rebuilding custom iso image {}".format(subprcer))
    except Exception as er:
        print("Error while rebuilding custom iso image {}".format(er))
