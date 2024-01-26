echo -e "\e[1;35mCode auto formatting...\e[0m"
poetry run black .
poetry run isort .
echo -e "\e[1;35mCode linting...\e[0m"
poetry run flake8 utilities --max-line-length=120 --exclude=custom_sense_hat.py
poetry run pylint utilities --max-line-length=120 --ignore=custom_sense_hat.py --disable=too-few-public-methods
echo -e "\e[1;35mCode type checking...\e[0m"
poetry run mypy utilities
