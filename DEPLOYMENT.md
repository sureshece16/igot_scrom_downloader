# Deployment Guide

## Deploying to Production Server

This guide explains how to deploy the iGOT SCORM Downloader to a production server.

### Prerequisites
- Python 3.8 or higher
- A web server (Nginx or Apache with reverse proxy)
- Access to the server with SSH

### Step 1: Prepare the Application

1. **Clone the repository** to your server:
```bash
cd /var/www/
git clone https://github.com/sureshece16/igot_scrom_downloader.git
cd igot_scrom_downloader
```

2. **Create a virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate     # On Windows
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure email settings** (optional):
   - Copy `email_config.py` and update with your SMTP settings
   - Set `ENABLE_EMAIL = True` if you want email notifications

### Step 2: Run with Gunicorn (Production Server)

For production deployment, use Gunicorn instead of Flask's built-in server:

```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 --threads 2 wsgi:app
```

**Explanation:**
- `--bind 0.0.0.0:5000`: Listen on all network interfaces, port 5000
- `--workers 4`: Use 4 worker processes
- `--timeout 120`: Increase timeout to 120 seconds (for long downloads)
- `--threads 2`: Use 2 threads per worker (for handling SSE connections)

### Step 3: Configure Reverse Proxy

#### Nginx Configuration

Create a configuration file `/etc/nginx/sites-available/igot_scrom_downloader`:

```nginx
server {
    listen 80;
    server_name portal.dev.karmayogibharat.net;

    # Main application location
    location /igot_scrom_downloader {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Important for Server-Sent Events (SSE)
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        
        # Increase timeouts for long-running downloads
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
        send_timeout 300;
    }

    # Static files (CSS, JS)
    location /igot_scrom_downloader/static {
        alias /var/www/igot_scrom_downloader/static;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/igot_scrom_downloader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### Apache Configuration (Alternative)

If using Apache with mod_proxy:

```apache
<VirtualHost *:80>
    ServerName portal.dev.karmayogibharat.net

    ProxyPreserveHost On
    ProxyRequests Off

    # Main application
    ProxyPass /igot_scrom_downloader http://127.0.0.1:5000/igot_scrom_downloader
    ProxyPassReverse /igot_scrom_downloader http://127.0.0.1:5000/igot_scrom_downloader

    # Static files
    Alias /igot_scrom_downloader/static /var/www/igot_scrom_downloader/static
    <Directory /var/www/igot_scrom_downloader/static>
        Require all granted
    </Directory>

    # Increase timeout for SSE
    ProxyTimeout 300
</VirtualHost>
```

### Step 4: Create Systemd Service (Auto-start)

Create `/etc/systemd/system/igot-scorm-downloader.service`:

```ini
[Unit]
Description=iGOT SCORM Downloader
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/igot_scrom_downloader
Environment="PATH=/var/www/igot_scrom_downloader/venv/bin"
ExecStart=/var/www/igot_scrom_downloader/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 --threads 2 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable igot-scrom-downloader
sudo systemctl start igot-scrom-downloader
sudo systemctl status igot-scrom-downloader
```

### Step 5: Verify Deployment

1. **Check the service is running**:
```bash
sudo systemctl status igot-scrom-downloader
```

2. **Test the application**:
   - Open browser: `https://portal.dev.karmayogibharat.net/igot_scrom_downloader`
   - Verify CSS/JS loads (check browser console F12)
   - Test a small download

3. **Check logs**:
```bash
# Application logs
sudo journalctl -u igot-scrom-downloader -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

## Troubleshooting

### CSS/JS Not Loading

1. **Check static files path**:
```bash
ls -la /var/www/igot_scrom_downloader/static/
```

2. **Verify Nginx static files alias**:
- Ensure the path in Nginx config matches your installation path
- Test direct access: `https://portal.dev.karmayogibharat.net/igot_scrom_downloader/static/styles.css`

3. **Check permissions**:
```bash
sudo chown -R www-data:www-data /var/www/igot_scrom_downloader/
```

### Download Button Not Working

1. **Check browser console** (F12 → Console tab) for JavaScript errors

2. **Verify API endpoints**:
```bash
curl https://portal.dev.karmayogibharat.net/igot_scrom_downloader/api/status
```

3. **Check Gunicorn logs**:
```bash
sudo journalctl -u igot-scrom-downloader -f
```

### Server-Sent Events (SSE) Issues

If progress updates don't work:
1. Ensure `proxy_buffering off` in Nginx config
2. Check that enough workers/threads are configured in Gunicorn
3. Verify browser supports SSE (all modern browsers do)

## Quick Restart

After making changes to the code:

```bash
cd /var/www/igot_scrom_downloader
source venv/bin/activate
git pull  # If using git
pip install -r requirements.txt  # If dependencies changed
sudo systemctl restart igot-scrom-downloader
```

## Security Recommendations

1. **Use HTTPS**: Configure SSL certificate (Let's Encrypt recommended)
2. **Firewall**: Only open necessary ports (80, 443)
3. **Authentication**: Consider adding login/authentication if needed
4. **File permissions**: Ensure proper ownership and permissions
5. **Regular updates**: Keep dependencies updated

## Support

For issues or questions, check:
- Application logs: `sudo journalctl -u igot-scrom-downloader -f`
- Nginx logs: `/var/log/nginx/`
- GitHub Issues: https://github.com/sureshece16/igot_scrom_downloader/issues
