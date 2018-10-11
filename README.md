# Nightscout to Open Humans Data Transfer Tool

Proof of concept project to develop a web-based data transfer tool from
Nightscout databases to Open Humans and other platforms.

This website is intended for deployment on Heroku at:
https://dataxfer-ns-oh.herokuapp.com/

### Local Setup and Development

#### Creating a project on Open Humans

First you will need an Open Humans project to test and develop on. You can set up a project here: https://www.openhumans.org/direct-sharing/projects/oauth2/create/

The `Enrollment URL` would be a link to a final app page (http://yourapp.herokuapp.com) once development is complete. You can pick or use a dummy name in the meantime.

Set the `Redirect URL` to exactly: `http://127.0.0.1:5000/complete`

Once created, you can go to https://www.openhumans.org/direct-sharing/projects/manage/ and click on the project name. You will find your `client_id` and`client_secret` here.

For more information on OAuth2 setup, go to: https://www.openhumans.org/direct-sharing/oauth2-setup/

#### Installation and configuration

These instructions expect you to be using the following. Make sure it's set
up for your system first!

* `pipenv` for local Python development (`brew install pipenv` on Mac)
* the Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli (`brew install heroku/brew/heroku` on Mac)
  *  Make sure to create a Heroku account if you don't have one, and log in.

Local setup:

1. Download the git repository, e.g. using `git clone`.
2. Navigate to be inside the repository base directory. Check also to make sure you're on the correct branch, in case you're using a dev branch instead of master.
3. Start a local pipenv shell with `pipenv shell`
4. Run `pipenv install` to install any needed dependencies automatically.
5. Copy the environment variable file using `cp env.example .env`
6. Open the `.env` file (`vi .env`) and edit to replace `CLIENT_ID` and `CLIENT_SECRET` with your project's matching ID and SECRET (see above)
7. Initialize the database locally with `heroku local:run python manage.py migrate`

#### Running the app locally

Inside the repository base, run: `heroku local`.

The app should be available in a local web browser at: http://127.0.0.1:5000 (if you have amqp; if not, you'll get a 500 Server error. Move on to Heroku deployment below. )

### Deployment to Heroku

Create a new app in Heroku, and link it to your own repository (connect to Github first inside Heroku) or use the Heroku-CLI to upload files to the heroku server.

#### Config in Open Humans

Once you have your heroku app created, go to https://www.openhumans.org/direct-sharing/projects/manage/ and click on the `edit` button next to your project name. Set the `Redirect URL` to exactly: `https://your-app-name.herokuapp.com/complete`

#### Config in Heroku

1. You should add the following local environment variables in the Config Vars section of your heroku app:
  * `APP_BASE_URL`: Set this to exactly https://your-app-name.herokuapp.com
  * `OH_ACTIVITY_PAGE` (optional): https://www.openhumans.org/activity/your-project-name
  * `OH_CLIENT_ID`: Your Client ID
  * `OH_CLIENT_SECRET`: Your Client Secret
  * `SECRET_KEY` : Something long and random
  * `PYTHONUNBUFFERED` : true
2. Deploy your git repository to git (e.g. `git push heroku master`. Note you may need to set the remote, and do a `git pull`, before you can push.)
3. On the Resources tab for your app, edit the Celery Worker to be active. (This may take some time to appear.)
4. On the same Resources tab, add a CloudAMQP add-on and use the "Little Lemur" version.
5. Initialize your database with `heroku run 'python manage.py migrate'`

Setup is now complete and the Heroku app should hopefully work!
