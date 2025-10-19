# Gunicorn configuration file for Mr White Backend

# Server socket
bind = "0.0.0.0:5001"
backlog = 2048

# Worker processes
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# Restart workers after this many requests, to help prevent memory leaks
preload_app = True

# Logging
accesslog = "/home/ubuntu/Mrwhite/Mr-White-Project/backend/logs/gunicorn_access.log"
errorlog = "/home/ubuntu/Mrwhite/Mr-White-Project/backend/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "mrwhite_backend"

# Server mechanics
daemon = False
pidfile = "/home/ubuntu/Mrwhite/Mr-White-Project/backend/logs/gunicorn.pid"
user = "ubuntu"
group = "ubuntu"
tmp_upload_dir = None

# SSL (if needed in future)
# keyfile = None
# certfile = None 