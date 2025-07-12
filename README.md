# Lift Log

Lift Log is an app that enables you to visualize your exercise sets and 
progress at the gym.

![screenshot_my_sets](./images/screenshot_my_sets.png)
![screenshot_import_sets](./images/screenshot_import_sets.png)

## How it works

You add your exercise sets by importing them. Lift Log organizes 
the sets and produces scatter plots. Each exercise is given four scatter plots:
- Load over time for sets with 1-5 reps
- Load over time for sets with 6-8 reps
- Load over time for sets with 9-11 reps
- Load over time for sets with 12+ reps

As of now, the only supported method for importing exercise sets is via 
an HTML file. Currently, there is a sample HTML file containing my exercise data.

## Setup + Running

Prerequisite: Python 3.10+

The app isn't neatly packaged (yet). The ideal way to set up the app is:
1. Clone the project.
2. Create virtual environment. `python -m venv .venv`
3. Activate virtual environment. `source .venv/bin/activate`
4. Install dependencies. `pip install -r requirements.txt`

Once set up, the ideal way to run the app is:
1. Activate virtual environment. `source .venv/bin/activate`
2. `python src/app.py`

## Inspiration

Since 2021, I've used my phone to jot down my exercise sets. I have several 
years of personal exercise data in Apple Notes. But Apple Notes isn't great for
visualizing progressive overload/progress over time :/

To solve this problem, I started developing an app that could ingest 
exercise data from Apple Notes and produce appealing visualizations. I'm not 
sure how useful of a fitness tool this will end up being. But the project 
combines my passions for fitness and programming, and I've enjoyed it a lot
so far. 

## TODOs
- Allow user to import sets directly from Apple Notes
  - Start off assuming the app is run on macOS... 
  - Maybe it's possible to containerize the app in macOS.
- Package the app + dependencies
- Containerize this app, so the user doesn't need a specific version of Python
- Reduce logging/fix up levels
- Image processing (advanced)