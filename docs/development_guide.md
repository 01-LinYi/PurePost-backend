# Development Guide for Django App

## Prerequisites

- Python 3.10+
- Django 4.x or higher
- pip (Python package installer)
- Virtualenv (optional but recommended)

## Setting Up the Development Environment

1. **Clone the Repository**

   ```bash
   git clone https://github.com/01-LinYi/PurePost-backend.git
   cd PurePost-backend
   ```

2. **Create and Activate Virtual Environment**

   ```bash
   python3 -m venv env
   source env/bin/activate  # On Windows use `env\Scripts\activate`
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up the Database**

   ```bash
   python manage.py migrate
   ```

5. **Create a Superuser**

   ```bash
   python manage.py createsuperuser
   ```

6. **Run the Development Server**

   Ensure you are in the root directory

   ```bash
   ./scripts/debug.sh start

   # OR

   docker run --rm -p 6379:6379 redis:7 # start a Redis server
   docker run --rm -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin minio/minio server /data --console-address ":9001" # start a MinIO server

   python manage.py runserver

   # OR

   # Important: change CHANNEL_LAYERS config from localhost to redis
   # Already fix it in compose.yml
   docker compose up -d --build
   ```

7. **Turn off dev server**
   Ctrl + C,
   To stop all containers:

   ```bash
      ./scripts/debug.sh stop

      OR
      docker compose down -v
   ```

## Running Tests

To run tests, use the following command:

```bash
python manage.py test
```

## Common Commands

- **Start a new app**

  ```bash
  python manage.py startapp app_name
  ```

- **Make migrations**

  ```bash
  python manage.py makemigrations
  ```

- **Apply migrations**

  ```bash
  python manage.py migrate
  ```

- **Create a new superuser**

  ```bash
  python manage.py createsuperuser
  ```

## Deployment

For deployment, follow these steps:

1. **Collect Static Files**

   ```bash
   python manage.py collectstatic
   ```

2. **Apply Migrations**

   ```bash
   python manage.py migrate
   ```

3. **Run the Server**

   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/en/stable/)
- [Django REST Framework](https://www.django-rest-framework.org/)
