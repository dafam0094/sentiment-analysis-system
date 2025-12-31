from django.db import models
from django.contrib.auth.models import User

class SentimentAnalysis(models.Model):
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField()
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES)
    confidence = models.FloatField()
    model_used = models.CharField(max_length=50)
    meta_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Sentiment Analyses'
    
    def __str__(self):
        return f"{self.sentiment} - {self.text[:50]}..."

class BatchAnalysis(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    file_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_reviews = models.IntegerField()
    positive_count = models.IntegerField(default=0)
    negative_count = models.IntegerField(default=0)
    neutral_count = models.IntegerField(default=0)
    average_confidence = models.FloatField(default=0)
    results_file = models.FileField(upload_to='reports/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = 'Batch Analyses'
    
    def __str__(self):
        return f"Batch {self.id} - {self.file_name}"