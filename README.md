# A simple home camera recorder/viewer.
![Screenshot of app](./doc/screenshot.png)

This is a simple camera recording and display implementation using Python/Flask/SQLite. I built this because I wanted to host my own recording for my home security cameras, and felt like the existing open source software that I could find was bigger/heavier than I wanted. I run this on a Raspberry Pi.

## Installation

Designed to be hosted on a RPi device. 
Make sure that the following packages are installed on your RPi:
- python3-bcrypt
- python3-flask
- python3-flask-login
- python3-opencv
- gunicorn
- nginx
- supervisor
- ffmpeg

Copy the contents of the src/ folder to your directory structure.

Create the user "camuser":
```bash
sudo adduser camuser --shell /sbin/nologin
sudo chown -R camuser:camuser /srv/http
```

Also, make sure that the user:group of your desired recording location is also camuser:camuser

Restart nginx and supervisor services.

To check on status in terminal:
```bash
sudo systemctl status nginx
sudo systemctl status supervisor
sudo supervisorctl status all
```
## Usage
- In a browser, go to your server's address.
- The first time you visit, the app will have you create an admin account
- Click on 'Admin' to configure what cameras you have. Note that this accesses the cameras through URLs, so you need to figure out a fully formed URL for both the video stream and to capture a still.
- On the Admin page you can also manage more users: "View" users can access the index and videos pages, but only can change their own password on the admin page. "Configure" users can do all viewing plus configure the cameras. Only admins can do the user management.
