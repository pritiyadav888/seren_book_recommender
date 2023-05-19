import os
import subprocess
from getpass import getpass
import logging

# Set up logging
logging.basicConfig(filename='deploy.log', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

def run_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode('utf-8'), stderr.decode('utf-8'), process.returncode

def create_requirements():
    stdout, stderr, exitcode = run_cmd("pip freeze > requirements.txt")
    if exitcode == 0:
        logging.info("requirements.txt has been successfully created/updated")
    else:
        logging.error(f"An error occurred during requirements.txt creation: {stderr}")
        return exitcode

def create_procfile():
    if not os.path.isfile('Procfile'):
        with open('Procfile', 'w') as f:
            f.write('web: gunicorn app:app')
        logging.info("Procfile has been successfully created")
    else:
        logging.info("Procfile already exists")

def push_to_heroku(heroku_app_name):
    commands = [
        "git init",
        "heroku git:remote -a " + heroku_app_name,
        "git add .",
        "git commit -m 'deploying to heroku'",
        "git push heroku main"
    ]

    for cmd in commands:
        stdout, stderr, exitcode = run_cmd(cmd)
        if exitcode != 0:
            logging.error(f"An error occurred during executing '{cmd}': {stderr}")
            return exitcode
        logging.info(stdout)

def create_heroku_app(heroku_app_name):
    stdout, stderr, exitcode = run_cmd(f"heroku create {heroku_app_name}")
    if exitcode == 0:
        logging.info(f"Heroku app create")
        print(f"Heroku app '{heroku_app_name}' has been successfully created")
    else:
        print(f"An error occurred during Heroku app creation: {stderr}")
        return exitcode

def main():
    heroku_app_name = getpass("Enter your Heroku app name: ")
    run_cmd("python3 -m venv venv")
    run_cmd("source venv/bin/activate")
    run_cmd("pip install -r requirements.txt")
    # create_requirements()
    create_procfile()
    create_heroku_app(heroku_app_name)
    push_to_heroku(heroku_app_name)

if __name__ == "__main__":
    main()
