# Lift Log

Lift Log is a progress tracking app for gym enthusiasts.
You can import exercise sets from a source like Apple Notes, and visualize the
progress over time of each exercise.

![screenshot_my_sets](./images/screenshot_my_sets.png)
![screenshot_import_sets](./images/screenshot_import_sets.png)


## How to run Lift Log


### Prerequisites:

- Python 3.10+
- Make sure you can run `python` and see version 3.10+

### Initial Setup

The app isn't neatly packaged (yet). The ideal way to set up the app is:

1. Clone the project. `git clone git@github.com:ben31w/lift-log.git`
2. Create virtual environment. `python -m venv .venv`
3. Activate virtual environment. `source .venv/bin/activate`
4. Install dependencies. `pip install -r requirements.txt`

### Running

Once set up, the ideal way to run the app is:

1. `./run.sh`


## How to use Lift Log


### 1. Import Sets

Exercise sets can be imported via the following methods: 
- Apple Notes
- HTML file

To import via Apple Notes, you must be running on macOS. If you are like me and
don't have a macOS computer, look into setting up a VM: 
https://www.makeuseof.com/macos-ubuntu-linux-virtual-machine/

Otherwise, you can import an HTML file. The `html` directory contains example 
HTML files with my exercise sets and other mock data.

Regardless of the import method, the exercise sets within Apple Notes or the 
HTML file must follow this syntax:
- exercise: Reps,SetxReps@Weight, SetxReps,~Reps@AnotherWeight, ...
- exercise: Reps,SetsxReps,~Reps  (no weight)

Examples: 
- bench press: 2x10@135, 2x8@145, ~5@155
- pull ups: 10,2x8,~7

Notes:
- You can also have comments at the end of each line that will be ignored.
- '~' is an acceptable syntax that indicates partial reps.
- Regarding the required syntax, the following substitutions are acceptable: 
    - ':' and '-'
    - ',' and ';'
    - '@' and ' at '
- If importing via Apple Notes, all your notes will be read. Only notes with names 
  starting in a M/D or M/D/Y date (ex: '1/1', '2/1/24 pull') will be considered 
  valid workout notes. All other notes will be ignored.

### 2. Have fun

Once you have imported some exercise sets, Lift Log generates progress plots.
You can view the progress plots, and edit individual exercise sets or imports
at any time.


## Inspiration


Since 2021, I've used my phone to jot down my exercise sets. I have several 
years of personal exercise data in Apple Notes. But Apple Notes isn't great for
visualizing progressive overload/progress over time. Also, the search 
functionality in Apple Notes is also atrocious: it often returns results that 
don't match your search at all!

To solve this problem, I developed an app that could ingest 
exercise data from Apple Notes and produce visualizations. I'm not 
sure how useful of a fitness tool this will end up being. But the project 
combines my passions for fitness and programming, and I've enjoyed it a lot
so far. 
