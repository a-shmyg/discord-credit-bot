install:
	poetry install

run:
	poetry run python src/main.py

lint:
	poetry run black src/*
	poetry run isort src/*

# clean:
# 	docker stop $(docker ps -aq)
# 	docker container rm -f $(docker container ls -aq)
# 	docker volume rm -f $(docker volume ls -q)