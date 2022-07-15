from django.contrib.auth.models import AbstractUser
from django.db import models

USER_ROLE_USER = 'user'
USER_ROLE_ADMIN = 'admin'

USER_ROLE_CHOICES = (
    (USER_ROLE_USER, 'Пользователь'),
    (USER_ROLE_ADMIN, 'Администратор')
)


class CustomUser(AbstractUser):
    """My custom  user model."""
    username = models.CharField(verbose_name='username - учетная запись',
                                max_length=150, unique=True)
    role = models.CharField(verbose_name='Полномочия', max_length=15,
                            choices=USER_ROLE_CHOICES,
                            default=USER_ROLE_USER)
    first_name = models.CharField(verbose_name='Имя',
                                  max_length=150)
    last_name = models.CharField(verbose_name='Фамилия',
                                 max_length=150)
    email = models.EmailField(verbose_name='Адрес электронной почты',
                              max_length=254, unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'password']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)
        constraints = [
            models.UniqueConstraint(
                fields=('username', 'email'), name='unique_username_email'
            )
        ]

    def __str__(self):
        return f'{self.username}: {self.email}'
