# Configure Hosts

This folder consists of Ansible playbooks to register REHL7/8 hosts.

## Prerequisites for installer machine

- Centos 7 Installer machine with the following configurations is essential to initiate the RHEL_OS deployment process.
    1. At least 500 GB disk space (in the "/" partition), 4 CPU cores and 8GB RAM.
    2. 1 network interface with static IP address configured on same network as the management plane of the bare-metal servers and has access to internet.
    4. Python 3.6 or above should be present and latest version associated pip should be present.
    5. Ansible 2.9 should be installed.
    6. Ensure that SELinux status is disabled on the installer machine. 

## Configuration
 
1. Enable Python3 and Ansible environment as mentioned in "Installer machine" section of deployment guide. Make sure redhat_subscription plugin is installed on installer machine if not run the below command to install.

   ``` ansible-galaxy collection install community.general ```

2. Edit secret.yaml file and provide subscription account details or Red Hat Satellite Server Details.

    ``` ansible-vault edit secret.yaml```

    Sample secret.yaml file

    rhsub_username       : <username>
    rhsub_password       : <password>
    activation_key       : <activationkey>
    org                  : <orgnaization>
    env                  : <environment>
    katello_package_path : <katello_package_path>

    NOTES:

    - rhsub_username is subscription account username or Red Hat Satellite server username

    - rhsub_password is subscription account password or Red Hat Satellite server password

    - Provide activation_key and org when the client system needs to be register against Red Hat Satellite server with specified organization view otherwise set these values to empty "". 

    - Provide env when the client system needs to be register against Red Hat Satellite server with default organization view otherwise set this value to empty "". Red Hat Satellite Server username and password are mandatory in this case.  

    - katello-ca-consumer-latest.noarch.rpm needs to be isntalled on client machines to register client with Red Hat Satellite Server. Provide katello_package_path in the input file. Example:  http://<redhat_satellite_server_hostname>/pub/katello-ca-consumer-<satellite_server_hostname>-1.0-1.noarch.rpm. Set this value to empty "" in case connected registration. 

    - By default all the repos will be enabled on client system. If the client system registered with Red Hat Satellite server and has any customized repos, customized repos needs to be added to the host manually by logging into the satellite server.

3. Edit hosts file and add client nodes FQDN or IP address.

4. Run below command to register REHL nodes. 

    ``` ansible-playbook -i hosts prepare_hosts.yaml --ask-vault-pass ```

    NOTE: 
    
    - This playbook register the client machines, attach subscription and enable rhel 7/8 repositories

    - Create an SSH private and public key using ```ssh-keygen``` command and copy ssh-key from installer machine to client machines using ```ssh-copy-id <user>@<client_machine_FQDN/IP>```