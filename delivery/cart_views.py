"""
Cart backend views — Part 4.
All actions are POST-only, login-required, and redirect after completing.
No frontend templates.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Product, Cart, CartItem


def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _respond(request, next_fallback, success, text, **extra):
    """Return JSON for AJAX requests, otherwise redirect with a flash message."""
    if _is_ajax(request):
        data = {'ok': success, 'text': text}
        data.update(extra)
        return JsonResponse(data)
    if success:
        messages.success(request, text)
    else:
        messages.warning(request, text)
    return redirect(_next_url(request, next_fallback))


def _get_or_create_cart(user):
    """Return the user's cart, creating it if needed."""
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _next_url(request, fallback_url):
    return request.POST.get('next') or request.META.get('HTTP_REFERER') or fallback_url


# ── Add ───────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def cart_add(request, product_pk):
    """Add product to cart; if already there, increase quantity by 1."""
    product = get_object_or_404(Product, pk=product_pk, is_available=True)
    cart = _get_or_create_cart(request.user)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1},
    )
    if not created:
        if item.quantity >= product.stock:
            return _respond(request, '/delivery/cart/', False,
                             f"«{product.name}» dan omborda faqat {product.stock} dona mavjud.",
                             cart_count=cart.get_total_quantity())
        item.quantity += 1
        item.save(update_fields=['quantity'])
        return _respond(request, '/delivery/cart/', True,
                         f"«{product.name}» miqdori oshirildi.",
                         cart_count=cart.get_total_quantity(), quantity=item.quantity)
    else:
        if product.stock < 1:
            item.delete()
            return _respond(request, '/delivery/cart/', False,
                             f"«{product.name}» hozircha mavjud emas.",
                             cart_count=cart.get_total_quantity())
        return _respond(request, '/delivery/cart/', True,
                         f"«{product.name}» savatga qo'shildi.",
                         cart_count=cart.get_total_quantity(), quantity=item.quantity)


# ── Remove ────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def cart_remove(request, product_pk):
    """Remove a CartItem from the cart entirely."""
    product = get_object_or_404(Product, pk=product_pk)
    cart = get_object_or_404(Cart, user=request.user)

    deleted, _ = CartItem.objects.filter(cart=cart, product=product).delete()
    if deleted:
        messages.success(request, f"«{product.name}» savatdan olib tashlandi.")
    else:
        messages.warning(request, "Bu mahsulot savatda topilmadi.")

    return redirect(_next_url(request, '/delivery/cart/'))


# ── Increase ──────────────────────────────────────────────────────────────────

@require_POST
@login_required
def cart_increase(request, product_pk):
    """Increase the quantity of a cart item by 1."""
    product = get_object_or_404(Product, pk=product_pk, is_available=True)
    cart = get_object_or_404(Cart, user=request.user)
    item = get_object_or_404(CartItem, cart=cart, product=product)

    if item.quantity >= product.stock:
        messages.warning(request, f"«{product.name}» dan omborda faqat {product.stock} dona mavjud.")
        return redirect(_next_url(request, '/delivery/cart/'))

    item.quantity += 1
    item.save(update_fields=['quantity'])
    messages.success(request, f"«{product.name}» miqdori: {item.quantity}.")

    return redirect(_next_url(request, '/delivery/cart/'))


# ── Decrease ──────────────────────────────────────────────────────────────────

@require_POST
@login_required
def cart_decrease(request, product_pk):
    """
    Decrease quantity by 1.
    If quantity reaches 0 after decrement, remove the item.
    """
    product = get_object_or_404(Product, pk=product_pk)
    cart = get_object_or_404(Cart, user=request.user)
    item = get_object_or_404(CartItem, cart=cart, product=product)

    if item.quantity > 1:
        item.quantity -= 1
        item.save(update_fields=['quantity'])
        messages.success(request, f"«{product.name}» miqdori: {item.quantity}.")
    else:
        item.delete()
        messages.success(request, f"«{product.name}» savatdan olib tashlandi.")

    return redirect(_next_url(request, '/delivery/cart/'))
