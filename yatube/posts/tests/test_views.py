from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.conf import settings


from ..models import Post, Group, User


class PostModelTest(TestCase):
    def __init__(self, methodName: str = ...):
        super().__init__(methodName)
        self.another_group = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовый текст'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )

    def check_attrs(self, page_obj):
        self.assertEqual(page_obj.author, self.post.author)
        self.assertEqual(page_obj.group, self.post.group)
        self.assertEqual(page_obj.id, self.post.id)
        self.assertEqual(page_obj.text, self.post.text)
        self.assertEqual(page_obj.pub_date, self.post.pub_date)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_index_context(self):
        """Шаблон Index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        post = Post.objects.select_related('author').all()[0]
        page_obj = response.context['page_obj'][0]

        self.check_attrs(page_obj)
        self.assertIn('page_obj', response.context)
        self.assertEqual(page_obj, post)

    def test_group_list_context(self):
        """Проверка Group list использует правильные данные в контекст."""
        response = self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,)))
        post = Post.objects.select_related(
            'author', 'group').filter(group=self.group)[0]

        page_obj = response.context['page_obj'][0]

        self.check_attrs(page_obj)
        self.assertIn('page_obj', response.context)
        self.assertIn('group', response.context)
        self.assertEqual(page_obj, post)

    def test_profile_context(self):
        """Проверка profile использует правильный контекст."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.user.username,)))
        post = Post.objects.select_related(
            'author', 'group').filter(author=self.user)[0]
        page_obj = response.context['page_obj'][0]

        self.assertIn('page_obj', response.context)
        self.assertIn('author', response.context)
        self.assertEqual(page_obj, post)

    def test_post_detail_context(self):
        """Проверка Post detail использует правильный контекст."""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))

        post = response.context['post']

        self.assertEqual(post, self.post)

    def test_post_create_and_post_edit_context(self):
        """Post create page и post_create и post_edit использует правильный контекст."""
        response = self.authorized_client.get(reverse('posts:create')), \
                   self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}))

        form_fields = {
            'posts:create': {
                'url_kwargs': None,
                'text_value': '',
                'group_value': ''
            },
            'posts:post_edit': {
                'url_kwargs': {'post_id': self.post.id},
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
            }
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_context(self):
        """Post create page with post_edit использует правильный контекст."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', args=(self.post.id,)))

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        form_field_text = response.context.get('form')['text'].value()
        form_field_group = response.context.get('form')['group'].value()

        self.assertEqual(form_field_text, self.post.text)
        self.assertEqual(form_field_group, self.post.group.pk)

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_didnot_fall_into_wrong_group(self):
        """Тест на то, что пост не попал не в ту группу."""
        test_post = Post.objects.create(
            text='этот пост не должен попасть в не нужную группу',
            author=self.user,
            group=self.another_group
        )
        response = self.client.get(
            reverse('posts:group_list', args=(self.group.slug,)))
        page_obj = response.context['page_obj'][settings.ZERO]
        self.assertNotEqual(test_post, page_obj)


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create(username='HasNoName')

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        list_of_posts = []

        for page in range(20):
            list_of_posts.append(
                Post(
                    text=f'Test text №{page}',
                    author=cls.user,
                    group=cls.group,
                ))
        Post.objects.bulk_create(list_of_posts)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator_first_page(self):
        """Проверка корректной работы paginator."""
        list_of_check_page = ('/',
                              '/group/test-slug/',
                              '/profile/HasNoName/'
                              )
        list_of_paginator_page = (
            (('?page=1', settings.POSTS_ON_PAGE),
             ('?page=2', settings.POSTS_ON_PAGE),
             ))

        for page in list_of_check_page:
            for pag in list_of_paginator_page:
                with self.subTest(adress=page):
                    response = self.client.get(page)
                    self.assertEqual(
                        len(response.context['page_obj']), settings.POSTS_ON_PAGE)
                    response = self.client.get(page + '?page=2')
                    self.assertEqual(
                        len(response.context['page_obj']),
                        settings.POSTS_ON_PAGE)
