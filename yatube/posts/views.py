from django.shortcuts import redirect, render, get_object_or_404
from .forms import PostForm, CommentForm
from .models import Post, Group, Follow
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

User = get_user_model()
POST_CNT = 10


def index(request):
    template = "posts/index.html"
    title = "Yatube"
    posts = Post.objects.all().order_by("-pub_date")
    paginator = Paginator(posts, POST_CNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "title": title,
        "text": "Последние обновления на сайте",
        "posts": posts,
        "page_obj": page_obj,
        "index": True
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = "posts/group_list.html"
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all().order_by("-pub_date")
    descripction = group.description
    paginator = Paginator(posts, POST_CNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "group": group,
        "descripction": descripction,
        "posts": posts,
        "text": f"Записи сообщества {group}",
        "page_obj": page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all().order_by("-pub_date")
    paginator = Paginator(posts, POST_CNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    following = request.user.is_authenticated and Follow.objects.filter(
        user=request.user,
        author=author
    ).exists()
    context = {
        "author": author,
        "posts": posts,
        "page_obj": page_obj,
        "following": following
    }
    return render(request, "posts/profile.html", context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    group = post.group
    comments = post.comments.all()
    comment_form = CommentForm(request.POST or None)
    context = {
        "post": post,
        "group": group,
        'comments': comments,
        'form': comment_form
    }
    return render(request, "posts/post_detail.html", context)


@login_required
def post_create(request):
    author = get_object_or_404(User, username=request.user)
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == "POST" and form.is_valid():
        deform = form.save(commit=False)
        deform.author = author
        deform.save()
        return redirect("posts:profile", username=author)
    context = {"form": form}
    return render(request, "posts/post_create.html", context)


@login_required
def post_edit(request, post_id):
    author = get_object_or_404(User, username=request.user)
    post = get_object_or_404(Post, id=post_id)
    form = PostForm(
        request.POST or None,
        instance=post,
        files=request.FILES or None
    )
    if author != post.author:
        return redirect("posts:post_detail", post_id=post_id)
    if request.method == "POST" and form.is_valid():
        deform = form.save(commit=False)
        deform.author = author
        deform.save()
        return redirect("posts:post_detail", post_id=post_id)
    context = {"form": form, "is_edit": True}
    return render(request, "posts/post_create.html", context)


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user == post.author:
        post.delete()
        return redirect('posts:profile', username=post.author)
    return redirect('posts:profile', username=post.author)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    user = request.user
    user_following = Follow.objects.filter(user=user)
    posts = []
    for follow in user_following:
        posts += follow.author.posts.all()
    paginator = Paginator(posts, POST_CNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'follow': True
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = User.objects.get(username=username)
    if author != user and not Follow.objects.filter(
        user=user,
        author=author
    ).exists():
        Follow.objects.create(user=user, author=author)
    return redirect('posts:profile', username=author)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = User.objects.get(username=username)
    follow_object = Follow.objects.get(user=user, author=author)
    follow_object.delete()
    return redirect('posts:profile', username=author)
