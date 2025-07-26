# your_app_name/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import Feedback, FeedbackImage

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['subject', 'message', 'email'] 
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject (Optional)'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Your feedback here...'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email (Optional)'}),
        }
        labels = { 
            'subject': 'Subject',
            'message': 'Your Message',
            'email': 'Your Email',
        }

FeedbackImageFormSet = inlineformset_factory(
    Feedback,              
    FeedbackImage,         
    fields=('image',),     
    extra=1,               
    max_num=5,            
    can_delete=False,     
    widgets={
        'image': forms.ClearableFileInput(attrs={'class': 'form-control'})
    }
)