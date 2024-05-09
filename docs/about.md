# Documentation for the netascode-dc-vxlan Ansible Collection

Infrastructure as code (IaC) is a DevOps methodology that uses code to manage and provision IT infrastructure, instead of manual procedures. IaC uses a descriptive coding language to automate provisioning servers, operating systems, network devices and more. The NetAsCode VXLAN EVPN collection allows you to configure, in easy to understand YAML, data structures with the intended configuration state of a VXLAN fabric using Cisco Nexus Dashboard Fabric Controller.

The NetAsCode VXLAN collection provides the capability to create a declarative method of configuration of VXLAN for [Cisco Nexus](https://www.cisco.com/site/us/en/products/networking/cloud-networking-switches/index.html) datacenter solution utilizing [Cisco Nexus Dashboard](https://www.cisco.com/site/us/en/products/networking/cloud-networking/nexus-platform/index.html). This allows the separation of data from execution logic. With little to no knowledge about automation, you can instantiate a VXLAN EVPN fabric with this collection.

This is achieved by creating YAML files that contain a pre-determined data schema that is translated into underlying Ansible modules and resources. The core Ansible collection is open source and available 

> **Note**: For complete support and additional capabilities, Cisco provides a profesional services capability under the Services as Code umbrella. TAC support is provided for the underlying Ansible modules.

## Setting up environment for the collection

The first procedure for local execution of the collection is going to be the installation of a virtual environment to be able to install the collection and it's requirements. Recomendation is to utilize [pyenv](https://github.com/pyenv/pyenv) which provides a robust python virtual environment capability that also includes management of python versions. These instructions will be detailed around pyenv.



## Step 1 - Installing the example repository

To simplify the usage of the collection we are providing you with an [example repository](https://github.com/netascode/ansible-dc-vxlan-example) that you can clone from github which creates the proper skeleton required, including beneficial examples for pipelines. To clone the repository requires the installation of [git client](https://git-scm.com/downloads) that is available for all platforms.

Run the following command in the location of interest.

```bash
git clone https://github.com/netascode/ansible-dc-vxlan-example.git nac-vxlan
```

This will clone the repository into the directory nac-vxlan.

## Step 2 - Create the virtual environment with pyenv

In this directory you will now create the new virtual environment. For pyenv to work you have to install a version of Python that you want to utilize. At the _time of this writting_, a common version utilized is python version 3.10.13 so to install this with pyenv would be the command `pyenv install 3.10.13`. For detailed instructions please visit the [pyenv](https://github.com/pyenv/pyenv) site.

```bash
cd nac-vxlan
pyenv virtualenv <python_version> nac-ndfc
pyenv local nac-ndfc
```

The final command is `pyenv local` which sets the environment so that whenever you enter the directory it will change into the right virtual environment.

## Step 3 - Install Ansible and additional required tools

Included in the example repository is the requirements file to install ansible. First upgrade PIP to latest version.

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 4 - Install Ansible Galaxy collections

```bash
ansible-galaxy collection install -p collections/ansible_collections/ -r requirements.yml
```

## Step 5 - Ensure proper python interpreter for Ansible

Using the envirnoment variable $PYENV_VIRTUAL_ENV from pyenv you should be able to locate the proper path that will be needed to be set in the `ansible.cfg` file.

```bash
echo $PYENV_VIRTUAL_ENV/lib/
```

Which is going to tell you the path for all the python modules and libraries of the virtual environment that was created. If you look in that directory you will find the collections package locations. Here is the base ansible.cfg, you will need to adjust the collection_path to your environment paths:

```bash
[defaults]
collections_path = $PYENV_VIRTUAL_ENV/lib/python3.10/site-packages/ansible/collections:./collections/ansible_collections/

# callback_whitelist=ansible.posix.timer,ansible.posix.profile_tasks,ansible.posix.profile_roles
# callbacks_enabled=ansible.posix.timer,ansible.posix.profile_tasks,ansible.posix.profile_roles
# bin_ansible_callbacks = True
```
