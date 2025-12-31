# sentiment_app/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Count, Avg
import logging
from .models import SentimentAnalysis, BatchAnalysis

logger = logging.getLogger(__name__)

@receiver(post_save, sender=SentimentAnalysis)
def log_sentiment_analysis_created(sender, instance, created, **kwargs):
    """Log when a new sentiment analysis is created"""
    if created:
        logger.info(f"New sentiment analysis created: ID={instance.id}, "
                   f"Sentiment={instance.sentiment}, "
                   f"Confidence={instance.confidence}")
        
        # Update batch analysis statistics if this is part of a batch
        if hasattr(instance, 'batch_analysis'):
            update_batch_statistics(instance.batch_analysis)

@receiver(post_delete, sender=SentimentAnalysis)
def log_sentiment_analysis_deleted(sender, instance, **kwargs):
    """Log when a sentiment analysis is deleted"""
    logger.info(f"Sentiment analysis deleted: ID={instance.id}")

@receiver(post_save, sender=BatchAnalysis)
def log_batch_analysis_created(sender, instance, created, **kwargs):
    """Log when a new batch analysis is created"""
    if created:
        logger.info(f"New batch analysis created: ID={instance.id}, "
                   f"File={instance.file_name}, "
                   f"Total={instance.total_reviews}")

@receiver(post_delete, sender=BatchAnalysis)
def cleanup_batch_files(sender, instance, **kwargs):
    """Clean up files when batch analysis is deleted"""
    try:
        if instance.results_file:
            # Delete the results file
            instance.results_file.delete(save=False)
            logger.info(f"Deleted results file for batch: {instance.id}")
    except Exception as e:
        logger.error(f"Error cleaning up batch files: {e}")

def update_batch_statistics(batch):
    """Update statistics for a batch analysis"""
    try:
        # Count sentiments in this batch
        sentiments = SentimentAnalysis.objects.filter(batch_analysis=batch)
        
        batch.positive_count = sentiments.filter(sentiment='positive').count()
        batch.negative_count = sentiments.filter(sentiment='negative').count()
        batch.neutral_count = sentiments.filter(sentiment='neutral').count()
        
        # Calculate average confidence
        avg_conf = sentiments.aggregate(Avg('confidence'))['confidence__avg']
        batch.average_confidence = avg_conf or 0
        
        batch.save(update_fields=[
            'positive_count', 'negative_count', 'neutral_count', 
            'average_confidence', 'updated_at'
        ])
        
        logger.info(f"Updated statistics for batch {batch.id}")
    except Exception as e:
        logger.error(f"Error updating batch statistics: {e}")

# Email notifications (optional)
@receiver(post_save, sender=BatchAnalysis)
def send_batch_completion_email(sender, instance, created, **kwargs):
    """Send email notification when batch analysis is complete"""
    if not created and instance.results_file:  # Only when results are ready
        from django.core.mail import send_mail
        from django.conf import settings
        
        try:
            subject = f"Batch Analysis Complete: {instance.file_name}"
            message = f"""
            Your batch analysis is complete!
            
            File: {instance.file_name}
            Total Reviews: {instance.total_reviews}
            Positive: {instance.positive_count}
            Negative: {instance.negative_count}
            Neutral: {instance.neutral_count}
            Average Confidence: {instance.average_confidence:.2%}
            
            You can view the results at: {settings.SITE_URL}/batch/{instance.id}/
            """
            
            if instance.user and instance.user.email:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.user.email],
                    fail_silently=True,
                )
                logger.info(f"Sent completion email for batch {instance.id}")
        except Exception as e:
            logger.error(f"Error sending batch completion email: {e}")

# Signal to update user analytics
@receiver(post_save, sender=SentimentAnalysis)
def update_user_analytics(sender, instance, created, **kwargs):
    """Update user analytics when analysis is created"""
    if created and instance.user:
        from django.contrib.auth.models import User
        from django.core.cache import cache
        
        # Clear user analytics cache
        cache_key = f"user_analytics_{instance.user.id}"
        cache.delete(cache_key)
        
        # You could also update a UserProfile model here
        logger.debug(f"Updated analytics cache for user {instance.user.id}")