echo -e "\e[1;35mCode auto formatting...\e[0m"
poetry run black .
poetry run isort .
echo -e "\e[1;35mCode linting...\e[0m"
poetry run flake8 utilities --max-line-length=120
poetry run pylint utilities --max-line-length=120
echo -e "\e[1;35mCode type checking...\e[0m"
poetry run mypy utilities
