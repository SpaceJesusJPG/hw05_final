from django.test import Client, TestCase, override_settings
from django.contrib.auth import get_user_model
from ..models import Post, Group
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
import shutil
from django.conf import settings

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
NEW_POST_TEXT = 'Текст нового поста'
EDITED_POST_TEXT = 'Текст обновлённого поста'
COMMENT_TEXT = 'Текст тестового комментария'


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='user')
        self.author_client = Client()
        self.author_client.force_login(self.user)
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        self.post = Post.objects.create(
            author=self.user,
            text='Текст',
            group=self.group
        )

    @classmethod
    def tearDown(self):
        super().tearDown(self)
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_create(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': NEW_POST_TEXT,
            'image': uploaded
        }
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user})
        )
        latest_post = Post.objects.all()[1]
        self.assertEqual(latest_post.text, NEW_POST_TEXT)
        self.assertEqual(latest_post.image, 'posts/small.gif')

    def test_post_edit(self):
        form_data = {
            'text': EDITED_POST_TEXT,
            'group': self.group.pk
        }
        response = self.author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.post.refresh_from_db()
        self.assertEqual(self.post.text, EDITED_POST_TEXT)
        self.assertEqual(self.post.group, self.group)

    def test_comment_add(self):
        form_data = {
            'text': COMMENT_TEXT
        }
        response = self.author_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data
        )
        comment = self.post.comments.all()[0]
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(comment.text, COMMENT_TEXT)
