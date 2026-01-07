from django.urls import path,include
from .views import(
 HomeView,
 ProductDetailView,
 add_to_cart,
 remove_from_cart,
 OrderSummaryView,
 CheckoutView,
 pesapal_callback,
 pesapal_ipn,
 mpesa_callback,
 check_payment_status
)


from .import views
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static


app_name = "Ecoweb"

urlpatterns = [
    path('accounts/signup/', views.CustomSignupView.as_view(), name='account_signup'),
    path('accounts/login/', views.CustomLoginView.as_view(), name='account_login'),
    path('accounts/', include('allauth.urls')),
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='index'),
    path('product/<slug>/',ProductDetailView.as_view(), name='detail'),
    path('add-to-cart/<slug>/',views.add_to_cart,name='add-to-cart'),
    path('remove-from-cart/<slug>/',views.remove_from_cart,name='remove-from-cart'),
    path('link/',views.detailitem,name='linkage'),
    path('cart/', OrderSummaryView.as_view(),name='cart'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('complete/',views.complete,name='complete'),
    path('about/',views.about,name='about'),
    path('contact/',views.contact,name='contact'),
    path('payment/callback/', pesapal_callback, name='pesapal_callback'),
    path('payment/ipn/', pesapal_ipn, name='pesapal_ipn'),
    path('mpesa/callback/', mpesa_callback, name='mpesa_callback'),
    path('check-payment-status/<str:checkout_request_id>/', check_payment_status, name='check_payment_status'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
