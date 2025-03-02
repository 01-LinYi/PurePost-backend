from rest_framework import serializers
from .models import Post, Folder, SavedPost

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'user', 'content', 'image', 'video', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ['id', 'user', 'name', 'created_at']
        read_only_fields = ['user', 'created_at']

class SavedPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPost
        fields = ['id', 'user', 'post', 'folder', 'saved_at']
        read_only_fields = ['user', 'saved_at']
