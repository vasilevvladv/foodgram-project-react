
![Status workflow](https://github.com/vasilevva/foodgram-project-react/actions/workflows/main.yml/badge.svg)

### DEMO
Демонстрационный проект развернут по адресу http://62.84.121.99
Учетные данные:
vasilevva@yandex.ru
789123


### Стэк технологий:
- Python
- Django Rest Framework
- Postgres
- Nginx
- Docker

### Описание
На сервисе Foodgram пользователи могут публиковать рецепты, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список «Избранное» и


1. Установите Docker и Docker-compose
Установите Docker и Docker-compose на свой сервер по инструкции с с официального  сайт.
Пример:
```
 sudo apt install docker.io
 sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
 sudo chmod +x /usr/local/bin/docker-compose
```

2. Скопируйте файлы Docker-compose.yml и nginx.conf из папки infra репозитория
Это млжно сделать при помощи команды scp

3. Создайте файл .env в папке со скопированными из репозитория файлами со следующим
содержимым:
```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
```

4. Перейдите с папку со скопированными из репозитория файлами и запустите проект:
```
sudo docker-compose up -d --build
```
5. Создайте суперпользователя для сайта:
```
docker exec -it <CONTAINER ID> bash
python manage.py createsuperuser
```
6. Зайдите в админку сайта и создайте теги рецептов .
