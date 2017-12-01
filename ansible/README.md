# Inventory
This is a list of devices that will be managed with a playbook.  The devices can be managed as a whole, in groups or individually.
The inventory is kept in the directory 'inventory'.  The master file is called hosts, and has a list of groups .  The individual members of 
each group is kept in it's own file, which is a list of router hostnames that belong to each group. Each hostname should have a file that is
named after it's own hostname, contains a line at the top with the hostname delimited by square brackets, and a second line with the IP
address that the device should be managed by. 
it's own name, and the lines:
"""
[<hostname>]
<IP address>
"""
For example, for the host MTST-TE01A with an IP address of 172.20.99.3 should have a file called MTST-TE01A with the following contents:
"""
[MTST-TE01A]
172.20.99.3
"""

Each device must be listed in a file that contains a group that defines the device model that the router is.  For instance, an M320 should be 
listed by it's hostname in the m320 file, and a SRX650 should be listed in the srx650 file.

There are other files for other groupings of devices to make managment easier.  The routers's hostname should be added to the file to make
it a member of the other groups.  The groups are:
- mpls : MPLS routers
- oob : OOB devices
- hub: OOB IPSEC hubs
- spoke: OOB IPSEC spokes
- iBGP_mesh: MPLS devices that participate in the BGP mesh
- flow: SRX devices that are running in flow mode
- packet: SRX devices that are running in packet mode
- selective_packet: SRX devices that are running in a combination of packet and flow mode

Other groups can be easily created following the model above.


# Vault
The vault is a encrypted file that contains sensitive information that can be used in playbooks such as passwords and community strings.
The vault file in use by the playbooks in these scripts is 'group_vars/secrets.yml'.

The file can be viewed with the command:
`ansible-vault --ask-vault-pass view  group_vars/secrets.yml`

The file can be edited with the command:
`ansible-vault --ask-vault-pass edit  group_vars/secrets.yml`

The password can be changed with the command:
`ansible-vault --ask-vault-pass rekey group_vars/secrets.yml`


# Running a Playbook


## list the hosts that will be modified
`ansible-playbook --ask-vault-pass --list-hosts -e 'juniper_user=<DEVICE USERNAME>'  <PLAYBOOK YAML FILE>`

## list the hosts that will be modified from a certain host or group with the -l flag
`ansible-playbook --ask-vault-pass -l <device to modify> --list-hosts -e 'juniper_user=<DEVICE USERNAME>'  <PLAYBOOK YAML FILE>`

## check a playbook on a host, -k is to prompt for ssh pasword, 
`ansible-playbook --ask-vault-pass -e 'juniper_user=<DEVICE USERNAME>'  -l <device to check> --check -k  <PLAYBOOK YAML FILE>`

## get a diff (show | compare) of what the playbook will do on a host
`ansible-playbook --ask-vault-pass -e 'juniper_user=<DEVICE USERNAME>'  -l <device to diff> --diff -k  <PLAYBOOK YAML FILE>`

## commit a playbook
`ansible-playbook --ask-vault-pass -e 'juniper_user=<DEVICE USERNAME>' -l <device to commit>  -k  <PLAYBOOK YAML FILE>`

## commit a playbook on a particular device with a rollback timer
`ansible-playbook --ask-vault-pass -e 'juniper_user=<DEVICE USERNAME> commit=<rollback timer in minutes>' -l <device to commit>  -k  <PLAYBOOK YAML FILE>`

## Playbooks

## baseline_ntp.yml 
Replaces the NTP configuration stanza on a device.  Uses a template 'templates/ntp.conf.j2' and populates it with variables from the 'group_vars/junosdevices.yml':
* *ntp_servers*: a list of NTP servers IP addresses
* *key_number*: the NTP key authentication number and the 'group_vars/secrets.yml' file (vault):
* *key_value*: the NTP authentication key in clear text



