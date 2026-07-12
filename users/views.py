from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .forms import UserRegisterForm, UserUpdateForm
from django.shortcuts import render,redirect
from django.contrib.auth import login,authenticate
from django.contrib.auth.decorators import login_required
from movies.models import Movie , Booking

def home(request):
    # Recommend top 10 movies by rating (fallback to newest if ratings tie)
    top_movies_qs = (
        Movie.objects.all()
        .order_by('-rating', '-release_date', 'name')
        .only('id', 'name', 'rating', 'description', 'image', 'release_date')
    )
    movies = list(top_movies_qs[:12])

    # Show top-10 as Recommended
    recommended_movies_qs = top_movies_qs[:10]

    recommended_movies = []
    for movie in recommended_movies_qs:
        poster = movie.image.url if getattr(movie, 'image', None) else None
        if not poster:
            poster_urls = [
                'https://images.unsplash.com/photo-1517602302552-471fe67acf66?auto=format&fit=crop&w=600&q=80',
                'https://images.unsplash.com/photo-1542204165-73f2bd057448?auto=format&fit=crop&w=600&q=80',
                'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=600&q=80',
                'https://images.unsplash.com/photo-1517602967131-07e25e9ec964?auto=format&fit=crop&w=600&q=80',
                'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=600&q=80',
            ]
            poster = poster_urls[len(recommended_movies) % len(poster_urls)]

        recommended_movies.append({'movie': movie, 'poster': poster})

    return render(request, 'home.html', {'movies': movies, 'recommended_movies': recommended_movies})
def register(request):
    if request.method == 'POST':
        form=UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username=form.cleaned_data.get('username')
            password=form.cleaned_data.get('password1')
            user=authenticate(username=username,password=password)
            login(request,user)
            return redirect('profile')
    else:
        form=UserRegisterForm()
    return render(request,'users/register.html',{'form':form})

def login_view(request):
    if request.method == 'POST':
        form=AuthenticationForm(request,data=request.POST)
        if form.is_valid():
            user=form.get_user()
            login(request,user)
            return redirect('/')
    else:
        form=AuthenticationForm()
    return render(request,'users/login.html',{'form':form})

@login_required
def profile(request):
    bookings= Booking.objects.filter(user=request.user)
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        if u_form.is_valid():
            u_form.save()
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)

    return render(request, 'users/profile.html', {'u_form': u_form,'bookings':bookings})

@login_required
def reset_password(request):
    if request.method == 'POST':
        form=PasswordChangeForm(user=request.user,data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form=PasswordChangeForm(user=request.user)
    return render(request,'users/reset_password.html',{'form':form})