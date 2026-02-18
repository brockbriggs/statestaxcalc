import os
from dotenv import load_dotenv

# This looks for the .env file and loads it into os.environ
load_dotenv() 

SECRET_KEY = os.environ.get('SECRET_KEY')