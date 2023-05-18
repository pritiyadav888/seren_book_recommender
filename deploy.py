import os
import subprocess
from getpass import getpass
import openai
openai.api_key = os.getenv('OPENAI_API_KEY')

def run_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode('utf-8'), stderr.decode('utf-8'), process.returncode

def resolve_errors_with_gpt(error_message):
    # try to find a solution up to 10 times
    for attempt in range(10):
        # ask GPT-3 for advice on how to resolve the error
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant.",
                },
                {
                    "role": "user",
                    "content": f"I encountered this error when deploying my app to Heroku: {error_message}. What could be causing this error and how can I fix it?",
                },
            ],
        )

        advice = response.choices[0].message['content']

        print(f"GPT-3 advice: {advice}")

        # apply the advice from GPT-3
        stdout, stderr, exitcode = run_cmd(advice)

        if exitcode == 0:
            # if the advice worked, break the loop
            print("The advice worked. Continuing with the deployment...")
            return
        else:
            # if the advice didn't work, let GPT-3 know and ask for new advice
            print(f"The advice didn't work. Error: {stderr}")
            error_message = f"The advice didn't work. Here's the new error message: {stderr}"

    print("GPT-3 was unable to resolve the error after 10 attempts.")
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
            print(f"An error occurred during executing '{cmd}': {stderr}")
            resolve_errors_with_gpt(stderr)
            # if still unresolved, return from the function
            if exitcode != 0:
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
