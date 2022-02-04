import shutil
import tempfile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import Post, Group, Comment, Follow
from django.core.cache import cache

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
POST_CNT = 13

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = User.objects.create_user(username='user1')
        cls.user_2 = User.objects.create_user(username='user2')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user_1)

    def setUp(self):
        super().setUp()
        self.group_1 = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        self.group_2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test_slug2',
            description='Тестовое описание2',
        )
        self.post_1 = Post.objects.create(
            author=self.user_1,
            text='Тестовый текст',
            group=self.group_1,
        )
        self.comment = Comment.objects.create(
            post=self.post_1,
            author=self.post_1.author,
            text='Тестовый текст комментария',
        )

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_posts', kwargs={'slug': self.group_1.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.post_1.author}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post_1.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post_1.pk}
            ): 'posts/post_create.html',
            reverse('posts:post_create'): 'posts/post_create.html'
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        post_text_1 = first_object.text
        post_author_1 = first_object.author
        post_pub_date_1 = first_object.pub_date
        post_group_1 = first_object.group
        self.assertEqual(post_text_1, self.post_1.text)
        self.assertEqual(post_author_1, self.post_1.author)
        self.assertEqual(post_pub_date_1, self.post_1.pub_date)
        self.assertEqual(post_group_1, self.post_1.group)

    def test_group_list_page_show_correct_context(self):
        self.post_2 = Post.objects.create(
            author=self.user_1,
            text='Тестовый текст1',
            group=self.group_1,
        )
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group_1.slug})
        )
        first_object = response.context['page_obj'][0]
        second_object = response.context['page_obj'][1]
        group_1 = first_object.group
        group_2 = second_object.group
        self.assertEqual(group_1, self.group_1)
        self.assertEqual(group_2, self.group_1)
        self.assertNotEqual(group_2, self.group_2)

    def test_profile_page_show_correct_context(self):
        self.post_3 = Post.objects.create(
            author=self.user_1,
            text='Тестовый текст2',
            group=self.group_1,
        )
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user_1.username})
        )
        first_object = response.context['page_obj'][0]
        second_object = response.context['page_obj'][1]
        author_1 = first_object.author
        author_2 = second_object.author
        group = second_object.group
        self.assertEqual(author_1, self.user_1)
        self.assertEqual(author_2, self.user_1)
        self.assertEqual(group, self.group_1)

    def test_post_detail_page_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post_1.pk})
        )
        post = response.context['post']
        last_comment = post.comments.all()[0]
        self.assertEqual(post.pk, self.post_1.pk)
        self.assertEqual(last_comment, self.comment)

    def test_post_create_page_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post_1.pk})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_cache_index_page(self):
        response = self.authorized_client.get(reverse('posts:index'))
        old_content = response.content
        self.post_1.delete()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(old_content, response.content)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, old_content)

    def test_authorized_user_can_follow_and_unfollow(self):
        author = self.user_2
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': author.username}
            )
        )
        self.assertTrue(Follow.objects.filter(
            author=self.user_2,
            user=self.user_1
        ).exists())
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': author.username}
            )
        )
        self.assertFalse(Follow.objects.filter(
            author=self.user_2,
            user=self.user_1
        ).exists())

    def test_follow_index(self):
        another_client = Client()
        another_client.force_login(self.user_2)
        post_2 = Post.objects.create(
            author=self.user_2,
            text='Тестовый текст',
        )
        Follow.objects.create(author=self.user_2, user=self.user_1)
        Follow.objects.create(author=self.user_1, user=self.user_2)
        response = self.authorized_client.get(
            reverse(
                'posts:follow_index'
            )
        )
        obj = response.context['page_obj'][0]
        self.assertEqual(obj, post_2)
        response = another_client.get(
            reverse(
                'posts:follow_index'
            )
        )
        obj = response.context['page_obj'][0]
        self.assertNotEqual(obj, post_2)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        objs = [
            Post(
                author=cls.user,
                text=f'Тестовый текст{e}'
            )
            for e in range(POST_CNT)
        ]
        Post.objects.bulk_create(objs)

    def test_first_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ImageVeiwsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(user=cls.user)
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='текст',
            author=cls.user,
            image=cls.uploaded,
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_image_in_context_index(self):
        page_adresses = [
            reverse('posts:index'),
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ),
            reverse(
                'posts:group_posts',
                kwargs={'slug': self.group.slug}
            )
        ]
        for adress in page_adresses:
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                first_object = response.context['page_obj'][0]
                post_image = first_object.image
                self.assertEqual(post_image, self.post.image)

    def test_imange_in_context_post_detail(self):
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        object = response.context['post']
        self.assertEqual(object.image, self.post.image)
