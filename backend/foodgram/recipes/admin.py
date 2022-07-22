from django.contrib import admin

from foodgram.settings import EMPTY_VALUE

from .models import (Favorite, Ingredient, Recipe, RecipeIngredientAmount,
                     ShoppingCart, Subscription, Tag)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('name',)
    empty_value_display = EMPTY_VALUE


class IngredientInline(admin.TabularInline):
    model = Ingredient
    fields = ('name', 'measurement_unit',)


@admin.register(RecipeIngredientAmount)
class RecipeIngredientAmountAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'recipe', 'amount', '_amount_unit')
    list_display_links = ('ingredient', 'recipe',)
    inline = [
        IngredientInline,
    ]
    empty_value_display = EMPTY_VALUE

    @admin.display()
    def _amount_unit(self, obj):
        return obj.ingredient.measurement_unit

    _amount_unit.short_description = 'единица измерения'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug')
    list_filter = ('name',)
    search_fields = ('name',)
    empty_value_display = EMPTY_VALUE


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'ingredients', )
    list_display = ('id', 'user', 'recipe')
    list_filter = ('user',)
    search_fields = ('user',)
    empty_value_display = EMPTY_VALUE


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    list_filter = ('user', 'recipe')
    search_fields = ('user', 'recipe')
    empty_value_display = EMPTY_VALUE


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author',
                    'subscribe_date')
    search_fields = ('user__username', 'author__username')
    empty_value_display = EMPTY_VALUE


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredientAmount
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'author', 'get_ingredients',
        'get_tags', 'get_count_favorites',

    )
    list_filter = ('name', 'author', 'tags')
    list_display_links = ('name',)
    search_fields = (
        'name', 'cooking_time', 'author__username',
        'ingredients__name'
    )
    inlines = (RecipeIngredientInline,)
    empty_value_display = EMPTY_VALUE

    @admin.display(description='Игредиенты')
    def get_ingredients(self, obj):
        ingredients = obj.ingredients.all().values_list('name', flat=True)
        return ', '.join(ingredients)

    @admin.display(description='Тэги')
    def get_tags(self, obj):
        tags = obj.tags.all().values_list('name', flat=True)
        return ', '.join(tags)

    @admin.display(description='В избранном')
    def get_count_favorites(self, obj):
        return obj.favorite_recipes.count()
