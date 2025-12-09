# Steps followed to create project structure and installation of django
1. checked for python version "python --version"
2. change to my project directory and created virtual environment using "python -m venv venv"
3. Activated using "..\venv\Scripts\activate "
4. Installed django using "pip install django"
5. Created a django project using "django-admin startproject Expense_tracker ."
6. Run the django development server "python manage.py runserver"
7. Created app_new using python manage.py startapp app_new"
8. Added my app_new in INSTALLED_APPS in settings.py
9. Initializing database tables using "python manage.py migrate"

Other additional packages Installations-
#install DRF
pip install djangorestframework

#Install external python package- dateutil
pip install python-dateutil

#To allow frontend to access APIs - 
pip install django-cors-headers
---------------------------------------------------------

**Steps to follow to run backend Code**
cd folder
cd backend
..\venv\Scripts\activate
pip install django
pip install djangorestframework
pip install python-dateutil
pip install django-cors-headers
python manage.py runserver


