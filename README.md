Proof of concept project to develop a web-based data transfer tool from
Nightscout databases to Open Humans and other platforms.

This website is intended for deployment on Heroku at:
https://dataxfer-ns-oh.herokuapp.com/

### Running locally

To develop this site, you can run this app locally with foreman...

#### Creating a project on Open Humans

If you want to develop locally, you'll probably want to create your own
OAuth2 project in Open Humans to get a new `client_id` and
`client_secret`.

(You can't reuse the IDs for the project/app running on Heroku, because
Open Humans requires OAuth2 projects to register their redirect_uri.)

Follow the instructions here: https://www.openhumans.org/direct-sharing/oauth2-setup/

**You should probably set your project's redirect URI to: http://127.0.0.1:5000/**
&ndash; this is the URI the app will default to when you run Flask locally.

#### Configure .env for OAuth2.

Copy `env.example` to `.env`.

Replace `CLIENT_ID` and `CLIENT_SECRET` to match your app.

#### Set up Python environment

Set up a virtual environment with virtualenv (optional but highly recommended). Use pip to install `requirements.txt`.

(If these are unfamiliar tools, you can search & find various guides on installing and using pip, virtualenv, and virtualenvwrapper.)

#### Install and run with foreman

`Procfile` and `.env` files are used by foreman. You can install foreman
to run this app locally.

Read more about installing foreman here: https://github.com/ddollar/foreman

Once installed, you can run this command in the project's base directory: `foreman start`

Your local site can be loaded by opening a web browser and visiting http://127.0.0.1:5000/
