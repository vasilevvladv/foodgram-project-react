from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404
from drf_base64.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (Ingredient, Recipe, RecipeIngredientAmount,
                            Subscription, Tag)
from users.models import CustomUser


class IsSubscribedMixin:

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            if isinstance(obj, CustomUser):
                return user.sub_user.filter(author=obj).exists()
            return True
        return False

    def get_recipes_template(self, recipes):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        if limit:
            recipes = recipes[:int(limit)]
        serializer = ShortRecipeSerializer(
            recipes, many=True, context={'request': request}
        )
        return serializer.data


class RecipeWriteMixin:

    def create_recipe_ingridient(self, ingredients, instance):
        listobj = []
        for ingredient in ingredients:
            ingredient_id, amount = ingredient['id'], ingredient['amount']
            listobj.append(RecipeIngredientAmount(
                recipe=instance,
                ingredient_id=ingredient_id,
                amount=amount
            ))
        RecipeIngredientAmount.objects.bulk_create(listobj)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'
        read_only_fields = '__all__',


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class CustomUserReadSerializer(serializers.ModelSerializer,
                               IsSubscribedMixin):
    is_subscribed = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'is_subscribed')


class CustomUserWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'password')


class CustomUserSetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(max_length=128)
    new_password = serializers.CharField(max_length=128, min_length=8)

    def validate_current_password(self, value):
        user = self.context.get('request').user
        if user.check_password(value):
            return value
        raise serializers.ValidationError(
            'Указан неверный текущий пароль.'
        )

    def validate_new_password(self, value):
        if not value:
            raise serializers.ValidationError(
                'Введите новый пароль'
            )
        validate_password(value)
        return value

    def create(self, validate_data):
        user = self.context.get('request').user
        newpassword = validate_data.get('new_password')
        user.set_password(newpassword)
        user.save()
        return validate_data


class SubscriptionSerializer(serializers.ModelSerializer,
                             IsSubscribedMixin):
    id = serializers.IntegerField(source='author.id')
    email = serializers.EmailField(source='author.email')
    username = serializers.CharField(source='author.username')
    first_name = serializers.CharField(source='author.first_name')
    last_name = serializers.CharField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField(
        read_only=True
    )
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count')

    def get_recipes(self, obj):
        return self.get_recipes_template(
            obj.author.recipes.only(
                'id', 'name', 'image', 'cooking_time'
            )
        )

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()


class SubscribeSerializer(serializers.ModelSerializer,
                          IsSubscribedMixin):
    queryset = CustomUser.objects.all()
    author_id = serializers.PrimaryKeyRelatedField(queryset=queryset)
    user_id = serializers.PrimaryKeyRelatedField(queryset=queryset)

    class Meta:
        model = CustomUser
        fields = ('author_id',
                  'user_id')

    def validate(self, data):
        user_id = data['user_id']
        author_id = data['author_id']
        subscription = Subscription.objects.filter(user=user_id,
                                                   author=author_id)
        if subscription.exists():
            raise serializers.ValidationError(
                'Нельзя дважды подписаться на одного автора.'
            )
        if user_id == author_id:
            raise serializers.ValidationError(
                'Подписаться на себя не получится.'
            )
        return data


class RecipeIngredientAmountSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name',
                                     read_only=True)
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = RecipeIngredientAmount
        fields = (
            'id', 'name', 'measurement_unit', 'amount'
        )


class IngredientAmountSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredientAmount
        fields = ('id', 'amount')

    def validate_amount(self, value):
        if value <= 0:
            return serializers.ValidationError(
                'Добавьте ингредиенты'
            )
        return value


class RecipeReadSerializer(serializers.ModelSerializer):
    author = CustomUserReadSerializer(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientAmountSerializer(
        many=True, source='recipe', required=True
    )
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return user.favorite_recipes.filter(recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return user.shopping_cart.filter(recipe=obj).exists()
        return False


class RecipeWriteSerializer(serializers.ModelSerializer,
                            RecipeWriteMixin):
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = IngredientAmountSerializer(
        many=True
    )
    image = Base64ImageField(
        max_length=None,
        use_url=True
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('id', 'author')

    def validate(self, data):
        ingredient_amount = data['ingredients']
        if not ingredient_amount:
            raise serializers.ValidationError(
                'Рецепт не может быть создан без ингредиентов.'
            )
        list_of_ingredients = []
        for value in ingredient_amount:
            ingredient_obj = get_object_or_404(
                Ingredient, pk=value.get('id')
            )
            if ingredient_obj in list_of_ingredients:
                raise serializers.ValidationError(
                    'Рецепт не может включать двух одиноковых ингредиентов.',
                )
            list_of_ingredients.append(ingredient_obj)

            amount = value['amount']
            if not isinstance(amount, int):
                error_message = amount.detail[0]
                raise serializers.ValidationError(
                    error_message
                )
        tags = data['tags']
        if not tags:
            raise serializers.ValidationError(
                'Нужен хотя бы один тэг для рецепта!')
        return data

    def validate_cooking_time(self, cooking_time):
        if int(cooking_time) < 1:
            raise serializers.ValidationError(
                'Время приготовления >= 1!')
        return cooking_time

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.create_recipe_ingridient(ingredients=ingredients,
                                      instance=recipe)
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.create_recipe_ingridient(ingredients=ingredients,
                                          instance=instance)
        if 'tags' in validated_data:
            tags = validated_data.pop('tags')
            instance.tags.clear()
            instance.tags.set(tags)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        serializer = RecipeReadSerializer(
            instance,
            context={
                'request': self.context['request']
            }
        )
        return serializer.data


class ShortRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = 'id', 'name', 'image', 'cooking_time'
