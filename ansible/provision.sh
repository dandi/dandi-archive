#!/bin/bash
set -e

# Download Ansible roles
ansible-galaxy install \
               --force \
               --role-file=./requirements.yml \
               --roles-path=./roles

# Run Ansible playbook
ansible-playbook \
    --inventory=./hosts.yml \
    ./playbook.yml
