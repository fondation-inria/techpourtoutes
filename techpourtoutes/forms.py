# from django import forms
# from .models import Post, Comment


# class PostForm(forms.ModelForm):
#     class Meta:
#         model = Post
#         fields = ("title", "text")
#         # labels = {
#         #     "title": False,
#         #     "text": False,
#         # }
#         widgets = {
#             "title": forms.TextInput(attrs={
#                 'class': 'input w-full',
#                 'placeholder': 'Title'
#             }),
#             "text": forms.Textarea(attrs={
#                 'class': 'textarea w-full',
#                 'placeholder': 'Texte'
#             }),
#         }


# class CommentForm(forms.ModelForm):
#     class Meta:
#         model = Comment
#         fields = ("title", "text")
#         widgets = {
#             "title": forms.TextInput(attrs={
#                 'class': 'input w-full',
#                 'placeholder': 'Title'
#             }),
#             "text": forms.Textarea(attrs={
#                 'class': 'textarea w-full',
#                 'placeholder': 'Texte'
#             }),
#         }
