# Nightscout to Open Humans Data Transfer Tool

Proof of concept project to develop a web-based data transfer tool from
Nightscout databases to Open Humans and other platforms.

This website is intended for deployment on Heroku at:
https://dataxfer-ns-oh.herokuapp.com/

### Local Setup and Development

To develop this tool, you can run this app locally by following the instructions below or by using the Heroku-CLI.

#### 1. Creating a project on Open Humans

First you will need an Open Humans project to test and develop on. You can set up a project here: https://www.openhumans.org/direct-sharing/projects/oauth2/create/

The `Enrollment URL` will be a link to your final app page (http://yourapp.herokuapp.com) once development is complete. 

Set the `Redirect URL` to exactly: http://127.0.0.1:5000/complete/

Once created, you can go to https://www.openhumans.org/direct-sharing/projects/manage/ and click on the project name. You will find your `client_id` and`client_secret` here.

For more information on OAuth2 setup, go to: https://www.openhumans.org/direct-sharing/oauth2-setup/

#### 2. Install Dependencies

A number of software depenencies are required to develop locally with foreman. You can install them using the following commands:

```sudo apt-get install rabbitmq-server
sudo apt-get install python-dev
sudo apt-get install libpq-dev
sudo gem install foreman
sudo apt-get install virtualenv
```

#### 3. Configure Local Environment Variables

Download the repository and then copy the enviornment variable file using `cp env.example .env`

Open the `.env` file and replace `CLIENT_ID` and `CLIENT_SECRET` with your project's matching ID and SECRET. 

#### 4. Setup Local Virtual Environment

Use `virtualenv venv` to create a new virtual environment file.

Enter the virtual environment with `source venv/bin/activate`.

Install the requirements using `pip install -r requirements.txt`.

Finally run `python manage.py migrate`.
 

#### 5. Start Local Server

Startup your local server in the virtual environment by typing `foreman start`.

Your local site can be loaded by opening a web browser and visiting http://127.0.0.1:5000/

`Ctrl-C` to quit foreman and `deactivate` to exit the virtual environment.

### Deployment to Heroku

Create a new app in Heroku, and link it to your own repository or use the Heroku-CLI to upload files to the heroku server.

Once you have your heroku app setup, go to https://www.openhumans.org/direct-sharing/projects/manage/ and click on the `edit` button next to your project name. Set the `Redirect URL` to exactly: https://your-app-name.herokuapp.com/complete/

Next you will need to add the following local enviornment variables in the Config Vars section of your heroku app:

`APP_BASE_URL`: Set this to exactly https://your-app-name.herokuapp.com

`OH_ACTIVITY_PAGE`: https://www.openhumans.org/activity/your-project-name

`OH_CLIENT_ID`: Your Client ID

`OH_CLIENT_SECRET`: Your Client Secret

`HEROKU_APP`: true

`SECRET_KEY` : your_secret_key_here (see http://www.howtogeek.com/howto/30184/10-ways-to-generate-a-random-password-from-the-command-line/)

`PYTHONUNBUFFERED` : true

On the Resources tab for your app, edit the Celery Worker to be active. After this, add a CloudAMQP add-on and use the "Little Lemur" version.


Setup is now complete.
