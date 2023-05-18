import os
import subprocess
from getpass import getpass

def run_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode('utf-8'), stderr.decode('utf-8'), process.returncode

def check_git_changes():
    stdout, stderr, exitcode = run_cmd("git status")
    if "nothing to commit, working tree clean" in stdout:
        print("There are no changes to commit.")
        return False
    else:
        print("There are changes to commit.")
        return True

def create_requirements():
    stdout, stderr, exitcode = run_cmd("pipreqs ./ --force")
    if exitcode == 0:
        print("requirements.txt has been successfully created/updated")
    else:
        print(f"An error occurred during requirements.txt creation: {stderr}")
        return exitcode


def create_procfile():
    if not os.path.isfile('Procfile'):
        with open('Procfile', 'w') as f:
            f.write('web: python app.py')
        print("Procfile has been successfully created")
    else:
        print("Procfile already exists")


def push_to_heroku(heroku_app_name):
    if not check_git_changes():
        print("Skipping push to Heroku due to lack of changes.")
        return

    commands = [
        "git init",
        "heroku git:remote -a " + heroku_app_name,
        "git add .",
        "git commit -m 'deploying to heroku'",
        "git push heroku master"
    ]

    for cmd in commands:
        stdout, stderr, exitcode = run_cmd(cmd)
        if exitcode != 0:
            print(f"An error occurred during pushing to Heroku: {stderr}")
            return exitcode
        print(stdout)


def create_heroku_app(heroku_app_name):
    stdout, stderr, exitcode = run_cmd(f"heroku create {heroku_app_name}")
    if exitcode == 0:
        print(f"Heroku app '{heroku_app_name}' has been successfully created")
    else:
        print(f"An error occurred during Heroku app creation: {stderr}")
        return exitcode


def main():
    heroku_app_name = getpass("Enter your Heroku app name: ")
    create_requirements()
    create_procfile()
    create_heroku_app(heroku_app_name)
    push_to_heroku(heroku_app_name)


if __name__ == "__main__":
    main()
