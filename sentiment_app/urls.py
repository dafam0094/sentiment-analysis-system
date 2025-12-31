from django.urls import path
from . import views

urlpatterns = [
    # Web interface
    path('', views.index, name='index'),
    path('analyze/', views.analyze_single, name='analyze_single'),
    path('bulk/', views.analyze_bulk, name='analyze_bulk'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('history/', views.analysis_history, name='analysis_history'),
    path('batch/<int:batch_id>/', views.batch_detail, name='batch_detail'),
    
    # API endpoints
    path('api/analyze/', views.api_analyze, name='api_analyze'),
    path('api/batch-analyze/', views.api_batch_analyze, name='api_batch_analyze'),
    path('api/stats/', views.api_stats, name='api_stats'),
    
    # Documentation
    path('api/docs/', views.api_documentation, name='api_docs'),
    path('api/delete-analysis/<int:analysis_id>/', views.delete_analysis, name='delete_analysis'),
]