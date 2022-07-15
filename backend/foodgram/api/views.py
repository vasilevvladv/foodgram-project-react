from urllib.parse import unquote

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe, ShoppingCart,
                            Subscription, Tag)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.models import CustomUser

from .pagination import CustomPageNumberPagination
from .permissions import IsAdminOrReadOnly, IsOwnerAdminOrReadOnly
from .serializers import (CustomUserReadSerializer,
                          CustomUserSetPasswordSerializer,
                          CustomUserWriteSerializer, IngredientSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer,
                          ShortRecipeSerializer, SubscribeSerializer,
                          SubscriptionSerializer, TagSerializer)
from .utils import create_pdf_shopping_cart

User = get_user_model()

KEYBOARD_LAYOUT = str.maketrans(
    'qwertyuiop[]asdfghjkl;\'zxcvbnm,./',
    'йцукенгшщзхъфывапролджэячсмитьбю.'
)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ Работа с тэгами. """
    permission_classes = (IsAdminOrReadOnly,)
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Работет с игридиентами"""
    queryset = Ingredient.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        name = self.request.query_params.get('name')
        queryset = self.queryset
        if name:
            if name[0] == '%':
                name = unquote(name)
            else:
                name = name.translate(KEYBOARD_LAYOUT)
            name = name.lower()
            startswith_queryset = list(queryset.filter(name__startswith=name))
            contain_queryset = queryset.filter(name__contains=name)
            startswith_queryset.extend(
                [i for i in contain_queryset if i not in startswith_queryset]
            )
            queryset = startswith_queryset
        return queryset


class CustomUserViewSet(UserViewSet):
    """
    Реализация работы с пользователями и подписками.
    Реализует эндпойнты
        GET:
            api/users/
            api/users/me/
            api/users/{user_id}/
            api/users/subscriptions/
        POST:
            api/users/
            api/auth/token/login/
            api/auth/token/logout/
            api/users/set_password/
    """

    queryset = CustomUser.objects.all()
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CustomUserReadSerializer
        return CustomUserWriteSerializer

    def perform_create(self, serializer):
        if 'password' in self.request.data:
            password = make_password(self.request.data['password'])
            serializer.save(password=password)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=(IsAuthenticated,),
        url_name='set_password'
    )
    def set_password(self, request):
        """
        Эндпоинт
        api/users/set_password.
        """
        serializer = CustomUserSetPasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                {'message': 'Пароль успешно изменен'},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
        url_name='subscriptions'
    )
    def subscriptions(self, request):
        """
        Эндпоинт подписчики
        GET: api/users/subscriptions
        """
        user = self.request.user
        queryset = Subscription.objects.filter(user=user)
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
        url_name='subscribe'
    )
    def subscribe(self, request, id):
        """
        Эндпоинт довбовление, удаление подписки
        POST, DELETE: api/users/<user_id>/subscribe/
        """
        user = request.user
        author = get_object_or_404(CustomUser, pk=id)
        subscription = user.sub_user.filter(author=author)
        if request.method == 'POST':
            if subscription.exists():
                return Response(
                    {'message': 'Нельзя дважды подписаться на одного автора.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if user == author:
                return Response(
                    {'message': 'Подписаться на себя не получится.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = SubscribeSerializer(
                author, context={'request': request}
            )
            Subscription.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not subscription:
                return Response(
                    {'message': 'Подписка не оформлялась или уже удалена.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    """
    Эндпоинт работает с рецептами
    GET, POST: /api/recipes/
    GEt, PATCH, DELETE: /api/recipes/{id}/
    """

    permission_classes = (IsOwnerAdminOrReadOnly,)
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        queryset = Recipe.objects.all()
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(
                tags__slug__in=tags).distinct()
        user = self.request.user
        if user.is_anonymous:
            return queryset
        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(author=author)
        is_in_shopping = self.request.query_params.get('is_in_shopping_cart')
        if is_in_shopping in ('1', 'true',):
            queryset = queryset.filter(shopping_cart__user=user)
        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited in ('1', 'true',):
            queryset = queryset.filter(favorite_recipe__user=user)
        return queryset

    def control_existence_recipe(self, model, pk, request):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        queryset = model.objects.filter(user=user, recipe=recipe)
        if request.method == 'POST':
            if queryset.exists():
                return Response(
                    {'message': 'Такой рецепт уже есть в каталоге.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = ShortRecipeSerializer(
                recipe,
                context={'request': request}
            )
            model.objects.create(user=user, recipe=recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not queryset:
                return Response(
                    {'message': 'Рецепт отсуствует в списке.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            queryset.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
        url_name='download_recipe'
    )
    def download_shopping_cart(self, request):
        """
        Эндпоинт скачивания списка покупок
        GET:api/recipes/download_shopping_cart
                """
        user = request.user
        buffer = create_pdf_shopping_cart(user)
        filename = f'{user.username}_shopping_list.pdf'
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename
        )

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
        url_name='favorite'
    )
    def favorite(self, request, pk):
        """
        Эндпоинт добовления в избраное
        POST, DELETE:api/recipes/<recipe_id>/favorite/
        """
        model = Favorite
        return self. control_existence_recipe(
            model, pk, request
        )

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
        url_name='shopping_cart'
    )
    def shopping_cart(self, request, pk):
        """
        Эндпоинт добовления в корзину.
        POST, DELETE: api/recipes/<recipe_id>/shopping_cart/
        """
        model = ShoppingCart
        return self.control_existence_recipe(
            model, pk, request
        )
