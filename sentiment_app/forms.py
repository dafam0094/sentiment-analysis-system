from django import forms
from .models import BatchAnalysis

class SingleAnalysisForm(forms.Form):
    text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Enter your review text here...'
        }),
        label='Review Text',
        max_length=10000
    )
    
    model_type = forms.ChoiceField(
        choices=[
            ('ensemble', 'Ensemble Model (Recommended)'),
            ('deep_learning', 'Deep Learning Model'),
        ],
        initial='ensemble',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select Model'
    )

class BulkAnalysisForm(forms.Form):
    file = forms.FileField(
        label='Upload File',
        help_text='Supported formats: CSV, Excel (.xlsx, .xls)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )
    
    text_column = forms.CharField(
        label='Text Column Name',
        initial='reviewText',
        help_text='Column name containing review text',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    model_type = forms.ChoiceField(
        choices=[
            ('ensemble', 'Ensemble Model (Faster)'),
            ('deep_learning', 'Deep Learning Model (More Accurate)'),
        ],
        initial='ensemble',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select Model'
    )
    
    max_reviews = forms.IntegerField(
        label='Maximum Reviews to Process',
        initial=100,
        min_value=1,
        max_value=1000,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text='Limit processing to prevent timeout'
    )