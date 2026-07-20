# Deployment notes — BookMySeat email worker

This document describes how to run the email queue worker (`process_email_queue`) and deploy the systemd unit created in `deploy/process_email_queue.service`.

1) Environment and secrets
- Copy `.env.example` to `.env` and populate secrets (do NOT commit `.env`).
- Required secrets for SMTP: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`.
- For SendGrid via AnyMail: set `SENDGRID_API_KEY` and optionally `EMAIL_BACKEND=anymail.backends.sendgrid.EmailBackend`.
- For AWS SES: set `AWS_SES_ACCESS_KEY_ID`, `AWS_SES_SECRET_ACCESS_KEY`, and `AWS_SES_REGION_NAME`.

2) Recommended packages
- Provider packages are listed in `requirements/email-providers.txt`.
- Install via `pip install -r requirements/email-providers.txt`.

3) systemd unit
- Edit `deploy/process_email_queue.service` to set `WorkingDirectory` to your project path and `ExecStart` to the full path of your Python venv and `manage.py` command.
- Place the file at `/etc/systemd/system/process_email_queue.service` then run:
```bash
sudo systemctl daemon-reload
sudo systemctl enable process_email_queue.service
sudo systemctl start process_email_queue.service
sudo journalctl -u process_email_queue -f
```

4) Running manually
```bash
# from project root
python manage.py process_email_queue --limit 200
```

5) Monitoring
- Email worker logs to `logs/email.log` (see `LOGGING` in `bookmyseat/settings.py`).
- Use `python manage.py process_email_queue --stats` to inspect queue counts.

6) Notes
- Use `transaction.on_commit` to enqueue only after DB commit; the web request is non-blocking.
- Ensure that your worker runs with the same virtualenv and environment variables as your web process.

EnvironmentFile for systemd
--------------------------------
Create a protected environment file (example: `/etc/bookmyseat/env`) containing environment variables for the service. A template is provided at `deploy/process_email_queue.env.example`.

Example systemd setup
----------------------
Place the `deploy/process_email_queue.service` unit in `/etc/systemd/system/` and the env file at `/etc/bookmyseat/env` (owned by root, mode 600).

Edit the unit to include the `EnvironmentFile` line, e.g.:
```
[Service]
EnvironmentFile=/etc/bookmyseat/env
ExecStart=/path/to/venv/bin/python /path/to/project/manage.py process_email_queue --limit 200
```
Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable process_email_queue.service
sudo systemctl start process_email_queue.service
sudo journalctl -u process_email_queue -f
```

Docker Compose, Nginx and Let's Encrypt
---------------------------------------
A production-ready `docker-compose.prod.yml` is provided. It runs `web`, `worker`, `db`, `nginx`, and `certbot` services. Adjust `IMAGE_NAME`, `WorkingDirectory`, and volumes as necessary.

To obtain a certificate with certbot manually (first-time only):
```bash
# Stop nginx container temporarily if running
docker-compose -f docker-compose.prod.yml stop nginx

# Use certbot to request certs (example)
docker run --rm -v $(pwd)/deploy/nginx:/etc/nginx/conf.d -v cert-data:/etc/letsencrypt -it certbot/certbot certonly --webroot -w /var/www/certbot -d your.domain.com --email you@domain.com --agree-tos

# Restart nginx
docker-compose -f docker-compose.prod.yml up -d nginx
```

CI/CD
-----
The repository includes a GitHub Actions workflow `.github/workflows/cd.yml` which builds and pushes Docker images (Docker Hub) and then SSHs to the server to run `docker-compose pull` and `up -d`.

You must add the following repository secrets in GitHub: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `SSH_PORT` (optional), and `DEPLOY_PATH` (remote compose directory).

SendGrid webhook
----------------
After you verify your sending domain in SendGrid, configure an Event Webhook pointing to:

	https://your.domain.com/webhooks/sendgrid/events/

Select events you want (delivered, bounce, dropped, open, click, spamreport, unsubscribe).
SendGrid will sign event requests; AnyMail can verify signatures if configured. Our endpoint will
persist events to `EmailEvent` and attempt to associate them with `EmailTask` records.

Ensure your reverse proxy (nginx) forwards POSTs to `/webhooks/sendgrid/events/` to the web service.
