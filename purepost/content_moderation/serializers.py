from rest_framework import serializers
from .models import Post, Folder, SavedPost, Like, Share, Comment
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    bio = serializers.CharField(source='user_profile.bio', read_only=True)
    profile_picture = serializers.ImageField(
        source='user_profile.avatar', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email',
                  'bio', 'profile_picture', 'is_private']


class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    post = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'user', 'post', 'liked_at']
        read_only_fields = ['user', 'post', 'liked_at']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class ShareSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    # post = PostSerializer(read_only=True)
    post = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Share
        fields = ['id', 'user', 'post', 'comment', 'shared_at']
        read_only_fields = ['user', 'post', 'shared_at']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'post', 'content',
                  'parent', 'created_at', 'replies']
        read_only_fields = ['user', 'post', 'created_at', 'replies']

    def get_replies(self, obj):
        return CommentSerializer(obj.replies.all(), many=True).data

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class PostSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()

    # shares = serializers.SerializerMethodField()
    # comments = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'user', 'content', 'image', 'video',
            'visibility', 'like_count', 'share_count', 'comment_count',
            'created_at', 'updated_at',
            'is_liked', 'is_saved', 'disclaimer', 'deepfake_status', 'pinned'
        ]
        read_only_fields = [
            'user', 'like_count', 'share_count', 'comment_count',
            'created_at', 'updated_at', 'is_liked', 'is_saved', 'disclaimer'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Assume there is a Like model with a ForeignKey to Post and User
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedPost.objects.filter(user=request.user, post=obj).exists()
        return False

    def get_shares(self, obj):
        from .serializers import ShareSerializer
        return ShareSerializer(obj.shares.all(), many=True).data

    def get_comments(self, obj):
        from .serializers import CommentSerializer
        return CommentSerializer(obj.comments.filter(parent=None), many=True).data

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class PostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'content', 'image',
                  'video', 'visibility', 'disclaimer']

    def validate(self, data):
        if not (data.get('content') or data.get('image') or data.get('video')):
            raise serializers.ValidationError(
                "Post must have at least content, image, or video")
        return data


class FolderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ['id', 'user', 'name',
                  'created_at', 'updated_at', 'post_count']
        read_only_fields = ['user', 'created_at', 'updated_at', 'post_count']

    def get_post_count(self, obj):
        return obj.saved_posts.count()

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)

    def validate_name(self, value):
        request = self.context.get('request')
        if Folder.objects.filter(user=request.user, name=value).exists():
            raise serializers.ValidationError(
                "You already have a folder with this name")
        return value


class SavedPostSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    post = PostSerializer(read_only=True)
    post_id = serializers.PrimaryKeyRelatedField(
        queryset=Post.objects.all(),
        write_only=True,
        source='post'
    )
    folder = FolderSerializer(read_only=True)
    folder_id = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        write_only=True,
        source='folder',
        required=False,
        allow_null=True
    )

    class Meta:
        model = SavedPost
        fields = ['id', 'user', 'post', 'post_id',
                  'folder', 'folder_id', 'saved_at']
        read_only_fields = ['user', 'post', 'folder', 'saved_at']

    def validate_folder_id(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError(
                "You don't have permission to save to this folder")
        return value

    def validate(self, data):
        request = self.context.get('request')
        post = data.get('post')
        folder = data.get('folder')

        if SavedPost.objects.filter(user=request.user, post=post, folder=folder).exists():
            if folder:
                raise serializers.ValidationError(
                    f"Post already saved in folder '{folder.name}'")
            else:
                raise serializers.ValidationError(
                    "Post already saved without a folder")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class SavedPostListSerializer(serializers.ModelSerializer):
    post = PostSerializer()
    folder_name = serializers.SerializerMethodField()

    class Meta:
        model = SavedPost
        fields = ['id', 'post', 'folder_name', 'saved_at']

    def get_folder_name(self, obj):
        return obj.folder.name if obj.folder else "No Folder"
