echo -e "\e[1;35mCode auto formatting...\e[0m"
python3 -m black .
python3 -m isort .
echo -e "\e[1;35mCode linting...\e[0m"
python3 -m flake8 air --max-line-length=120
python3 -m pylint air --max-line-length=120 --ignore=custom_sense_hat.py --disable=too-few-public-methods
echo -e "\e[1;35mCode type checking...\e[0m"
python3 -m mypy air
