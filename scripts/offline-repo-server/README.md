# Setting up ubuntu offline repository on Baremetal or Virtual machine

This folder consists of script how to configure a local repository server based on Ubuntu Bionic over virtual machine/bare metal.
 
## Prerequisites for installer machine

- Ubuntu 18.04 virtual machine with the following configurations is essential to initiate the Ubuntu repository server process.

    1. Network bandwidth becomes very important
    2. Need to register the repository to the Ubuntu list of mirrors
    3. At least 2 TB disk space or more of disk space (in the "/" partition) because user must mirror all previous versions, 4 CPU cores and 16GB RAM.
    4. 1 network interface with static IP address configured on same network as the management plane of the bare-metal servers and has access to internet.
    5. Ansible 2.9 should be installed.

## Installing the required software on the server and creating apt-mirror repository.

1. Navigate to the directory, $BASE_DIR/Anthos/scripts/offline-repo-server and Open inventory.yaml file with the following command and add the details of server IP.
      ```
      $ sudo vi inventory.yaml

      ``` 
	  	  	  
      Example values for the input configuration is as follows
	  
      ```
      hosts:
        localhost:
         vars:
           ansible_connection: server IP
		
      ```
      
2. Executing the ubuntu_repository_server.yaml playbook to create Ubuntu repository server. 

   ```
    $ ansible-playbook ubuntu_repository_server.yaml 
   
   ```

Note: Once the playbook done always need to check the base_path option in the mirror.list file. Sometimes the set base_path line containing the option points to (by default is /var/spool/apt-mirror), the correct path for our repository /var/www/html/Ubuntu/. Also need to specify mirroring the bionic distro (change accordingly if user have a different Ubuntu version) repos, always in the mirror.list configuration file.

      
   ```
    $ sudo vi /etc/apt/mirror.list

   ```
3. Once changes are done in mirror.list run the below command to create a local mirror, keep in mind that an initial mirroring (from archive.ubuntu.com only) sometimes can take a lot of time (based on connection).
  
   ```
   $ sudo apt-mirror

   ```
Eventually we will get to the point when the clean.sh and postmirror.sh scripts are executed, it is a sign the mirroring process has been completed.

## Configuring the Linux client to use the local repository server

1. Update control file located in /etc/apt/sources.list by specifying local repository.

2. Below is the path to check repositories in web GUI.
  
   ```
   http://server IP/ubuntu/mirror/archive.ubuntu.com/ubuntu

   ```


































   ```



