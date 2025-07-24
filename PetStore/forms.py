# your_app_name/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import Feedback, FeedbackImage

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['subject', 'message', 'email'] # 'user' will be set automatically in the view
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject (Optional)'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Your feedback here...'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email (Optional)'}),
        }
        labels = { # Custom labels for the form fields
            'subject': 'Subject',
            'message': 'Your Message',
            'email': 'Your Email',
        }

# Formset for handling multiple FeedbackImage instances associated with a Feedback object
FeedbackImageFormSet = inlineformset_factory(
    Feedback,              # Parent model
    FeedbackImage,         # Child model
    fields=('image',),     # Fields to include in the formset (only the image file)
    extra=1,               # Number of empty forms to display initially (for new images)
    max_num=5,             # Maximum number of images allowed per feedback (matches frontend limit)
    can_delete=False,      # Whether forms in the formset can be marked for deletion (not needed here)
    widgets={
        'image': forms.ClearableFileInput(attrs={'class': 'form-control'})
    }
)