from rest_framework import serializers
from .models import Post, Folder, SavedPost, Like, Share, Comment, Tag
from django.utils import timezone
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


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']
        extra_kwargs = {'name': {'validators': []} }

    @staticmethod
    def validate_tag_names(tag_names):
        """Validation for tag names that can be reused across serializers"""
        if not isinstance(tag_names, list):
            raise serializers.ValidationError("Expected a list of tags")
        
        validated_tags = []
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            if len(name) > 50:
                raise serializers.ValidationError(
                    f"Tag '{name}' is too long (max 50 characters)")
            validated_tags.append(name.lower())
        return validated_tags

    @staticmethod
    def get_or_create_tags(tag_names):
        """Helper method to get or create tags from names"""
        tags = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        return tags


class PostSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    caption = serializers.CharField(read_only=True) 

    # shares = serializers.SerializerMethodField()
    # comments = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'user', 'content', 'image', 'video', 'caption',
            'visibility', 'like_count', 'share_count', 'comment_count',
            'created_at', 'updated_at', 'is_liked', 'is_saved', 
            'disclaimer', 'deepfake_status', 'pinned', 'status', 'tags'
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

    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        write_only=True
    )

    caption = serializers.CharField(
        max_length=300,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    class Meta:
        model = Post
        fields = ['id', 'content', 'image',
                  'video', 'visibility', 'disclaimer','status',
                  'tags', 'caption',
                  'is_scheduled', 'scheduled_time']

    def validate(self, data):
        if data.get('status') != 'draft' and not (data.get('content') or data.get('image') or data.get('video')):
            raise serializers.ValidationError(
                "Post must have at least content, image, or video")
        
        if 'caption' in data and len(data['caption'] or '') > 300:
            raise serializers.ValidationError(
                "Caption cannot exceed 300 characters")
        
        if 'tags' in data:
            try:
                data['tags'] = TagSerializer.validate_tag_names(data['tags'])
            except serializers.ValidationError as e:
                raise serializers.ValidationError({'tags': e.detail})
            
            if len(data['tags']) > 10:
                raise serializers.ValidationError(
                    {'tags': "Cannot add more than 10 tags to a post"})
        
        if data.get('is_scheduled'):
            if not data.get('scheduled_time'):
                raise serializers.ValidationError(
                    "Scheduled time is required when is_scheduled is True")
            if data['scheduled_time'] <= timezone.now():
                raise serializers.ValidationError(
                    "Scheduled time must be in the future")
            data['status'] = 'draft'  # Force scheduled posts to be drafts initially

        return data
    
    def create(self, validated_data):
        validated_data.pop('user', None)
        tag_names = validated_data.pop('tags', [])
        post = Post.objects.create(user=self.context['request'].user, **validated_data)
        tags = self._get_or_create_tags(tag_names)
        post.tags.set(tags)
        return post

    def update(self, instance, validated_data):
        tag_names = validated_data.pop('tags', None)
        if 'caption' in validated_data:
            instance.caption = validated_data['caption']
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tag_names is not None:
            tags = []
            for name in tag_names:
                tag, _ = Tag.objects.get_or_create(name=name.lower().strip())
                tags.append(tag)
            instance.tags.set(tags)
        return instance

    def to_representation(self, instance):
        """Custom representation to include tag names"""
        representation = super().to_representation(instance)
        representation['tags'] = [tag.name for tag in instance.tags.all()]
        return representation

    def _get_or_create_tags(self, tag_names):
        """Utility to get or create Tag objects from a list of names"""
        tags = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name.strip())
            tags.append(tag)
        return tags


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
