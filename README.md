# discord-credit-bot

## How to run
### Prerequisites
- Install [poetry](https://python-poetry.org/docs/#installation)
- Set up the discord bot user through Discord dev portal (first part of [this](https://realpython.com/how-to-make-a-discord-bot-python/#how-to-make-a-discord-bot-in-python) guide covers it)
- Enable required intents in developer portal in the **Bot** tab under **Privileged Gateway Intents** - more info [here](https://discordpy.readthedocs.io/en/latest/intents.html?highlight=intents) in the docs

Once that's all set up, navigate to root of the repository and run:
```
# Copy example.env to repo root and fill out values for the bot from developer portal
cp env/example.env .env

# Install dependencies
poetry install

# Run the app
poetry run python src/main.py
```

Alternatively, if you have Make installed just use the Makefile:
```
make install && make run
```

## What is it?
A discord bot to keep track of feedback 'credits' - the use-case is intended for creative groups where there's a feedback loop. Kind of like a, I'll read yours if you read mine, kinda thing.

## Why?
Practice and fun mostly. Not intended for anything other than small tinkering. 

