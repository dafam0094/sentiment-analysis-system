# Create your views here.
import json
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.db.models import Count, Avg
from django.core.paginator import Paginator
from django.utils import timezone

from .forms import SingleAnalysisForm, BulkAnalysisForm
from .models import SentimentAnalysis, BatchAnalysis
from .services import SentimentAnalyzer

analyzer = SentimentAnalyzer()

def index(request):
    """Home page"""
    # Get some statistics
    stats = {
        'total_analyses': SentimentAnalysis.objects.count(),
        'positive_count': SentimentAnalysis.objects.filter(sentiment='positive').count(),
        'negative_count': SentimentAnalysis.objects.filter(sentiment='negative').count(),
        'neutral_count': SentimentAnalysis.objects.filter(sentiment='neutral').count(),
    }
    
    # Sample reviews for demonstration
    sample_reviews = [
        "This product is absolutely amazing! Works perfectly and exceeded my expectations.",
        "Not happy with the quality. Stopped working after just 2 days of use.",
        "It's okay for the price. Nothing special but gets the job done.",
        "Best purchase ever! Highly recommend to everyone.",
        "Complete waste of money. Don't buy this product.",
    ]
    
    return render(request, 'sentiment_app/index.html', {
        'stats': stats,
        'sample_reviews': sample_reviews
    })

def analyze_single(request):
    """Single review analysis"""
    if request.method == 'POST':
        form = SingleAnalysisForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data['text']
            model_type = form.cleaned_data['model_type']
            
            try:
                result = analyzer.analyze(text, model_type)
                
                # Save to database if user is authenticated
                if request.user.is_authenticated:
                    SentimentAnalysis.objects.create(
                        user=request.user,
                        text=text[:500],  # Store first 500 chars
                        sentiment=result['sentiment'],
                        confidence=result['confidence'],
                        model_used=result['model'],
                        meta_data=result
                    )
                
                # Prepare data for visualization
                chart_data = {
                    'labels': ['Negative', 'Neutral', 'Positive'],
                    'data': [
                        result['probabilities']['negative'] * 100,
                        result['probabilities']['neutral'] * 100,
                        result['probabilities']['positive'] * 100
                    ]
                }
                
                return render(request, 'sentiment_app/result_single.html', {
                    'form': form,
                    'result': result,
                    'original_text': text,
                    'chart_data': json.dumps(chart_data),
                    'model_type': model_type
                })
                
            except Exception as e:
                messages.error(request, f'Error during analysis: {str(e)}')
    else:
        form = SingleAnalysisForm()
    
    return render(request, 'sentiment_app/analyze_single.html', {'form': form})

@login_required
def analyze_bulk(request):
    """Bulk file analysis"""
    if request.method == 'POST':
        form = BulkAnalysisForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            text_column = form.cleaned_data['text_column']
            model_type = form.cleaned_data['model_type']
            max_reviews = form.cleaned_data['max_reviews']
            
            try:
                # Save uploaded file - FIXED PATH
                fs = FileSystemStorage(location='media/uploads/')
                filename = fs.save(file.name, file)
                file_path = fs.path(filename)
                
                # Read file
                if filename.endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                
                # Get text column
                if text_column not in df.columns:
                    messages.error(request, f'Column "{text_column}" not found in file')
                    return render(request, 'sentiment_app/analyze_bulk.html', {'form': form})
                
                texts = df[text_column].dropna().tolist()
                texts = texts[:max_reviews]  # Limit reviews
                
                # Analyze in batches to prevent timeout
                results = []
                batch_size = 50
                
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i+batch_size]
                    batch_results = analyzer.batch_analyze(batch_texts, model_type)
                    results.extend(batch_results)
                
                # Create summary
                sentiments = [r['sentiment'] for r in results if 'sentiment' in r]
                sentiment_counts = pd.Series(sentiments).value_counts()
                
                # Create batch record
                batch = BatchAnalysis.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    file_name=filename,
                    total_reviews=len(texts),
                    positive_count=sentiment_counts.get('positive', 0),
                    negative_count=sentiment_counts.get('negative', 0),
                    neutral_count=sentiment_counts.get('neutral', 0),
                    average_confidence=sum(r.get('confidence', 0) for r in results) / len(results) if results else 0
                )
                
                # Save detailed results to CSV - FIXED PATH
                import os
                from django.conf import settings
                
                # Create reports directory if it doesn't exist
                reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
                os.makedirs(reports_dir, exist_ok=True)
                
                # Save results
                results_df = pd.DataFrame(results)
                results_filename = f'batch_{batch.id}_results.csv'
                results_path = os.path.join(reports_dir, results_filename)
                results_df.to_csv(results_path, index=False)
                
                # Save relative path to database
                batch.results_file.name = f'reports/{results_filename}'
                batch.save()
                
                messages.success(request, f'Successfully analyzed {len(results)} reviews')
                return redirect('batch_detail', batch_id=batch.id)
                
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
    
    else:
        form = BulkAnalysisForm()
    
    return render(request, 'sentiment_app/analyze_bulk.html', {'form': form})

def batch_detail(request, batch_id):
    """View batch analysis details"""
    batch = get_object_or_404(BatchAnalysis, id=batch_id)
    
    results = []
    if batch.results_file:
        try:
            # Try to get the file path
            if hasattr(batch.results_file, 'path'):
                file_path = batch.results_file.path
            else:
                # Construct path manually
                file_path = os.path.join(settings.MEDIA_ROOT, batch.results_file.name)
            
            # Read file using helper
            df = read_results_file(file_path)
            if df is not None:
                results = df.to_dict('records')
            else:
                # Create dummy data for testing
                results = [
                    {'id': 1, 'text': 'Sample review 1', 'sentiment': 'positive', 'confidence': 0.85},
                    {'id': 2, 'text': 'Sample review 2', 'sentiment': 'negative', 'confidence': 0.75},
                    {'id': 3, 'text': 'Sample review 3', 'sentiment': 'neutral', 'confidence': 0.65},
                ]
                
        except Exception as e:
            print(f"Error in batch_detail: {e}")
            results = []
    
    return render(request, 'sentiment_app/batch_detail.html', {
        'batch': batch,
        'results': results[:20]
    })

import os
from django.conf import settings

def read_results_file(file_path):
    """Safely read results CSV file"""
    try:
        if os.path.exists(file_path):
            return pd.read_csv(file_path)
        else:
            # Try alternative paths
            # Remove duplicate 'media/' if present
            if 'media/media/' in file_path:
                corrected_path = file_path.replace('media/media/', 'media/')
                if os.path.exists(corrected_path):
                    return pd.read_csv(corrected_path)
            
            # Try from MEDIA_ROOT
            filename = os.path.basename(file_path)
            media_path = os.path.join(settings.MEDIA_ROOT, filename)
            if os.path.exists(media_path):
                return pd.read_csv(media_path)
            
            return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def dashboard(request):
    """Interactive dashboard"""
    # Get overall statistics
    sentiment_dist = SentimentAnalysis.objects.values('sentiment').annotate(
        count=Count('id')
    ).order_by('sentiment')
    
    # Prepare data for charts - with safe defaults
    labels = []
    counts = [0, 0, 0]  # [negative, neutral, positive]
    
    for item in sentiment_dist:
        sentiment = item['sentiment']
        count = item['count']
        
        if sentiment == 'negative':
            labels.append('Negative')
            counts[0] = count
        elif sentiment == 'neutral':
            labels.append('Neutral')
            counts[1] = count
        elif sentiment == 'positive':
            labels.append('Positive')
            counts[2] = count
    
    # Ensure all labels exist
    if 'Negative' not in labels:
        labels.append('Negative')
    if 'Neutral' not in labels:
        labels.append('Neutral')
    if 'Positive' not in labels:
        labels.append('Positive')
    
    chart_data = {
        'labels': labels,
        'counts': counts,
        'colors': ['#FF6B6B', '#FFD166', '#06D6A0']  # Red, Yellow, Green
    }
    
    # Recent analyses
    recent_analyses = SentimentAnalysis.objects.all().order_by('-created_at')[:10]
    
    return render(request, 'sentiment_app/dashboard.html', {
        'chart_data': json.dumps(chart_data),
        'recent_analyses': recent_analyses,
        'total_analyses': SentimentAnalysis.objects.count()
    })

# sentiment_app/views.py - Add this function
@csrf_exempt
def api_batch_analyze(request):
    """API endpoint for batch analysis"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            texts = data.get('texts', [])
            model_type = data.get('model_type', 'ensemble')
            
            if isinstance(texts, str):
                texts = [texts]
            
            # Analyze using sentiment analyzer
            results = sentiment_analyzer.batch_analyze(texts, model_type)
            
            return JsonResponse({
                'success': True,
                'results': results,
                'count': len(results),
                'model_used': model_type
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def batch_detail(request, batch_id):
    """View batch analysis details"""
    batch = get_object_or_404(BatchAnalysis, id=batch_id, user=request.user)
    
    # Read results file
    if batch.results_file:
        results_df = pd.read_csv(batch.results_file.path)
        results = results_df.to_dict('records')
    else:
        results = []
    
    return render(request, 'sentiment_app/batch_detail.html', {
        'batch': batch,
        'results': results[:50],  # Show first 50 results
    })

@csrf_exempt
def api_analyze(request):
    """API endpoint for single analysis"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text', '')
            model_type = data.get('model_type', 'ensemble')
            
            if not text:
                return JsonResponse({'error': 'Text is required'}, status=400)
            
            result = analyzer.analyze(text, model_type)
            
            return JsonResponse({
                'success': True,
                'result': result,
                'model_used': model_type
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def api_stats(request):
    """API endpoint for statistics"""
    stats = {
        'total_analyses': SentimentAnalysis.objects.count(),
        'sentiment_distribution': {
            'positive': SentimentAnalysis.objects.filter(sentiment='positive').count(),
            'negative': SentimentAnalysis.objects.filter(sentiment='negative').count(),
            'neutral': SentimentAnalysis.objects.filter(sentiment='neutral').count(),
        },
        'average_confidence': SentimentAnalysis.objects.aggregate(Avg('confidence'))['confidence__avg'] or 0,
    }
    
    return JsonResponse(stats)


@login_required
def analysis_history(request):
    """View analysis history with export, filter, and search functionality"""
    analyses = SentimentAnalysis.objects.filter(user=request.user).order_by('-created_at')
    
    # Handle filtering by sentiment
    sentiment_filter = request.GET.get('sentiment')
    if sentiment_filter and sentiment_filter != 'all':
        analyses = analyses.filter(sentiment=sentiment_filter)
    
    # Handle search
    search_query = request.GET.get('search')
    if search_query:
        analyses = analyses.filter(text__icontains=search_query)
    
    # Handle export requests
    export_format = request.GET.get('export')
    if export_format in ['csv', 'excel']:
        return export_history(analyses, export_format)
    
    # Pagination for normal view
    paginator = Paginator(analyses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'sentiment_app/history.html', {
        'page_obj': page_obj,
        'current_filter': sentiment_filter,
        'search_query': search_query,
    })

def export_history(queryset, format_type):
    """Export analysis history to CSV or Excel"""
    # Prepare data
    data = []
    for analysis in queryset:
        data.append({
            'ID': analysis.id,
            'Text': analysis.text,
            'Sentiment': analysis.sentiment,
            'Confidence': f"{analysis.confidence:.2%}" if analysis.confidence else "N/A",
            'Model Used': analysis.model_used,
            'Created Date': analysis.created_at.strftime('%Y-%m-%d'),
            'Created Time': analysis.created_at.strftime('%H:%M:%S'),
            'User': analysis.user.username if analysis.user else 'Anonymous',
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create filename with timestamp
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    
    if format_type == 'csv':
        # Export to CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sentiment_history_{timestamp}.csv"'
        df.to_csv(response, index=False, encoding='utf-8-sig')
        return response
    
    elif format_type == 'excel':
        # Export to Excel
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="sentiment_history_{timestamp}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sentiment History', index=False)
        
        return response
    
    return HttpResponse('Invalid export format', status=400)

@csrf_exempt
@login_required
def delete_analysis(request, analysis_id):
    """Delete a specific analysis"""
    if request.method == 'DELETE':
        try:
            analysis = SentimentAnalysis.objects.get(id=analysis_id, user=request.user)
            analysis.delete()
            return JsonResponse({'success': True, 'message': 'Analysis deleted successfully'})
        except SentimentAnalysis.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Analysis not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def api_documentation(request):
    """API documentation page"""
    return render(request, 'sentiment_app/api_docs.html')