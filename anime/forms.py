from django import forms
from .models import Anime, Genre

class AnimeFilterForm(forms.Form):
    """Form for filtering anime in the catalog"""
    SORT_CHOICES = [
        ('', 'Ordenar por'),
        ('title_asc', 'Título (A-Z)'),
        ('title_desc', 'Título (Z-A)'),
        ('rating', 'Puntuación'),
        ('year', 'Año'),
    ]
    
    q = forms.CharField(
        label='Buscar',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar por título, género...',
            'class': 'form-control'
        })
    )
    
    genre = forms.ModelChoiceField(
        label='Género',
        queryset=Genre.objects.all().order_by('name'),
        required=False,
        empty_label='Todos los géneros',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        label='Estado',
        choices=[('', 'Todos los estados')] + list(Anime.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    anime_type = forms.ChoiceField(
        label='Tipo',
        choices=[('', 'Todos los tipos')] + list(Anime.TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    year = forms.ChoiceField(
        label='Año',
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sort = forms.ChoiceField(
        label='Ordenar por',
        choices=SORT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get unique years from the Anime model
        years = Anime.objects.values_list('year', flat=True).distinct().order_by('-year')
        year_choices = [('', 'Todos los años')] + [(str(year), str(year)) for year in years if year is not None]
        self.fields['year'].choices = year_choices
