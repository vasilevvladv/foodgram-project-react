from colorfield.fields import ColorField
from django.contrib.auth import get_user_model
from django.core import validators
from django.db import models
from django.db.models import CASCADE, CheckConstraint, F, Q, UniqueConstraint

CustomUser = get_user_model()


class Tag(models.Model):
    """Тэги для рецептов."""
    name = models.CharField(verbose_name='Название тега',
                            max_length=200, unique=True)
    color = ColorField(verbose_name='Цвет HEX-код',
                       max_length=7, unique=True,
                       default='#ff0000')
    slug = models.SlugField(verbose_name='Слаг',
                            unique=True)

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'
        ordering = ('name', )

    def __str__(self):
        return f'{self.name} (цвет: {self.color})'


class Ingredient(models.Model):
    """Ингридиенты для рецепта."""
    name = models.CharField(verbose_name='Ингридиент',
                            max_length=200)
    measurement_unit = models.CharField(verbose_name='Единица измерения',
                                        max_length=200)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        db_table = 'ingredient'
        constraints = [
            UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_for_ingredient'
            ),
        ]

    def __str__(self) -> str:
        return f'{self.name} {self.measurement_unit}'


class RecipeIngredientAmount(models.Model):
    """Количество ингридиентов в блюде."""
    recipe = models.ForeignKey('Recipe', verbose_name='В рецептах',
                               related_name='recipe',
                               on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient,
                                   verbose_name='Связанные ингредиенты',
                                   related_name='ingredient',
                                   on_delete=models.CASCADE)

    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество', default=0,
        validators=(
            validators.MinValueValidator(
                1, message='Ингредиентов должно быть 1 и больше.'
            ),
        )
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Количество ингридиентов'
        constraints = [
            UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_ingredient_for_recipe')
        ]

    def __str__(self) -> str:
        return f'{self.amount} {self.ingredients}'


class Recipe(models.Model):
    """Модель для рецептов"""
    name = models.CharField(verbose_name='Название блюда',
                            max_length=200)
    author = models.ForeignKey(CustomUser, verbose_name='Автор рецепта',
                               related_name='recipes', on_delete=CASCADE)
    tags = models.ManyToManyField(Tag, verbose_name='Тег',
                                  related_name='recipes')
    ingredients = models.ManyToManyField(Ingredient, verbose_name='Ингредиент',
                                         related_name='recipes',
                                         through='RecipeIngredientAmount')
    image = models.ImageField(verbose_name='Изображение блюда',
                              upload_to='recipes/images/')
    text = models.TextField(verbose_name='Описание блюда')
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        default=1,
    )
    pub_date = models.DateTimeField(verbose_name='Дата публикации',
                                    auto_now_add=True)

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        return f'{self.name}. Автор: {self.author.username}'


class Favorite(models.Model):
    """ Модель любимых рецептов пользователя """
    user = models.ForeignKey(CustomUser,
                             verbose_name='Пользователь',
                             related_name='favorite_recipes',
                             on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe,
                               verbose_name='Отборные рецепты',
                               related_name='favorite_recipes',
                               on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные рецепты'
        constraints = (
            UniqueConstraint(
                fields=('user', 'recipe'), name='unique_favorite'),
            )

    def __str__(self):
        return f'{self.user} добавил(-а) в избранное {self.recipe}'


class ShoppingCart(models.Model):
    """Корзина покупок    """
    user = models.ForeignKey(CustomUser,
                             verbose_name='Пользователь',
                             related_name='shopping_cart',
                             on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, verbose_name='Покупки',
                               related_name='shopping_cart',
                               on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Список покупок'
        constraints = (
            UniqueConstraint(
                fields=['recipe', 'user'], name='unique_shoppingcart'
            ),
        )

    def __str__(self):
        return (f'Пользователь {self.user} добавил'
                f'в список покупк рецепт: {self.recipe}')


class Subscription(models.Model):
    """Подписки"""
    user = models.ForeignKey(CustomUser, verbose_name='Фолловер',
                             related_name='sub_user', on_delete=models.CASCADE)
    author = models.ForeignKey(CustomUser, verbose_name='Автор',
                               related_name='sub_author',
                               on_delete=models.CASCADE)
    subscribe_date = models.DateTimeField(verbose_name='Дата',
                                          auto_now_add=True)

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            UniqueConstraint(
                fields=('user', 'author'), name='unique_subscription'
            ),
            CheckConstraint(check=~Q(user=F('author')),
                            name='user_cant_follow_himself'),
        ]

    def __str__(self):
        return f'{self.user} подписался на {self.author}'
