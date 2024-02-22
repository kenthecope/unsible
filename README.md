This is unsible.  An lightweight ansible rip off for those who can't install ansible or don't want to....

Installation:

1.  Create a python3 virtual enviornment: python3 -m venv ve 
2.  Activate the virtual environment:  source ve/bin/activate
3.  Upgrade pip:  pip install --upgrade pip
4.  Install depencencies:  pip install -r requirements.txt


Running:

Make sure the virtual environment is activated, step 2 above:

Display help:

./unsible.py -h
Unsible FE ver 22.01.2024.01 - A Junos PyEZ cli frontend
usage: unsible.py [-h] [-d HOST] [--hostlist HOSTLIST] [-l LIMIT] [-i INVENTORY_FILE] [-u USERNAME] [-p] [--list-hosts] [--list-vars] [--output-file OUTPUT_FILE]
                  [--output-dir OUTPUT_DIR] [--separate]
                  {cli,configure,commit,rollback,copyto,inventory,storage} ...

Unsible

positional arguments:
  {cli,configure,commit,rollback,copyto,inventory,storage}
                        commands
    cli                 Run a cli command
    configure           Configure a device interactively
    commit              Perform a commit on a device
    rollback            Perform a rollback 1 and a commit on a device
    copyto              Copy a file to a device using scp
    inventory           Do a "show chassis hardware" on the device
    storage             cleanup system storage on device

optional arguments:
  -h, --help            show this help message and exit
  -d HOST, --host HOST  Hostname or IP address of device to check.
  --hostlist HOSTLIST   Filename with hostnames or IP addresses to check.
  -l LIMIT, --limit LIMIT
                        Limit hosts to a subset of matching hosts
  -i INVENTORY_FILE, --inventory-file INVENTORY_FILE
                        Ansible inventory directory.
  -u USERNAME, --username USERNAME
                        name of user to connect to hubs with
  -p, --password        prompt for password
  --list-hosts          Output matching hosts, but don't excecute anything.
  --list-vars           Output matching hosts and any variables they may inherit.
  --output-file OUTPUT_FILE
                        Write all output to a file that starts with the prefix
  --output-dir OUTPUT_DIR
                        Write all output files into this directory (must exist)
  --separate            Write output to separate file per device


Unsible needs a device or set of devices to operate on.  It can read from a basic ansible invetory, or the device or a list can be specified from the command line with the "-d" switch 
or a file with a list of IP addresses can be used with the --hostlist <filename> switch. 

Specify the username to login to the device with -u, and -p to be prompted for the device password.  Then specify one of the following commands:

cli, configure, commit, rollaback, copyto, inventory, or storage

cli runs a cli command:

unsible on  main [✘!] via 🐍 v3.8.10 (ve)
❯ ./unsible.py -d 10.0.0.25 -u copek -p cli "show version"
Unsible FE ver 22.01.2024.01 - A Junos PyEZ cli frontend
Password: 
__________________________________________________
Connecting to 10.0.0.25 (10.0.0.25)...


--------------------------------------------------------------------------------
Executing cli command "show version" on 10.0.0.25
--------------------------------------------------------------------------------

Hostname: SRX300-KELLAR
Model: srx300
Junos: 21.4R3-S5.4
JUNOS Software Release [21.4R3-S5.4]

--------------------------------------------------------------------------------

unsible on  main [✘!] via 🐍 v3.8.10 (ve)took 12s 
❯ 

Running the same command on multiple hosts.  Ip addresses are contained in the /tmp/myhosts file, one IP address per line.


❯ ./unsible.py --hostlist /tmp/myhosts -u copek -p cli "show version"
Unsible FE ver 22.01.2024.01 - A Junos PyEZ cli frontend
Password: 
__________________________________________________
Connecting to 10.0.0.25
 (10.0.0.25)...


--------------------------------------------------------------------------------
Executing cli command "show version" on 10.0.0.25
--------------------------------------------------------------------------------

Hostname: SRX300-KELLAR
Model: srx300
Junos: 21.4R3-S5.4
JUNOS Software Release [21.4R3-S5.4]

--------------------------------------------------------------------------------
__________________________________________________
Connecting to 172.20.2.25
 (172.20.2.25)...


--------------------------------------------------------------------------------
Executing cli command "show version" on 172.20.2.25 --------------------------------------------------------------------------------

fpc0:
--------------------------------------------------------------------------
Hostname: EX2200-48P
Model: ex2200-48p-4g
Junos: 15.1R7-S13
JUNOS EX  Software Suite [15.1R7-S13]
JUNOS FIPS mode utilities [15.1R7-S13]
JUNOS Online Documentation [15.1R7-S13]
JUNOS EX 2200 Software Suite [15.1R7-S13]
JUNOS Web Management Platform Package [15.1R7-S13]

--------------------------------------------------------------------------------

unsible on  main [✘!] via 🐍 v3.8.10 (ve)took 20s 



The configure command allows you to use a file full of {} or set commands to configure devices.  By default, unsible will configure the device, then display a diff and ask 
the user for confirmation if the configuration should be commited.  If the configuration file is in set format, specify with the -s switch,  -y will skip the user interaction, and -c
with an integer in minutes will do a commmit confirmed instead of a commit.  -h will display more help on the configure sub commands.

An example, configuring the set commands in the /tmp/commands.set file, the first device will have a commit confirmed of 11 minutes, and the second will be skipped

❯ cat /tmp/commands.set 
set interfaces ge-0/0/0 description "UNUSED PORT"
set interfaces ge-0/0/1 description "DISABLED"
set system ntp server 10.0.0.123


unsible on  main [✘!] via 🐍 v3.8.10 (v

❯ ./unsible.py --hostlist /tmp/myhosts -u copek -p configure -s /tmp/commands.set 
Unsible FE ver 22.01.2024.01 - A Junos PyEZ cli frontend
Password: 
__________________________________________________
Connecting to 10.0.0.25
 (10.0.0.25)...


                                                                                
                                                                     Configuring 10.0.0.25
                                                                                
The following configuration will be loaded:
--------------------------------------------------------------------------------
set interfaces ge-0/0/0 description "UNUSED PORT"
set interfaces ge-0/0/1 description "DISABLED"
set system ntp server 10.0.0.123

--------------------------------------------------------------------------------
Configuration locked.
Configuration successfully loaded.
Results of a show configuration | compare rollback 0 
%%%%%%%%%%%%%%%%%%%%CONFIGURATION DIFFERENCES%%%%%%%%%%%%%%%%%%%%

[edit system ntp]
     server 185.207.105.38 { ... }
+    server 10.0.0.123;
[edit interfaces ge-0/0/0]
-   description EX2200C:ge-0/0/11;
+   description "UNUSED PORT";
[edit interfaces ge-0/0/1]
+   description DISABLED;

%%%%%%%%%%%%%%%%%%%%CONFIGURATION DIFFERENCES%%%%%%%%%%%%%%%%%%%%


Commit on 10.0.0.25 (yes to commit,integer to commmit confirmed)
Proceed?11
Commiting with confirmation timer of 11 minutes.
Remember to perform another commit or these changeswill rollback.
Commit successful.
Configuration unlocked.
__________________________________________________
Connecting to 172.20.2.25
 (172.20.2.25)...


                                                                                
                                                                    Configuring 172.20.2.25
                                                                                
The following configuration will be loaded:
--------------------------------------------------------------------------------
set interfaces ge-0/0/0 description "UNUSED PORT"
set interfaces ge-0/0/1 description "DISABLED"
set system ntp server 10.0.0.123

--------------------------------------------------------------------------------
Configuration locked.
Configuration successfully loaded.
Results of a show configuration | compare rollback 0 
%%%%%%%%%%%%%%%%%%%%CONFIGURATION DIFFERENCES%%%%%%%%%%%%%%%%%%%%

[edit interfaces ge-0/0/0]
-   description "ALIENWARE LAPTOP";
+   description "UNUSED PORT";
[edit interfaces ge-0/0/1]
-   description "TEMP - KID PC";
+   description DISABLED;

%%%%%%%%%%%%%%%%%%%%CONFIGURATION DIFFERENCES%%%%%%%%%%%%%%%%%%%%


Commit on 172.20.2.25 (yes to commit,integer to commmit confirmed)
Proceed?n
Aborting commit on 172.20.2.25
Configuration unlocked.

unsible on  main [✘!] via 🐍 v3.8.10 (ve)took 1m27s 



The commit command just performs a commit on the target device(s).  This is useful for commiting after commit confirms.

The rollback command will rollback the config, and then commiit it.  The default is a rollback of 1, but with -r you can specify different rollback numbers.

Example:  Do a rollback 3 on a device

./unsible.py -d 1.2.3.4 -u username -p rollback -r 3

The copyto command copys a file to the target device(s). This is useful for stating OS images.

❯ ./unsible.py --hostlist /tmp/myhosts -u copek copyto -h
Unsible FE ver 22.01.2024.01 - A Junos PyEZ cli frontend
usage: unsible.py copyto [-h] [-d DESTINATION]  source_file

positional arguments:
  copyto                Copy a file to a device using scp
  source_file           File to copy to devices (with optional path)

optional arguments:
  -h, --help            show this help message and exit
  -d DESTINATION, --destination DESTINATION
                        Filename or directory to copy source file to on device


Exampe: copy the junos imaage in the /tmp dir on the host to the /var/tmp dir on the target devices:

./unsible.py --hostlist /tmp/myhosts -u copek copyto /tmp/junos-srxsme-21.4R3-S7.tgz -d /var/tmp


The inventory command performs a "show chassis hardware" on the target devices.  The --xml switch can be used as a subcommand to save the output in xml format.  

./unisble.py --hostlist /tmp/myhosts -u user -p --output-file myinventory.txt inventory

./unisble.py --hostlist /tmp/myhosts -u user -p --output-file myinventory.txt inventory --xml

The storage command does a simple "request system storage cleanup" on the target devcies.






