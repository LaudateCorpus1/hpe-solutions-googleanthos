# OS Deployment

This folder consists of script to deploy RHEL8, RHEL7, SLES15, Ubuntu18, Ubuntu20, and Centos8 operating systems over bare-metal servers using virtual media.

## Prerequisites for installer machine
- Centos 7 Installer machine with the following configurations is essential to initiate the RHEL_OS deployment process.
    1. At least 500 GB disk space (in the "/" partition), 4 CPU cores and 8GB RAM.
    2. 1 network interface with static IP address configured on same network as the management plane of the bare-metal servers and has access to internet.
    4. Python 3.6 or above should be present and latest version associated pip should be present.
    5. Ansible 2.9 should be installed.
    6. Ensure that SELinux status is disabled on the installer machine. 
   
- HPE ProLiant DL servers with configurations for installing operating system is listed as follows: 
     * 2 network interfaces for the production network 
     * 1 local drive to be used as the boot device
     * Boot mode is set to UEFI
     * Boot order - Hard disk
     * Secure Boot - disabled

- For each of the servers, iLO account with administrative privileges is required to ensure successful deployment of the operating system.

## Installation

1. Enable Python3 and Ansible Environment as mentioned in "Installer machine" section of deployment guide.
2. Setup the installer machine to configure the development tools and other python packages required for OS installation. Navigate to the directory, $BASE_DIR/os_deployment/ and run the below command to install requirements. 
   ```
   # sh setup.sh

   # pip3 install -r requirements.txt

   ```

3. Open input.yaml file with the following command and add the details of web server, operating system, network, and iLO details.

      Command to edit input.yaml

      ```
      # ansible-vault edit input.yaml
      ```
      NOTE:
      * The default password for input file is **changeme**
	  	  	  
      Example values for the input configuration is as follows
	  
      ```
		servers:
		 - Server_serial_number  : MXQ01201G8
		   ILO_Address           : 10.0.40.61
		   ILO_Username          : <username_of_the_admin_privileges_account>
		   ILO_Password          : <password_of_the_admin_privileges_account>
		   Hostname              : worker1.*****.local
		   Host_Username         : <host_username> 
		   Host_Password         : <host_password>
         Bonding_Interface1    : <interface to be bonded>
         Bonding_Interface2    : <interface to be bonded>
		   Host_IP               : 20.0.**.**
		   Host_Netmask          : 255.**.**.**
		   Host_Gateway          : 20.**.**.**
		   Host_DNS              : 20.**.**.**
		   OS_type               : rhel8
		   OS_image_name         : rhel-server-8.1-x86_64-dvd.iso
         Host_Search           : <domain> #This input required only in case of SLES15 deployment.
		   
		config:
		   HTTP_server_base_url: http://20.0.**.**/     #Installer machine ip address
		   HTTP_file_path: /usr/share/nginx/html/
		   base_dir_path: $BASE_DIR/os_deployment/

		
      ```
      Note: 

      * $BASE_DIR = /opt/hpe/anthos/scripts/

      * Acceptable values for "OS_type" variable are "rhel7","rhel8", "centos8", "sles15", "ubuntu18", and "ubuntu20".

      * It is strong recommended that user should unmount existing partitions on selected storage drive.
   
      * Make sure that host ip's are reachable from the installer machine.

      * It is strongly recomended to set "Host_Username" to root only for SLES15, RHEL8, RHEL7, Centos8.  

     
4. Executing the playbook to deploy operating system.
   ```
   # ansible-playbook os_deploy.yaml --ask-vault-pass
   ```

Note
1. Generic settings done as part of kickstart file for RHEL/Ubuntu/SLES/Centos are as follows. It is recommended that the user reviews and modifies the kickstart files or autoyast file to suit their requirements.
   * Graphical installation
   * Language - en_US
   * Keyboard & layout - US
   * System service chronyd disabled
   * timezone - Asia/Kolkata
   * Bootloader config
       * bootloader location=mbr
       * clearpart --all --initlabel
       * ignoredisk --only-use=sda
       * part swap --asprimary --fstype="swap" --size=77263
       * part /boot --fstype xfs --size=300
       * part /boot/efi --fstype="vfat" --size=1024
       * part / --size=500 --grow
	   * part /var --fstype ext4 --size=15360
	   * part /usr/local/bin --size=1024
   *  NIC teaming is performed with devices provided in 'Bonding_interface1' and 'Bonding_interface2'. It is assigned with the Host_IP defined in the input_files/server_details.json input file.
   
  ```   

