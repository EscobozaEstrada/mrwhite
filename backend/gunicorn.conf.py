# Gunicorn configuration file for Mr White Backend - App Runner optimized

# Server socket (App Runner expects port 8080)
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes (optimized for App Runner)
workers = 2  # Reduced for App Runner resource constraints
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increased from 30 to 120 seconds for AI processing
graceful_timeout = 30  # Added graceful shutdown timeout
keepalive = 5  # Increased from 2 to 5 seconds
max_requests = 1000
max_requests_jitter = 50

# Restart workers after this many requests, to help prevent memory leaks
preload_app = True

# Logging (App Runner compatible paths)
accesslog = "-"  # Log to stdout for App Runner
errorlog = "-"   # Log to stderr for App Runner
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "mrwhite_backend"

# Server mechanics (App Runner compatible)
daemon = False
# pidfile removed - not needed in App Runner containers
# user/group removed - App Runner manages this
tmp_upload_dir = None

# SSL (if needed in future)
# keyfile = None
# certfile = None 