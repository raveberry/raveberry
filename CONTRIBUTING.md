# Quick start for contributors

This file is meant for new contributors to get a fast start as a dev in this project.

## Dependencies for development

Install dependencies for raveberry (if not already installed for running raveberry before)
```
wget -q -O - https://apt.mopidy.com/mopidy.gpg | sudo apt-key add -
sudo wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/buster.list
sudo apt-get update
sudo apt-get install -y python3-pip ffmpeg atomicparsley mopidy redis-server libspotify-dev libglib2.0-dev libgirepository1.0-dev libcairo2-dev gstreamer1.0-plugins-bad
pip3 install raveberry
```

Extra dependencies for development
```
wget -q -O - https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
sudo echo "deb https://dl.yarnpkg.com/debian/ stable main" > sudo /etc/apt/sources.list.d/yarn.list
sudo apt-get update
sudo apt-get install -y git python3-venv yarn
```

On a Raspberry Pi 4 with Buster light a wrong yarn version could be installed. To fix this problem, use
```
sudo apt remove yarn
curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
sudo apt-get update  
sudo apt-get install yarn
```

## Setup Github

Configure git (if not already done for another github project)
https://kbroman.org/github_tutorial/pages/first_time.html

Fork repository on github from https://github.com/raveberry/raveberry/

Clone your own forked repository
```
git clone https://github.com/stappjno/raveberry.git
```

Add remote upstream source (original repo!)
```
cd raveberry/
git remote add upstream https://github.com/raveberry/raveberry.git
```

## Create a branch
Make sure your local and forked repo are in sync with the original repo
```
git pull upstream master && git push origin master
```

Create branch, use "bugfix" or "feature" as type and replace "readme-update" with whatever you are working on
```
git checkout -b feature/readme-update
```

## Start virtual enviroment for development


Create new virtual enviroment for python development
```
python3 -m venv .venv
```

Use new virtual Enviroment (required each time you start a bash session)
```
. .venv/bin/activate
```

Install minimal dependencies
```
cd raveberry/
pip3 install wheel
pip3 install -r requirements/common.txt
```

If you need all dependencies (testing, visualization, type checking etc.), also run
```
pip3 install -r requirements/dev.txt
```

If you want to develop in the frontend (change scss files), enable the sass processor so changes are visible immediately.
In `main/settings.py`, change the value of `SASS_PROCESSOR_ENABLED` from `False` to `True`.

Start development server
```
bin/raveberry run
```

If you get a sass error, install yarn dependencies
```
yarn install
```

Now you should be able to run the development server again with
```
bin/raveberry run
```

Fix the issue / add the feature described in your branch

## Push & PR

Push your branch to your forked repo
```
git push -u origin feature/readme-update
```

Navigate with your browser to your fork on github and "compare & pull request"
Give your PR a good title and description that we can see what you've added / fixed
Check if the diff of your changes is what you expected
Push the "Create pull request" button!
