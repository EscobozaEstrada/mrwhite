# Mr White Dev Container (Python 3.11)

This Dev Container mirrors the App Runner Python 3.11 revised build expectations.

- Deps are installed at container creation via `.devcontainer/setup.sh` using `pip3`.
- Run the backend just like App Runner:

```
cd backend
gunicorn --config gunicorn.conf.py wsgi:application
```

Port 5001 is forwarded.

If you need AWS SSM/Secrets access locally, export AWS credentials in your VS Code environment (or use `aws sso login`) before opening the container.
