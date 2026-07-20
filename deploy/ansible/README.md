Ansible playbook — provision and deploy

Usage (basic):

1. Install Ansible on your control node:

```bash
python -m pip install ansible
```

2. Edit `deploy/ansible/inventory.ini` and set your server IP.
3. Copy `deploy/process_email_queue.env.example` to a secure file and edit values.
4. Run the playbook:

```bash
ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/site.yml --extra-vars "deploy_path=/opt/bookmyseat"
```

Notes:
- This playbook is intentionally simple. For production, use vault/secret storage for `env` files.
- It configures Docker, copies compose and nginx config, pulls images, runs containers, and performs DB migrations and `collectstatic`.
- Ensure the remote user has sudo privileges and SSH key access.
