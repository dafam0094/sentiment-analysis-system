
# sentiment_app/services.py
import logging

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        logger.info("SentimentAnalyzer initialized")
        
    def analyze(self, text, model_type='ensemble'):
        """Analyze text sentiment"""
        # For now, use simple keyword matching
        text_lower = text.lower()
        
        positive_words = ['good', 'great', 'excellent', 'love', 'best', 'perfect', 'amazing', 'awesome']
        negative_words = ['bad', 'poor', 'terrible', 'worst', 'disappointed', 'waste', 'horrible', 'awful']
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            sentiment = 'positive'
            confidence = min(0.95, 0.7 + (pos_count * 0.05))
        elif neg_count > pos_count:
            sentiment = 'negative'
            confidence = min(0.95, 0.7 + (neg_count * 0.05))
        else:
            sentiment = 'neutral'
            confidence = 0.6
        
        # Calculate probabilities
        if sentiment == 'positive':
            probabilities = {
                'negative': 0.1,
                'neutral': 0.2,
                'positive': 0.7
            }
        elif sentiment == 'negative':
            probabilities = {
                'negative': 0.7,
                'neutral': 0.2,
                'positive': 0.1
            }
        else:  # neutral
            probabilities = {
                'negative': 0.3,
                'neutral': 0.4,
                'positive': 0.3
            }
        
        # Adjust probabilities based on confidence
        for key in probabilities:
            if key == sentiment:
                probabilities[key] = confidence
            else:
                probabilities[key] = (1 - confidence) / 2
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'probabilities': probabilities,
            'model': 'Keyword-based Analyzer' if model_type == 'ensemble' else 'DL Model (Placeholder)',
            'text_statistics': {
                'word_count': len(text.split()),
                'char_count': len(text)
            }
        }

    def batch_analyze(self, texts, model_type='ensemble'):
        """Analyze multiple texts"""
        results = []
        for i, text in enumerate(texts):
            try:
                result = self.analyze(text, model_type)
                results.append({
                    'id': i,
                    'text': text[:100] + '...' if len(text) > 100 else text,
                    'sentiment': result['sentiment'],
                    'confidence': result['confidence'],
                    'model': result['model']
                })
            except Exception as e:
                results.append({
                    'id': i,
                    'text': text[:100] + '...' if len(text) > 100 else text,
                    'sentiment': 'error',
                    'confidence': 0,
                    'model': 'Error',
                    'error': str(e)
                })
        return results
# Create global instance
analyzer = SentimentAnalyzer()

    
   