from django_filters import FilterSet
from django_filters.filters import (
    CharFilter,
    ChoiceFilter,
    ModelMultipleChoiceFilter,
    NumberFilter,
)
from recipes.models import Ingredient, Recipe, Tag

RECIPE_CHOICES = (
    (0, 'Not_In_List'),
    (1, 'In_List'),
)


class IngredientFilter(FilterSet):
    name = CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(FilterSet):
    author = NumberFilter(field_name='author__id', lookup_expr='exact')
    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    is_in_shopping_cart = ChoiceFilter(
        choices=RECIPE_CHOICES,
        method='get_is_in'
    )
    is_favorited = ChoiceFilter(
        choices=RECIPE_CHOICES,
        method='get_is_in'
    )

    def get_is_in(self, queryset, name, value):
        user = self.request.user
        if user.is_anonymous:
            return queryset
        if value in ('1', 'true',):
            if name == 'is_favorited':
                queryset = queryset.filter(favorite_recipes__user=user)
            if name == 'is_in_shopping_cart':
                queryset = queryset.filter(shopping_cart__user=user)
        return queryset

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')
