from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPageNumberPagination
from .permissions import IsAdminOrReadOnly, IsOwnerAdminOrReadOnly
from .serializers import (CustomUserReadSerializer,
                          CustomUserSetPasswordSerializer,
                          CustomUserWriteSerializer, IngredientSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer,
                          ShortRecipeSerializer, SubscribeSerializer,
                          SubscriptionSerializer, TagSerializer)
from .utils import create_pdf_shopping_cart
from recipes.models import (Favorite, Ingredient, Recipe, ShoppingCart,
                            Subscription, Tag)
from users.models import CustomUser

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
    """Работет с ингредиентами"""
    queryset = Ingredient.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


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

    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CustomUserReadSerializer
        return CustomUserWriteSerializer

    def perform_create(self, serializer):
        if 'password' in self.request.data:
            password = make_password(self.request.data['password'])
            serializer.save(password=password)

    def get_queryset(self):
        return CustomUser.objects.all()

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
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'Пароль успешно изменен'},
            status=status.HTTP_201_CREATED
        )

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
            serializer = SubscribeSerializer(
                data={
                    'author_id': author.pk,
                    'user_id': user.pk
                },
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            item = Subscription.objects.create(user=user, author=author)
            return Response(SubscriptionSerializer(
                item, context={'request': request}
            ).data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            if not subscription.exists():
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
    queryset = Recipe.objects.all()
    permission_classes = (IsOwnerAdminOrReadOnly,)
    pagination_class = CustomPageNumberPagination
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.author != self.request.user:
            raise PermissionDenied('Изменение чужого контента запрещено!')
        super().perform_update(serializer)

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
